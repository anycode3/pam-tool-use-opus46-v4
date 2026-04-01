"""Device modification service for PAM layout optimization.

Computes new geometry for devices when their electrical value changes.
Supports capacitors, resistors, and inductors in auto or manual mode.
"""

from __future__ import annotations

import copy
import math
import uuid

from services.geometry_utils import polygon_bbox, bbox_dimensions, polygon_centroid


def modify_device(
    device: dict,
    layout_data: dict,
    new_value: float,
    mode: str = "auto",
    manual_params: dict | None = None,
) -> dict:
    """Compute a modification preview for a device.

    Args:
        device: Device dict from devices.json.
        layout_data: Full layout data dict (with geometries list).
        new_value: Target electrical value for the device.
        mode: "auto" or "manual".
        manual_params: For manual mode - dict with keys like width, length, scale_factor.

    Returns:
        Modification preview dict with old/new points for each affected polygon.

    Raises:
        ValueError: If device type is unsupported or parameters are invalid.
    """
    device_type = device["type"]
    old_value = device["value"]

    if new_value <= 0:
        raise ValueError("new_value must be positive")
    if old_value <= 0:
        raise ValueError("Device has invalid current value")

    # Build a lookup of polygon_id -> geometry
    geo_lookup = {g["id"]: g for g in layout_data.get("geometries", [])}

    handlers = {
        "capacitor": _modify_capacitor,
        "resistor": _modify_resistor,
        "inductor": _modify_inductor,
    }

    handler = handlers.get(device_type)
    if handler is None:
        raise ValueError(f"Unsupported device type for modification: {device_type}")

    changes = handler(device, geo_lookup, old_value, new_value, mode, manual_params)

    mod_id = f"mod_{uuid.uuid4().hex[:6]}"
    return {
        "id": mod_id,
        "device_id": device["id"],
        "device_type": device_type,
        "old_value": old_value,
        "new_value": new_value,
        "changes": changes,
    }


def apply_modifications(layout_data: dict, modifications: list[dict]) -> dict:
    """Apply a list of modifications to layout data, returning a new copy.

    Args:
        layout_data: Original layout data dict.
        modifications: List of modification preview dicts.

    Returns:
        New layout data dict with modifications applied.
    """
    new_data = copy.deepcopy(layout_data)
    geo_lookup = {g["id"]: g for g in new_data.get("geometries", [])}

    for mod in modifications:
        for change in mod.get("changes", []):
            polygon_id = change["polygon_id"]
            if polygon_id in geo_lookup:
                geo_lookup[polygon_id]["points"] = change["new_points"]

    # Recompute bounds
    all_x, all_y = [], []
    for g in new_data.get("geometries", []):
        for p in g.get("points", []):
            all_x.append(p[0])
            all_y.append(p[1])

    if all_x and all_y:
        new_data["bounds"] = {
            "min_x": min(all_x),
            "min_y": min(all_y),
            "max_x": max(all_x),
            "max_y": max(all_y),
        }

    return new_data


def _modify_capacitor(
    device: dict,
    geo_lookup: dict,
    old_value: float,
    new_value: float,
    mode: str,
    manual_params: dict | None,
) -> list[dict]:
    """Modify capacitor polygons. C proportional to area."""
    polygon_ids = device.get("polygon_ids", [])
    changes = []

    if mode == "manual":
        if not manual_params or "width" not in manual_params or "length" not in manual_params:
            raise ValueError("Manual mode requires 'width' and 'length' parameters")
        target_width = manual_params["width"]
        target_length = manual_params["length"]

        for pid in polygon_ids:
            geo = geo_lookup.get(pid)
            if geo is None:
                continue
            old_points = [list(p) for p in geo["points"]]
            new_points = _resize_rect(old_points, target_width, target_length)
            changes.append({
                "polygon_id": pid,
                "old_points": old_points,
                "new_points": new_points,
            })
    else:
        # Auto: scale area proportionally. Area ratio = new_value/old_value.
        # Scale one dimension (length) to achieve new area.
        ratio = new_value / old_value

        for pid in polygon_ids:
            geo = geo_lookup.get(pid)
            if geo is None:
                continue
            old_points = [list(p) for p in geo["points"]]
            bbox = polygon_bbox(old_points)
            w, h = bbox_dimensions(bbox)

            # Keep height (shorter side) fixed, scale width (longer side)
            if w >= h:
                new_w = w * ratio
                new_h = h
            else:
                new_w = w
                new_h = h * ratio

            new_points = _resize_rect(old_points, new_w, new_h)
            changes.append({
                "polygon_id": pid,
                "old_points": old_points,
                "new_points": new_points,
            })

    return changes


def _modify_resistor(
    device: dict,
    geo_lookup: dict,
    old_value: float,
    new_value: float,
    mode: str,
    manual_params: dict | None,
) -> list[dict]:
    """Modify resistor polygons. R proportional to length/width."""
    polygon_ids = device.get("polygon_ids", [])
    changes = []

    if mode == "manual":
        if not manual_params or "width" not in manual_params or "length" not in manual_params:
            raise ValueError("Manual mode requires 'width' and 'length' parameters")
        target_width = manual_params["width"]
        target_length = manual_params["length"]

        for pid in polygon_ids:
            geo = geo_lookup.get(pid)
            if geo is None:
                continue
            old_points = [list(p) for p in geo["points"]]
            new_points = _resize_rect(old_points, target_width, target_length)
            changes.append({
                "polygon_id": pid,
                "old_points": old_points,
                "new_points": new_points,
            })
    else:
        # Auto: keep width, adjust length. new_length = old_length * (new_value/old_value)
        ratio = new_value / old_value

        for pid in polygon_ids:
            geo = geo_lookup.get(pid)
            if geo is None:
                continue
            old_points = [list(p) for p in geo["points"]]
            bbox = polygon_bbox(old_points)
            w, h = bbox_dimensions(bbox)
            length = max(w, h)
            width = min(w, h)

            new_length = length * ratio
            # Preserve orientation
            if w >= h:
                new_points = _resize_rect(old_points, new_length, width)
            else:
                new_points = _resize_rect(old_points, width, new_length)

            changes.append({
                "polygon_id": pid,
                "old_points": old_points,
                "new_points": new_points,
            })

    return changes


def _modify_inductor(
    device: dict,
    geo_lookup: dict,
    old_value: float,
    new_value: float,
    mode: str,
    manual_params: dict | None,
) -> list[dict]:
    """Modify inductor polygons. Scale uniformly by sqrt(ratio) around centroid."""
    polygon_ids = device.get("polygon_ids", [])
    changes = []

    if mode == "manual":
        if not manual_params or "scale_factor" not in manual_params:
            raise ValueError("Manual mode for inductors requires 'scale_factor' parameter")
        scale = manual_params["scale_factor"]
    else:
        # Auto: L proportional to n^2 * d_avg, scale uniformly by sqrt(ratio)
        ratio = new_value / old_value
        scale = math.sqrt(ratio)

    for pid in polygon_ids:
        geo = geo_lookup.get(pid)
        if geo is None:
            continue
        old_points = [list(p) for p in geo["points"]]
        centroid = polygon_centroid(old_points)
        cx, cy = centroid

        new_points = []
        for p in old_points:
            nx = cx + (p[0] - cx) * scale
            ny = cy + (p[1] - cy) * scale
            new_points.append([round(nx, 6), round(ny, 6)])

        changes.append({
            "polygon_id": pid,
            "old_points": old_points,
            "new_points": new_points,
        })

    return changes


def _resize_rect(
    old_points: list[list[float]],
    new_width: float,
    new_height: float,
) -> list[list[float]]:
    """Resize a rectangular polygon anchored at its min corner.

    Assumes a 4-point polygon and preserves the bottom-left anchor.
    """
    bbox = polygon_bbox(old_points)
    x_min, y_min = bbox[0], bbox[1]

    return [
        [round(x_min, 6), round(y_min, 6)],
        [round(x_min + new_width, 6), round(y_min, 6)],
        [round(x_min + new_width, 6), round(y_min + new_height, 6)],
        [round(x_min, 6), round(y_min + new_height, 6)],
    ]

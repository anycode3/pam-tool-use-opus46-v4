"""Device recognition engine for PAM layout analysis.

Identifies inductors, capacitors, resistors, PADs and GND vias
from parsed layout geometries using layer mapping and geometric rules.
"""

from __future__ import annotations

import math
from services.geometry_utils import (
    polygon_bbox,
    polygon_area,
    polygon_perimeter,
    polygon_centroid,
    polygons_overlap,
    is_rectangular,
    overlap_area,
    bbox_dimensions,
    aspect_ratio,
)


# Physical constants (placeholder values for estimation)
EPSILON_0 = 8.854e-12  # F/m
EPSILON_R = 7.0  # relative permittivity (SiN dielectric)
DIELECTRIC_THICKNESS = 0.2e-6  # 0.2 um between ME1 and ME2
SHEET_RESISTANCE_TFR = 50.0  # Ohm/square
INDUCTANCE_PER_TURN_NH = 0.5  # nH per turn (rough placeholder)


def recognize_devices(
    geometries: list[dict],
    layer_mapping: dict[str, str],
) -> dict:
    """Run the full device recognition pipeline.

    Args:
        geometries: List of geometry dicts from layout_data.json,
                    each having id, type, layer, datatype, points.
        layer_mapping: Dict mapping "<layer>/<datatype>" to target
                       layer name (ME1, ME2, TFR, VA1, GND).

    Returns:
        Dict with "devices" list and "stats" summary.
    """
    # Build reverse mapping: target_layer_name -> list of geometries
    layer_geos: dict[str, list[dict]] = {
        "ME1": [], "ME2": [], "TFR": [], "VA1": [], "GND": [],
    }

    for geo in geometries:
        layer = geo['layer']
        # Handle both integer (GDS) and string (DXF) layer identifiers
        if isinstance(layer, int):
            key = f"{layer}/{geo.get('datatype', 0)}"
        else:
            key = str(layer)

        target = layer_mapping.get(key)
        if target and target in layer_geos:
            layer_geos[target].append(geo)

    used_ids: set[str] = set()
    devices: list[dict] = []
    dev_counter = 0

    def next_id():
        nonlocal dev_counter
        dev_counter += 1
        return f"dev_{dev_counter:03d}"

    # 1. Inductors (spiral detection on both ME1 and ME2 overlapping)
    me1_spirals = []
    for geo in layer_geos["ME1"]:
        if geo["id"] in used_ids:
            continue
        pts = geo["points"]
        if _is_inductor_shape(pts):
            me1_spirals.append(geo)

    me2_spirals = []
    for geo in layer_geos["ME2"]:
        if geo["id"] in used_ids:
            continue
        pts = geo["points"]
        if _is_inductor_shape(pts):
            me2_spirals.append(geo)

    # Match ME1 spirals with overlapping ME2 spirals
    for g1 in me1_spirals:
        if g1["id"] in used_ids:
            continue
        bb1 = polygon_bbox(g1["points"])
        for g2 in me2_spirals:
            if g2["id"] in used_ids:
                continue
            bb2 = polygon_bbox(g2["points"])
            # Check if the two spirals overlap significantly
            ov = overlap_area(bb1, bb2)
            min_area = min(polygon_area(g1["points"]), polygon_area(g2["points"]))
            if ov > 0 and min_area > 0 and ov / min_area > 0.5:
                # Found a matching pair
                turns = _estimate_turns(g1["points"])
                combined_bbox = [
                    min(bb1[0], bb2[0]), min(bb1[1], bb2[1]),
                    max(bb1[2], bb2[2]), max(bb1[3], bb2[3]),
                ]
                value = turns * INDUCTANCE_PER_TURN_NH
                dev = _make_device(
                    dev_id=next_id(),
                    dev_type="inductor",
                    value=round(value, 3),
                    unit="nH",
                    layers=["ME1", "ME2"],
                    bbox=combined_bbox,
                    polygon_ids=[g1["id"], g2["id"]],
                    points_list=[g1["points"], g2["points"]],
                    extra={"turns": turns},
                )
                devices.append(dev)
                used_ids.add(g1["id"])
                used_ids.add(g2["id"])
                break  # each ME1 spiral matched to at most one ME2 spiral

    # 2. Capacitors (overlapping rectangles on ME1 and ME2)
    me1_rects = [g for g in layer_geos["ME1"]
                 if g["id"] not in used_ids and is_rectangular(g["points"])]
    me2_rects = [g for g in layer_geos["ME2"]
                 if g["id"] not in used_ids and is_rectangular(g["points"])]

    # Pre-collect VA1 polygons for PAD/GND via exclusion during cap detection
    va1_all = [g for g in layer_geos["VA1"] if g["id"] not in used_ids]

    for g1 in me1_rects:
        if g1["id"] in used_ids:
            continue
        bb1 = polygon_bbox(g1["points"])
        for g2 in me2_rects:
            if g2["id"] in used_ids:
                continue
            bb2 = polygon_bbox(g2["points"])
            ov = overlap_area(bb1, bb2)
            if ov > 0:
                # Skip if a VA1 polygon overlaps here (likely PAD or GND via)
                has_va1 = any(
                    polygons_overlap(g1["points"], vg["points"])
                    for vg in va1_all if vg["id"] not in used_ids
                )
                if has_va1:
                    continue
                combined_bbox = [
                    min(bb1[0], bb2[0]), min(bb1[1], bb2[1]),
                    max(bb1[2], bb2[2]), max(bb1[3], bb2[3]),
                ]
                # Estimate capacitance: C = eps0 * eps_r * A / d
                area_m2 = ov * 1e-12  # assume layout units are microns
                cap_f = EPSILON_0 * EPSILON_R * area_m2 / DIELECTRIC_THICKNESS
                cap_pf = cap_f * 1e12
                dev = _make_device(
                    dev_id=next_id(),
                    dev_type="capacitor",
                    value=round(cap_pf, 4),
                    unit="pF",
                    layers=["ME1", "ME2"],
                    bbox=combined_bbox,
                    polygon_ids=[g1["id"], g2["id"]],
                    points_list=[g1["points"], g2["points"]],
                )
                devices.append(dev)
                used_ids.add(g1["id"])
                used_ids.add(g2["id"])
                break  # each ME1 rect matched to at most one ME2 rect

    # 3. Resistors (TFR layer, rectangular, high aspect ratio)
    for geo in layer_geos["TFR"]:
        if geo["id"] in used_ids:
            continue
        pts = geo["points"]
        if is_rectangular(pts) and aspect_ratio(pts) > 2.0:
            bbox = polygon_bbox(pts)
            w, h = bbox_dimensions(bbox)
            length = max(w, h)
            width = min(w, h)
            squares = length / width if width > 0 else 0
            resistance = SHEET_RESISTANCE_TFR * squares
            dev = _make_device(
                dev_id=next_id(),
                dev_type="resistor",
                value=round(resistance, 2),
                unit="Ω",
                layers=["TFR"],
                bbox=bbox,
                polygon_ids=[geo["id"]],
                points_list=[pts],
            )
            devices.append(dev)
            used_ids.add(geo["id"])

    # 4. GND vias (GND + ME1 + ME2 + VA1 overlap, excluding used)
    #    Detected before PADs because GND vias are more specific (4 layers vs 3).
    gnd_geos = [g for g in layer_geos["GND"] if g["id"] not in used_ids]
    va1_geos = [g for g in layer_geos["VA1"] if g["id"] not in used_ids]
    _find_multi_layer_devices(
        devices, used_ids, next_id,
        required_layers={"GND": gnd_geos,
                         "ME1": layer_geos["ME1"],
                         "ME2": layer_geos["ME2"],
                         "VA1": va1_geos},
        dev_type="via_gnd",
    )

    # 5. PADs (ME1 + ME2 + VA1 overlap, excluding used)
    va1_geos2 = [g for g in layer_geos["VA1"] if g["id"] not in used_ids]
    _find_multi_layer_devices(
        devices, used_ids, next_id,
        required_layers={"ME1": layer_geos["ME1"],
                         "ME2": layer_geos["ME2"],
                         "VA1": va1_geos2},
        dev_type="pad",
    )

    stats = {
        "inductors": sum(1 for d in devices if d["type"] == "inductor"),
        "capacitors": sum(1 for d in devices if d["type"] == "capacitor"),
        "resistors": sum(1 for d in devices if d["type"] == "resistor"),
        "pads": sum(1 for d in devices if d["type"] == "pad"),
        "via_gnds": sum(1 for d in devices if d["type"] == "via_gnd"),
        "total": len(devices),
    }

    return {"devices": devices, "stats": stats}


def _is_inductor_shape(points: list[list[float]]) -> bool:
    """Detect if a polygon looks like a spiral inductor.

    Criteria: many vertices (> 8) and high perimeter-to-area ratio.
    """
    n = len(points)
    if n <= 8:
        return False
    area = polygon_area(points)
    if area == 0:
        return False
    perimeter = polygon_perimeter(points)
    # Compactness = 4*pi*area / perimeter^2.  Circle=1, spiral << 1.
    compactness = (4 * math.pi * area) / (perimeter * perimeter)
    # Spiral shapes have low compactness (< 0.3 roughly)
    return compactness < 0.3


def _estimate_turns(points: list[list[float]]) -> int:
    """Estimate the number of turns in a spiral polygon.

    Sums absolute angle changes around the polygon.  Each full
    revolution of the centroid corresponds to one turn.
    """
    centroid = polygon_centroid(points)
    cx, cy = centroid
    total_angle = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i][0] - cx, points[i][1] - cy
        x2, y2 = points[(i + 1) % n][0] - cx, points[(i + 1) % n][1] - cy
        angle1 = math.atan2(y1, x1)
        angle2 = math.atan2(y2, x2)
        delta = angle2 - angle1
        # Normalize to [-pi, pi]
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        total_angle += abs(delta)
    turns = max(1, int(total_angle / (2 * math.pi)))
    return turns


def _find_multi_layer_devices(
    devices: list[dict],
    used_ids: set[str],
    next_id,
    required_layers: dict[str, list[dict]],
    dev_type: str,
) -> None:
    """Find devices that require overlapping polygons on multiple layers.

    Used for PADs and GND vias.
    """
    layer_names = list(required_layers.keys())
    if not all(required_layers[ln] for ln in layer_names):
        return

    # Use the first layer as anchor
    anchor_layer = layer_names[0]
    other_layers = layer_names[1:]

    for anchor_geo in required_layers[anchor_layer]:
        if anchor_geo["id"] in used_ids:
            continue
        matched = {anchor_layer: anchor_geo}
        anchor_bb = polygon_bbox(anchor_geo["points"])

        all_matched = True
        for ol in other_layers:
            found = False
            for candidate in required_layers[ol]:
                if candidate["id"] in used_ids:
                    continue
                if polygons_overlap(anchor_geo["points"], candidate["points"]):
                    matched[ol] = candidate
                    found = True
                    break
            if not found:
                all_matched = False
                break

        if all_matched:
            poly_ids = [matched[ln]["id"] for ln in layer_names]
            all_points = [matched[ln]["points"] for ln in layer_names]
            all_bbs = [polygon_bbox(pts) for pts in all_points]
            combined_bbox = [
                min(b[0] for b in all_bbs),
                min(b[1] for b in all_bbs),
                max(b[2] for b in all_bbs),
                max(b[3] for b in all_bbs),
            ]
            dev = _make_device(
                dev_id=next_id(),
                dev_type=dev_type,
                value=0,
                unit="",
                layers=layer_names,
                bbox=combined_bbox,
                polygon_ids=poly_ids,
                points_list=all_points,
            )
            devices.append(dev)
            for pid in poly_ids:
                used_ids.add(pid)


def _make_device(
    dev_id: str,
    dev_type: str,
    value: float,
    unit: str,
    layers: list[str],
    bbox: list[float],
    polygon_ids: list[str],
    points_list: list[list[list[float]]],
    extra: dict | None = None,
) -> dict:
    """Build a device dict in the standard format."""
    w, h = bbox_dimensions(bbox)
    area = w * h

    # Ports: two corners of bbox
    ports = [
        {"id": "p1", "position": [bbox[0], bbox[1]], "layer": layers[0]},
        {"id": "p2", "position": [bbox[2], bbox[3]], "layer": layers[-1]},
    ]

    device = {
        "id": dev_id,
        "type": dev_type,
        "value": value,
        "unit": unit,
        "layers": layers,
        "bbox": bbox,
        "polygon_ids": polygon_ids,
        "ports": ports,
        "metrics": {
            "area": round(area, 2),
            "width": round(min(w, h), 2),
            "length": round(max(w, h), 2),
        },
    }

    if extra:
        device.update(extra)

    return device

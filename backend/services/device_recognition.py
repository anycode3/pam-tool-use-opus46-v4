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
    distance_to_centroid_range,
    bbox_area_ratio,
    median_edge_length,
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

    # 1. Inductors - Step 1: Single polygon spiral detection
    me1_spirals: list[tuple[dict, dict]] = []  # (geometry, params)
    for geo in layer_geos["ME1"]:
        if geo["id"] in used_ids:
            continue
        pts = geo["points"]
        is_spiral, spiral_params = _is_inductor_shape(pts)
        if is_spiral:
            me1_spirals.append((geo, spiral_params))

    me2_spirals: list[tuple[dict, dict]] = []
    for geo in layer_geos["ME2"]:
        if geo["id"] in used_ids:
            continue
        pts = geo["points"]
        is_spiral, spiral_params = _is_inductor_shape(pts)
        if is_spiral:
            me2_spirals.append((geo, spiral_params))

    # Match ME1 spirals with overlapping ME2 spirals
    for g1, params1 in me1_spirals:
        if g1["id"] in used_ids:
            continue
        bb1 = polygon_bbox(g1["points"])
        for g2, params2 in me2_spirals:
            if g2["id"] in used_ids:
                continue
            bb2 = polygon_bbox(g2["points"])
            ov = overlap_area(bb1, bb2)
            min_area = min(polygon_area(g1["points"]), polygon_area(g2["points"]))
            if ov > 0 and min_area > 0 and ov / min_area > 0.3:
                turns = _estimate_turns(g1["points"])
                combined_bbox = [
                    min(bb1[0], bb2[0]), min(bb1[1], bb2[1]),
                    max(bb1[2], bb2[2]), max(bb1[3], bb2[3]),
                ]
                value = turns * INDUCTANCE_PER_TURN_NH
                merged_params = {
                    "turns": turns,
                    "inner_radius": params1.get("inner_radius", 0),
                    "outer_radius": params2.get("outer_radius", 0),
                    "line_width": params1.get("line_width", 0),
                    "compactness": params1.get("compactness", 0),
                    "recognition_method": "single_polygon",
                }
                dev = _make_device(
                    dev_id=next_id(),
                    dev_type="inductor",
                    value=round(value, 3),
                    unit="nH",
                    layers=["ME1", "ME2"],
                    bbox=combined_bbox,
                    polygon_ids=[g1["id"], g2["id"]],
                    points_list=[g1["points"], g2["points"]],
                    extra=merged_params,
                )
                devices.append(dev)
                used_ids.add(g1["id"])
                used_ids.add(g2["id"])
                break

    # 1b. Inductors - Step 2: Multi-polygon spiral detection (separate rectangles)
    #    Detect clusters of ME1+ME2 overlapping rectangles forming a spiral pattern
    separate_spiral_inductors = _find_separate_spiral_inductors(
        layer_geos["ME1"], layer_geos["ME2"], used_ids
    )
    for ind_info in separate_spiral_inductors:
        dev = _make_device(
            dev_id=next_id(),
            dev_type="inductor",
            value=round(ind_info["turns"] * INDUCTANCE_PER_TURN_NH, 3),
            unit="nH",
            layers=["ME1", "ME2"],
            bbox=ind_info["bbox"],
            polygon_ids=ind_info["polygon_ids"],
            points_list=ind_info["points_list"],
            extra={
                "turns": ind_info["turns"],
                "inner_radius": ind_info["inner_radius"],
                "outer_radius": ind_info["outer_radius"],
                "recognition_method": "multi_polygon",
            },
        )
        devices.append(dev)
        for pid in ind_info["polygon_ids"]:
            used_ids.add(pid)

    # 2. Capacitors (overlapping plates on ME1 and ME2)
    # Use improved capacitor plate detection supporting more vertices
    me1_plates: list[tuple[dict, float]] = []  # (geometry, area)
    for g in layer_geos["ME1"]:
        if g["id"] in used_ids:
            continue
        is_plate, area = _is_capacitor_plate(g["points"])
        if is_plate:
            me1_plates.append((g, area))

    me2_plates: list[tuple[dict, float]] = []
    for g in layer_geos["ME2"]:
        if g["id"] in used_ids:
            continue
        is_plate, area = _is_capacitor_plate(g["points"])
        if is_plate:
            me2_plates.append((g, area))

    # Pre-collect VA1 polygons for PAD/GND via exclusion during cap detection
    va1_all = [g for g in layer_geos["VA1"] if g["id"] not in used_ids]

    for g1, area1 in me1_plates:
        if g1["id"] in used_ids:
            continue
        bb1 = polygon_bbox(g1["points"])
        for g2, area2 in me2_plates:
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
                break  # each ME1 plate matched to at most one ME2 plate

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


def _is_inductor_shape(points: list[list[float]]) -> tuple[bool, dict]:
    """Detect if a polygon looks like a spiral inductor.

    Improved detection with relaxed thresholds and additional geometric checks.

    Returns:
        Tuple of (is_spiral, params_dict) where params_dict contains
        inner_radius, outer_radius, line_width, compactness if detected.
    """
    n = len(points)
    if n < 8:  # Relaxed: >= 8 vertices
        return False, {}

    area = polygon_area(points)
    if area == 0:
        return False, {}

    perimeter = polygon_perimeter(points)
    # Compactness = 4*pi*area / perimeter^2.  Circle=1, spiral << 1.
    compactness = (4 * math.pi * area) / (perimeter * perimeter)

    # Relaxed threshold: < 0.4 instead of < 0.3
    if compactness > 0.4:
        return False, {}

    # New check: inner/outer radius ratio
    inner_r, outer_r = distance_to_centroid_range(points)

    # Spiral should have significant radius difference (ratio > 1.3)
    if inner_r == 0 or outer_r / inner_r < 1.3:
        return False, {}

    # New check: bounding box area ratio
    # Spirals have lower ratios due to hollow center
    bbox_ratio = bbox_area_ratio(points)
    if bbox_ratio > 0.8:  # Rectangle-like shapes are not spirals
        return False, {}

    # Extract line width from median edge length
    line_width = median_edge_length(points)

    params = {
        "inner_radius": round(inner_r, 2),
        "outer_radius": round(outer_r, 2),
        "line_width": round(line_width, 2),
        "compactness": round(compactness, 4),
    }
    return True, params


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


def _is_capacitor_plate(points: list[list[float]]) -> tuple[bool, float]:
    """Detect if a polygon is suitable as a capacitor plate.

    Improved detection supporting polygons with more vertices
    (GDS files may use more than 4 vertices for rectangles).

    Returns:
        Tuple of (is_plate, area) where area is the polygon area.
    """
    n = len(points)
    if n < 4 or n > 50:  # Relaxed vertex range
        return False, 0.0

    bbox = polygon_bbox(points)
    bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    poly_area = polygon_area(points)

    if bbox_area == 0 or poly_area == 0:
        return False, 0.0

    # Area ratio > 0.85 indicates an approximately rectangular shape
    area_ratio = poly_area / bbox_area
    if area_ratio < 0.85:
        return False, 0.0

    # For 4-vertex polygons, also check rectangularity with relaxed tolerance
    if n == 4:
        if not is_rectangular(points, tolerance=0.15):
            return False, 0.0

    return True, poly_area


def _find_separate_spiral_inductors(
    me1_geos: list[dict],
    me2_geos: list[dict],
    used_ids: set[str],
) -> list[dict]:
    """Detect spiral inductors formed by multiple separate rectangles.

    This handles the case where a spiral inductor is represented as
    multiple separate rectangles (one per arm/turn) rather than a
    single continuous polygon.

    Algorithm:
    1. Find best ME1+ME2 matching pairs (one-to-one matching)
    2. Cluster them by spatial proximity
    3. Check if each cluster forms a spiral pattern (concentric rings)

    Returns:
        List of dicts with inductor info (bbox, polygon_ids, turns, etc.)
    """
    # Step 1: Find best matching ME1+ME2 pairs (one-to-one)
    # Each ME1 rectangle should only match with the closest ME2 rectangle
    overlapping_pairs: list[tuple[dict, dict, float]] = []

    for g1 in me1_geos:
        if g1["id"] in used_ids:
            continue
        is_rect1, _ = _is_capacitor_plate(g1["points"])
        if not is_rect1:
            continue

        bb1 = polygon_bbox(g1["points"])
        best_g2 = None
        best_score = 0

        for g2 in me2_geos:
            if g2["id"] in used_ids:
                continue
            is_rect2, _ = _is_capacitor_plate(g2["points"])
            if not is_rect2:
                continue

            bb2 = polygon_bbox(g2["points"])
            ov = overlap_area(bb1, bb2)
            if ov > 0:
                # Score based on overlap and size similarity
                area1 = (bb1[2] - bb1[0]) * (bb1[3] - bb1[1])
                area2 = (bb2[2] - bb2[0]) * (bb2[3] - bb2[1])
                size_ratio = min(area1, area2) / max(area1, area2) if max(area1, area2) > 0 else 0

                # Prefer large overlap and similar sizes
                score = ov * (1 + size_ratio)
                if score > best_score:
                    best_score = score
                    best_g2 = g2

        if best_g2:
            overlapping_pairs.append((g1, best_g2, best_score))

    if len(overlapping_pairs) < 4:  # Need at least 4 pairs for a spiral
        return []

    # Remove duplicate matches (one ME2 matched by multiple ME1s)
    # Keep only the best match for each ME2
    me2_best_match: dict[str, tuple[dict, dict, float]] = {}
    for g1, g2, score in overlapping_pairs:
        if g2["id"] not in me2_best_match or me2_best_match[g2["id"]][2] < score:
            me2_best_match[g2["id"]] = (g1, g2, score)

    unique_pairs = list(me2_best_match.values())

    if len(unique_pairs) < 4:
        return []

    # Step 2: Cluster overlapping pairs by spatial proximity
    clusters = _cluster_rectangle_pairs(unique_pairs)

    # Step 3: Analyze each cluster for spiral pattern
    inductors = []
    for cluster in clusters:
        spiral_info = _analyze_spiral_cluster(cluster)
        if spiral_info:
            inductors.append(spiral_info)

    return inductors


def _cluster_rectangle_pairs(
    pairs: list[tuple[dict, dict, float]],
) -> list[list[tuple[dict, dict, float]]]:
    """Cluster rectangle pairs by spatial proximity.

    Uses distance between combined bounding box centers to determine
    if pairs belong to the same cluster (potential spiral inductor).
    """
    if not pairs:
        return []

    # Calculate center for each pair
    pair_centers = []
    for g1, g2, score in pairs:
        bb1 = polygon_bbox(g1["points"])
        bb2 = polygon_bbox(g2["points"])
        # Use the average center of the two bounding boxes
        cx = (bb1[0] + bb1[2] + bb2[0] + bb2[2]) / 4
        cy = (bb1[1] + bb1[3] + bb2[1] + bb2[3]) / 4
        pair_centers.append((cx, cy))

    # Use a distance threshold based on typical inductor size
    # Pairs closer than this are likely part of the same spiral
    cluster_threshold = 80  # microns - reduced for tighter clustering

    clusters = []
    assigned = [False] * len(pairs)

    for i, (g1, g2, score) in enumerate(pairs):
        if assigned[i]:
            continue

        cluster = [(g1, g2, score)]
        assigned[i] = True
        cx_i, cy_i = pair_centers[i]

        # Find all pairs close to this one
        for j in range(i + 1, len(pairs)):
            if assigned[j]:
                continue
            cx_j, cy_j = pair_centers[j]
            dist = math.sqrt((cx_i - cx_j) ** 2 + (cy_i - cy_j) ** 2)
            if dist < cluster_threshold:
                cluster.append(pairs[j])
                assigned[j] = True

        clusters.append(cluster)

    return clusters


def _analyze_spiral_cluster(
    cluster: list[tuple[dict, dict, float]],
) -> dict | None:
    """Analyze if a cluster of rectangle pairs forms a spiral inductor.

    Checks for:
    - Multiple pairs (typically >= 4 for a spiral with turns)
    - Rectangles arranged around a common center
    - Multiple distinct radius levels (turns)

    Returns:
        Dict with spiral info, or None if not a spiral.
    """
    if len(cluster) < 4:  # Minimum 4 arms for a recognizable spiral
        return None

    # Calculate combined bbox and center for each pair
    all_bboxes = []
    all_centers = []
    all_radii = []  # Distance from overall center
    all_poly_ids = []
    all_points = []

    for g1, g2, score in cluster:
        bb1 = polygon_bbox(g1["points"])
        bb2 = polygon_bbox(g2["points"])

        # Combined bbox
        combined_bb = [
            min(bb1[0], bb2[0]), min(bb1[1], bb2[1]),
            max(bb1[2], bb2[2]), max(bb1[3], bb2[3]),
        ]
        all_bboxes.append(combined_bb)

        # Center of this rectangle pair
        cx = (combined_bb[0] + combined_bb[2]) / 2
        cy = (combined_bb[1] + combined_bb[3]) / 2
        all_centers.append((cx, cy))

        all_poly_ids.extend([g1["id"], g2["id"]])
        all_points.extend([g1["points"], g2["points"]])

    if not all_centers:
        return None

    # Calculate overall center (average of all centers)
    overall_cx = sum(c[0] for c in all_centers) / len(all_centers)
    overall_cy = sum(c[1] for c in all_centers) / len(all_centers)

    # Calculate radii (distance from overall center)
    for cx, cy in all_centers:
        radius = math.sqrt((cx - overall_cx) ** 2 + (cy - overall_cy) ** 2)
        all_radii.append(radius)

    # Group radii into buckets to count turns
    # Each turn consists of multiple arms at similar radius
    radius_buckets: dict[int, list[float]] = {}
    bucket_size = 10  # Group radii within 10 microns

    for r in all_radii:
        bucket = int(r / bucket_size)
        if bucket not in radius_buckets:
            radius_buckets[bucket] = []
        radius_buckets[bucket].append(r)

    # Count turns: number of distinct radius levels
    # Filter out buckets with too few elements (noise)
    significant_buckets = [b for b, radii in radius_buckets.items() if len(radii) >= 2]
    num_turns = len(significant_buckets)

    if num_turns < 2:  # Need at least 2 turns for a spiral
        return None

    # Check for concentric pattern: buckets should span a range
    if significant_buckets:
        bucket_range = max(significant_buckets) - min(significant_buckets)
        if bucket_range < 2:  # All at same radius level, not a spiral
            return None

    # Calculate combined bbox
    combined_bbox = [
        min(bb[0] for bb in all_bboxes),
        min(bb[1] for bb in all_bboxes),
        max(bb[2] for bb in all_bboxes),
        max(bb[3] for bb in all_bboxes),
    ]

    # Inner and outer radius
    inner_radius = min(all_radii)
    outer_radius = max(all_radii)

    # Additional check: make sure there's significant radius variation
    # (a spiral should have distinct inner and outer regions)
    if outer_radius - inner_radius < 20:  # At least 20 microns of variation
        return None

    return {
        "bbox": combined_bbox,
        "polygon_ids": all_poly_ids,
        "points_list": all_points,
        "turns": num_turns,
        "inner_radius": round(inner_radius, 2),
        "outer_radius": round(outer_radius, 2),
    }


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

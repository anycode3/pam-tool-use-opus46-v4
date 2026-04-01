"""Design Rule Check (DRC) engine for layout geometries.

Checks layout geometries against user-defined rules and reports violations.
Uses bounding-box approximations for width, spacing, and overlap checks.
"""

import json
import uuid

from services.geometry_utils import polygon_bbox, polygon_area, polygon_centroid, bbox_dimensions


def _generate_rule_id() -> str:
    return f"rule_{uuid.uuid4().hex[:8]}"


def validate_rule(rule: dict) -> str | None:
    """Validate a single DRC rule dict. Returns error message or None."""
    valid_types = {"min_width", "min_spacing", "min_area", "min_overlap", "max_width"}
    rtype = rule.get("type")
    if rtype not in valid_types:
        return f"Invalid rule type: {rtype}. Must be one of {sorted(valid_types)}"
    if "layer" not in rule:
        return "Rule must specify 'layer'"
    if "value" not in rule:
        return "Rule must specify 'value'"
    try:
        float(rule["value"])
    except (TypeError, ValueError):
        return f"Rule value must be numeric, got: {rule['value']}"
    if rtype in ("min_spacing", "min_overlap") and not rule.get("layer2"):
        # layer2 is optional for min_spacing (same-layer check), required for min_overlap
        if rtype == "min_overlap":
            return "min_overlap rule must specify 'layer2'"
    return None


def parse_rules(rules_input: list[dict]) -> list[dict]:
    """Parse and normalize a list of rule dicts, assigning IDs where missing."""
    parsed = []
    for r in rules_input:
        rule = {
            "id": r.get("id") or _generate_rule_id(),
            "type": r["type"],
            "layer": r["layer"],
            "layer2": r.get("layer2"),
            "value": float(r["value"]),
            "description": r.get("description", ""),
        }
        parsed.append(rule)
    return parsed


def parse_rule_file(content: str) -> list[dict]:
    """Parse a JSON rule file and return list of normalized rules."""
    data = json.loads(content)
    raw_rules = data.get("rules", [])
    return parse_rules(raw_rules)


def _build_layer_index(layout_data: dict, layer_mapping: dict) -> dict[str, list[dict]]:
    """Build a mapping from mapped layer name to list of geometries on that layer.

    layer_mapping is e.g. {"1/0": "ME1", "2/0": "ME2"}.
    Returns e.g. {"ME1": [geom1, geom2, ...], "ME2": [...]}.
    """
    index: dict[str, list[dict]] = {}
    # Invert: for each geometry, look up its layer key in the mapping
    for geom in layout_data.get("geometries", []):
        layer_key = f"{geom['layer']}/{geom.get('datatype', 0)}"
        mapped_name = layer_mapping.get(layer_key)
        if mapped_name:
            index.setdefault(mapped_name, []).append(geom)
    return index


def _bbox_min_dim(geom: dict) -> float:
    """Return the minimum bbox dimension (width or height) of a geometry."""
    bb = polygon_bbox(geom["points"])
    w, h = bbox_dimensions(bb)
    return min(w, h)


def _bbox_max_dim(geom: dict) -> float:
    """Return the maximum bbox dimension (width or height) of a geometry."""
    bb = polygon_bbox(geom["points"])
    w, h = bbox_dimensions(bb)
    return max(w, h)


def _bbox_spacing(geom1: dict, geom2: dict) -> float:
    """Compute Manhattan distance between closest bbox edges.

    Returns 0 if bboxes overlap.
    """
    bb1 = polygon_bbox(geom1["points"])
    bb2 = polygon_bbox(geom2["points"])

    dx = max(0, max(bb1[0] - bb2[2], bb2[0] - bb1[2]))
    dy = max(0, max(bb1[1] - bb2[3], bb2[1] - bb1[3]))
    return dx + dy


def _bbox_overlap_area(geom1: dict, geom2: dict) -> float:
    """Compute overlap area between two geometries' bounding boxes."""
    bb1 = polygon_bbox(geom1["points"])
    bb2 = polygon_bbox(geom2["points"])

    x_overlap = max(0, min(bb1[2], bb2[2]) - max(bb1[0], bb2[0]))
    y_overlap = max(0, min(bb1[3], bb2[3]) - max(bb1[1], bb2[1]))
    return x_overlap * y_overlap


def _check_min_width(rule: dict, layer_index: dict[str, list[dict]]) -> list[dict]:
    violations = []
    layer = rule["layer"]
    threshold = rule["value"]
    for geom in layer_index.get(layer, []):
        min_dim = _bbox_min_dim(geom)
        if min_dim < threshold:
            centroid = polygon_centroid(geom["points"])
            violations.append({
                "rule_id": rule["id"],
                "rule_type": "min_width",
                "description": rule.get("description", "") + " violation",
                "severity": "error",
                "polygon_id": geom["id"],
                "actual_value": round(min_dim, 4),
                "required_value": threshold,
                "location": centroid,
            })
    return violations


def _check_max_width(rule: dict, layer_index: dict[str, list[dict]]) -> list[dict]:
    violations = []
    layer = rule["layer"]
    threshold = rule["value"]
    for geom in layer_index.get(layer, []):
        max_dim = _bbox_max_dim(geom)
        if max_dim > threshold:
            centroid = polygon_centroid(geom["points"])
            violations.append({
                "rule_id": rule["id"],
                "rule_type": "max_width",
                "description": rule.get("description", "") + " violation",
                "severity": "error",
                "polygon_id": geom["id"],
                "actual_value": round(max_dim, 4),
                "required_value": threshold,
                "location": centroid,
            })
    return violations


def _check_min_area(rule: dict, layer_index: dict[str, list[dict]]) -> list[dict]:
    violations = []
    layer = rule["layer"]
    threshold = rule["value"]
    for geom in layer_index.get(layer, []):
        area = polygon_area(geom["points"])
        if area < threshold:
            centroid = polygon_centroid(geom["points"])
            violations.append({
                "rule_id": rule["id"],
                "rule_type": "min_area",
                "description": rule.get("description", "") + " violation",
                "severity": "error",
                "polygon_id": geom["id"],
                "actual_value": round(area, 4),
                "required_value": threshold,
                "location": centroid,
            })
    return violations


def _check_min_spacing(rule: dict, layer_index: dict[str, list[dict]]) -> list[dict]:
    violations = []
    layer = rule["layer"]
    layer2 = rule.get("layer2") or layer  # same-layer if layer2 not specified
    threshold = rule["value"]

    geoms1 = layer_index.get(layer, [])
    geoms2 = layer_index.get(layer2, [])

    same_layer = (layer == layer2)

    for i, g1 in enumerate(geoms1):
        start_j = i + 1 if same_layer else 0
        candidates = geoms1[start_j:] if same_layer else geoms2
        for g2 in candidates:
            if g1["id"] == g2["id"]:
                continue
            spacing = _bbox_spacing(g1, g2)
            if spacing < threshold:
                centroid1 = polygon_centroid(g1["points"])
                centroid2 = polygon_centroid(g2["points"])
                mid = [
                    round((centroid1[0] + centroid2[0]) / 2, 4),
                    round((centroid1[1] + centroid2[1]) / 2, 4),
                ]
                violations.append({
                    "rule_id": rule["id"],
                    "rule_type": "min_spacing",
                    "description": rule.get("description", "") + " violation",
                    "severity": "error",
                    "polygon_id": f"{g1['id']},{g2['id']}",
                    "actual_value": round(spacing, 4),
                    "required_value": threshold,
                    "location": mid,
                })
    return violations


def _check_min_overlap(rule: dict, layer_index: dict[str, list[dict]]) -> list[dict]:
    violations = []
    layer = rule["layer"]
    layer2 = rule["layer2"]
    threshold = rule["value"]

    geoms1 = layer_index.get(layer, [])
    geoms2 = layer_index.get(layer2, [])

    for g1 in geoms1:
        for g2 in geoms2:
            ov = _bbox_overlap_area(g1, g2)
            # Only report violations for polygon pairs that actually overlap
            # but have insufficient overlap area
            if 0 < ov < threshold:
                centroid1 = polygon_centroid(g1["points"])
                centroid2 = polygon_centroid(g2["points"])
                mid = [
                    round((centroid1[0] + centroid2[0]) / 2, 4),
                    round((centroid1[1] + centroid2[1]) / 2, 4),
                ]
                violations.append({
                    "rule_id": rule["id"],
                    "rule_type": "min_overlap",
                    "description": rule.get("description", "") + " violation",
                    "severity": "warning",
                    "polygon_id": f"{g1['id']},{g2['id']}",
                    "actual_value": round(ov, 4),
                    "required_value": threshold,
                    "location": mid,
                })
    return violations


_CHECKERS = {
    "min_width": _check_min_width,
    "max_width": _check_max_width,
    "min_area": _check_min_area,
    "min_spacing": _check_min_spacing,
    "min_overlap": _check_min_overlap,
}


def run_drc(layout_data: dict, rules: list[dict], layer_mapping: dict) -> list[dict]:
    """Run DRC checks and return list of violations.

    Args:
        layout_data: Parsed layout with 'geometries' list.
        rules: List of DRC rule dicts (normalized via parse_rules).
        layer_mapping: e.g. {"1/0": "ME1", "2/0": "ME2"}.

    Returns:
        List of violation dicts.
    """
    layer_index = _build_layer_index(layout_data, layer_mapping)
    violations: list[dict] = []

    for rule in rules:
        checker = _CHECKERS.get(rule["type"])
        if checker:
            violations.extend(checker(rule, layer_index))

    return violations

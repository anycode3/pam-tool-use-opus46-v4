"""Layout diff service for comparing original and modified geometries."""

from __future__ import annotations

from services.geometry_utils import polygon_bbox, polygon_area


def compute_diff(
    original_geometries: list[dict],
    modified_geometries: list[dict],
) -> list[dict]:
    """Compare original and modified geometry lists, returning changes.

    Args:
        original_geometries: List of geometry dicts from original layout.
        modified_geometries: List of geometry dicts from modified layout.

    Returns:
        List of change dicts with polygon_id, old/new bbox, old/new area.
    """
    # Build lookup by polygon id for modified geometries
    mod_lookup = {g["id"]: g for g in modified_geometries}

    changes = []
    for orig in original_geometries:
        mod = mod_lookup.get(orig["id"])
        if mod is None:
            # Polygon was removed
            changes.append({
                "polygon_id": orig["id"],
                "change_type": "removed",
                "old_bbox": polygon_bbox(orig["points"]),
                "new_bbox": None,
                "old_area": polygon_area(orig["points"]),
                "new_area": 0,
            })
            continue

        if orig["points"] != mod["points"]:
            changes.append({
                "polygon_id": orig["id"],
                "change_type": "modified",
                "old_bbox": polygon_bbox(orig["points"]),
                "new_bbox": polygon_bbox(mod["points"]),
                "old_area": polygon_area(orig["points"]),
                "new_area": polygon_area(mod["points"]),
            })

    # Check for added polygons
    orig_ids = {g["id"] for g in original_geometries}
    for mod in modified_geometries:
        if mod["id"] not in orig_ids:
            changes.append({
                "polygon_id": mod["id"],
                "change_type": "added",
                "old_bbox": None,
                "new_bbox": polygon_bbox(mod["points"]),
                "old_area": 0,
                "new_area": polygon_area(mod["points"]),
            })

    return changes

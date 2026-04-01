import gdstk


def parse_gds(file_path: str) -> dict:
    """Parse a GDS file and return unified layout data dict."""
    lib = gdstk.read_gds(file_path)

    all_polygons = []
    for cell in lib.cells:
        all_polygons.extend(_collect_cell_polygons(cell))

    if not all_polygons:
        return {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0},
            "layers": [],
            "geometries": [],
        }

    geometries = []
    layer_stats: dict[str, int] = {}
    all_x, all_y = [], []

    for idx, (layer, datatype, points) in enumerate(all_polygons):
        geo_id = f"poly_{idx:06d}"
        geometries.append({
            "id": geo_id,
            "type": "polygon",
            "layer": layer,
            "datatype": datatype,
            "points": points,
            "properties": {},
        })

        layer_name = f"{layer}/{datatype}"
        layer_stats[layer_name] = layer_stats.get(layer_name, 0) + 1

        for x, y in points:
            all_x.append(x)
            all_y.append(y)

    bounds = {
        "min_x": min(all_x),
        "min_y": min(all_y),
        "max_x": max(all_x),
        "max_y": max(all_y),
    }

    layers = []
    for name, count in sorted(layer_stats.items()):
        parts = name.split("/")
        layers.append({
            "layer": int(parts[0]),
            "datatype": int(parts[1]),
            "name": name,
            "polygon_count": count,
        })

    return {"bounds": bounds, "layers": layers, "geometries": geometries}


def _collect_cell_polygons(cell) -> list[tuple[int, int, list[list[float]]]]:
    """Collect all polygons from a cell, flattening references."""
    results = []

    for polygon in cell.polygons:
        points = polygon.points.tolist()
        results.append((polygon.layer, polygon.datatype, points))

    for path in cell.paths:
        for polygon in path.to_polygons():
            points = polygon.points.tolist()
            results.append((polygon.layer, polygon.datatype, points))

    for ref in cell.references:
        ref_polygons = ref.cell.get_polygons()
        for polygon in ref_polygons:
            points = polygon.points.tolist()
            results.append((polygon.layer, polygon.datatype, points))

    return results

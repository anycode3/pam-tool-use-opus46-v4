import ezdxf


def parse_dxf(file_path: str) -> dict:
    """Parse a DXF file and return unified layout data dict."""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    # Build a layer name -> integer index mapping
    layer_index: dict[str, int] = {}
    for i, layer_def in enumerate(doc.layers):
        layer_index[layer_def.dxf.name] = i

    geometries = []
    layer_stats: dict[str, int] = {}
    all_x: list[float] = []
    all_y: list[float] = []
    poly_idx = 0

    for entity in msp:
        points = _entity_to_points(entity)
        if not points:
            continue

        layer_name = entity.dxf.layer
        layer_num = layer_index.get(layer_name, 0)

        geo_id = f"poly_{poly_idx:06d}"
        geometries.append({
            "id": geo_id,
            "type": "polygon",
            "layer": layer_num,
            "datatype": 0,
            "points": points,
            "properties": {"dxf_layer": layer_name},
        })
        poly_idx += 1

        layer_stats[layer_name] = layer_stats.get(layer_name, 0) + 1
        for x, y in points:
            all_x.append(x)
            all_y.append(y)

    if not geometries:
        return {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0},
            "layers": [],
            "geometries": [],
        }

    bounds = {
        "min_x": min(all_x),
        "min_y": min(all_y),
        "max_x": max(all_x),
        "max_y": max(all_y),
    }

    layers = []
    for name, count in sorted(layer_stats.items()):
        layers.append({
            "layer": layer_index.get(name, 0),
            "datatype": 0,
            "name": name,
            "polygon_count": count,
        })

    return {"bounds": bounds, "layers": layers, "geometries": geometries}


def _entity_to_points(entity) -> list[list[float]] | None:
    """Convert a DXF entity to a list of [x, y] points. Returns None if unsupported."""
    dxf_type = entity.dxftype()

    if dxf_type == "LWPOLYLINE":
        return [[p[0], p[1]] for p in entity.get_points(format="xy")]

    if dxf_type == "LINE":
        s = entity.dxf.start
        e = entity.dxf.end
        return [[s.x, s.y], [e.x, e.y]]

    if dxf_type == "CIRCLE":
        import math
        cx, cy = entity.dxf.center.x, entity.dxf.center.y
        r = entity.dxf.radius
        n = 32
        return [
            [cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)]
            for i in range(n)
        ]

    if dxf_type == "POLYLINE":
        return [[v.dxf.location.x, v.dxf.location.y] for v in entity.vertices]

    if dxf_type == "HATCH":
        points = []
        for path in entity.paths:
            if hasattr(path, "vertices"):
                points.extend([[v[0], v[1]] for v in path.vertices])
        return points if points else None

    return None

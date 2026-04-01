from services.parser_dxf import parse_dxf


def test_parse_dxf_returns_layout_data(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    assert "bounds" in result
    assert "layers" in result
    assert "geometries" in result


def test_parse_dxf_bounds(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    b = result["bounds"]
    assert b["min_x"] == 0.0
    assert b["min_y"] == 0.0
    assert b["max_x"] == 250.0
    assert b["max_y"] == 50.0


def test_parse_dxf_layers(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    layer_names = {l["name"] for l in result["layers"]}
    assert "LAYER1" in layer_names
    assert "LAYER2" in layer_names
    assert "LAYER3" in layer_names


def test_parse_dxf_geometry_count(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    assert len(result["geometries"]) == 3

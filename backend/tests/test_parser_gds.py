from services.parser_gds import parse_gds


def test_parse_gds_returns_layout_data(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    assert "bounds" in result
    assert "layers" in result
    assert "geometries" in result


def test_parse_gds_bounds(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    b = result["bounds"]
    assert b["min_x"] == 0.0
    assert b["min_y"] == 0.0
    assert b["max_x"] == 250.0
    assert b["max_y"] == 130.0


def test_parse_gds_layers(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    layers = result["layers"]
    layer_names = {l["name"] for l in layers}
    assert "1/0" in layer_names
    assert "2/0" in layer_names
    assert "3/0" in layer_names


def test_parse_gds_geometry_count(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    assert len(result["geometries"]) == 4


def test_parse_gds_geometry_structure(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    geo = result["geometries"][0]
    assert "id" in geo
    assert "type" in geo
    assert "layer" in geo
    assert "datatype" in geo
    assert "points" in geo
    assert isinstance(geo["points"], list)
    assert len(geo["points"]) >= 3

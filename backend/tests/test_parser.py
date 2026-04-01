import pytest
from services.parser import parse_layout


def test_parse_gds(sample_gds_path):
    result = parse_layout(str(sample_gds_path))
    assert len(result["geometries"]) == 4


def test_parse_dxf(sample_dxf_path):
    result = parse_layout(str(sample_dxf_path))
    assert len(result["geometries"]) == 3


def test_parse_unknown_format(tmp_path):
    f = tmp_path / "test.xyz"
    f.write_text("garbage")
    with pytest.raises(ValueError, match="Unsupported file format"):
        parse_layout(str(f))

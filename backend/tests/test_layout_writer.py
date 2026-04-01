"""Tests for layout writer service (GDS/DXF write and re-read)."""

import pytest

from services.layout_writer import write_gds, write_dxf, write_layout
from services.parser_gds import parse_gds
from services.parser_dxf import parse_dxf


def _sample_layout():
    """Create a simple layout data dict for testing."""
    return {
        "bounds": {"min_x": 0, "min_y": 0, "max_x": 100, "max_y": 50},
        "layers": [
            {"layer": 1, "datatype": 0, "name": "1/0", "polygon_count": 1},
            {"layer": 2, "datatype": 0, "name": "2/0", "polygon_count": 1},
        ],
        "geometries": [
            {
                "id": "poly_000000",
                "type": "polygon",
                "layer": 1,
                "datatype": 0,
                "points": [[0, 0], [100, 0], [100, 50], [0, 50]],
                "properties": {},
            },
            {
                "id": "poly_000001",
                "type": "polygon",
                "layer": 2,
                "datatype": 0,
                "points": [[10, 10], [90, 10], [90, 40], [10, 40]],
                "properties": {},
            },
        ],
    }


class TestWriteGDS:
    """Test GDS write and re-read."""

    def test_write_and_reread(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "output.gds")
        write_gds(layout, output)

        # Re-read and verify
        result = parse_gds(output)
        assert len(result["geometries"]) == 2
        layers_found = {g["layer"] for g in result["geometries"]}
        assert 1 in layers_found
        assert 2 in layers_found

    def test_preserves_polygon_count(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "output.gds")
        write_gds(layout, output)

        result = parse_gds(output)
        assert len(result["geometries"]) == len(layout["geometries"])

    def test_empty_layout(self, tmp_path):
        layout = {"geometries": [], "bounds": {}, "layers": []}
        output = str(tmp_path / "empty.gds")
        write_gds(layout, output)

        result = parse_gds(output)
        assert len(result["geometries"]) == 0


class TestWriteDXF:
    """Test DXF write and re-read."""

    def test_write_and_reread(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "output.dxf")
        write_dxf(layout, output)

        # Re-read and verify
        result = parse_dxf(output)
        assert len(result["geometries"]) == 2

    def test_preserves_polygon_count(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "output.dxf")
        write_dxf(layout, output)

        result = parse_dxf(output)
        assert len(result["geometries"]) == len(layout["geometries"])

    def test_empty_layout(self, tmp_path):
        layout = {"geometries": [], "bounds": {}, "layers": []}
        output = str(tmp_path / "empty.dxf")
        write_dxf(layout, output)

        result = parse_dxf(output)
        assert len(result["geometries"]) == 0


class TestWriteLayout:
    """Test the unified write_layout dispatcher."""

    def test_gds_dispatch(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "dispatch.gds")
        write_layout(layout, output, "gds")
        result = parse_gds(output)
        assert len(result["geometries"]) == 2

    def test_dxf_dispatch(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "dispatch.dxf")
        write_layout(layout, output, "dxf")
        result = parse_dxf(output)
        assert len(result["geometries"]) == 2

    def test_unsupported_type_raises(self, tmp_path):
        layout = _sample_layout()
        output = str(tmp_path / "dispatch.xyz")
        with pytest.raises(ValueError, match="Unsupported file type"):
            write_layout(layout, output, "xyz")

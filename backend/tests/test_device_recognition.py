"""Tests for geometry utilities and device recognition engine."""

import math

from services.geometry_utils import (
    polygon_bbox,
    polygon_area,
    polygon_perimeter,
    polygon_centroid,
    polygons_overlap,
    is_rectangular,
    overlap_area,
    aspect_ratio,
)
from services.parser import parse_layout
from services.device_recognition import recognize_devices


# ---------- geometry_utils tests ----------

class TestPolygonBbox:
    def test_simple_rectangle(self):
        pts = [[0, 0], [10, 0], [10, 5], [0, 5]]
        assert polygon_bbox(pts) == [0, 0, 10, 5]

    def test_negative_coords(self):
        pts = [[-5, -3], [5, -3], [5, 3], [-5, 3]]
        assert polygon_bbox(pts) == [-5, -3, 5, 3]


class TestPolygonArea:
    def test_unit_square(self):
        pts = [[0, 0], [1, 0], [1, 1], [0, 1]]
        assert polygon_area(pts) == 1.0

    def test_rectangle(self):
        pts = [[0, 0], [10, 0], [10, 5], [0, 5]]
        assert polygon_area(pts) == 50.0

    def test_triangle(self):
        pts = [[0, 0], [4, 0], [0, 3]]
        assert polygon_area(pts) == 6.0


class TestPolygonPerimeter:
    def test_unit_square(self):
        pts = [[0, 0], [1, 0], [1, 1], [0, 1]]
        assert polygon_perimeter(pts) == 4.0

    def test_rectangle(self):
        pts = [[0, 0], [10, 0], [10, 5], [0, 5]]
        assert polygon_perimeter(pts) == 30.0


class TestPolygonCentroid:
    def test_square(self):
        pts = [[0, 0], [10, 0], [10, 10], [0, 10]]
        c = polygon_centroid(pts)
        assert c == [5.0, 5.0]


class TestPolygonsOverlap:
    def test_overlapping(self):
        p1 = [[0, 0], [10, 0], [10, 10], [0, 10]]
        p2 = [[5, 5], [15, 5], [15, 15], [5, 15]]
        assert polygons_overlap(p1, p2) is True

    def test_non_overlapping(self):
        p1 = [[0, 0], [10, 0], [10, 10], [0, 10]]
        p2 = [[20, 20], [30, 20], [30, 30], [20, 30]]
        assert polygons_overlap(p1, p2) is False


class TestIsRectangular:
    def test_rectangle(self):
        pts = [[0, 0], [10, 0], [10, 5], [0, 5]]
        assert is_rectangular(pts) is True

    def test_non_rectangle(self):
        pts = [[0, 0], [10, 0], [10, 5]]
        assert is_rectangular(pts) is False

    def test_diamond(self):
        # 45-degree rotated square — should still be rectangular
        pts = [[5, 0], [10, 5], [5, 10], [0, 5]]
        assert is_rectangular(pts) is True


class TestOverlapArea:
    def test_partial_overlap(self):
        bb1 = [0, 0, 10, 10]
        bb2 = [5, 5, 15, 15]
        assert overlap_area(bb1, bb2) == 25.0

    def test_no_overlap(self):
        bb1 = [0, 0, 10, 10]
        bb2 = [20, 20, 30, 30]
        assert overlap_area(bb1, bb2) == 0.0

    def test_full_containment(self):
        bb1 = [0, 0, 50, 50]
        bb2 = [5, 5, 45, 45]
        assert overlap_area(bb1, bb2) == 40 * 40


class TestAspectRatio:
    def test_square(self):
        pts = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert aspect_ratio(pts) == 1.0

    def test_thin_strip(self):
        pts = [[0, 0], [50, 0], [50, 5], [0, 5]]
        assert aspect_ratio(pts) == 10.0


# ---------- device recognition tests ----------

LAYER_MAPPING = {
    "1/0": "ME1",
    "2/0": "ME2",
    "3/0": "TFR",
    "4/0": "VA1",
    "5/0": "GND",
}


class TestDeviceRecognition:
    def test_recognizes_capacitor(self, sample_gds_with_devices):
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        caps = [d for d in result["devices"] if d["type"] == "capacitor"]
        assert len(caps) >= 1
        cap = caps[0]
        assert "ME1" in cap["layers"]
        assert "ME2" in cap["layers"]
        assert cap["value"] > 0
        assert cap["unit"] == "pF"
        assert len(cap["polygon_ids"]) == 2

    def test_recognizes_resistor(self, sample_gds_with_devices):
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        resistors = [d for d in result["devices"] if d["type"] == "resistor"]
        assert len(resistors) >= 1
        r = resistors[0]
        assert r["layers"] == ["TFR"]
        assert r["value"] > 0
        assert r["unit"] == "Ω"

    def test_recognizes_pad(self, sample_gds_with_devices):
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        pads = [d for d in result["devices"] if d["type"] == "pad"]
        assert len(pads) >= 1
        pad = pads[0]
        assert "ME1" in pad["layers"]
        assert "ME2" in pad["layers"]
        assert "VA1" in pad["layers"]

    def test_recognizes_gnd_via(self, sample_gds_with_devices):
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        vias = [d for d in result["devices"] if d["type"] == "via_gnd"]
        assert len(vias) >= 1
        via = vias[0]
        assert "GND" in via["layers"]
        assert "ME1" in via["layers"]

    def test_device_counts(self, sample_gds_with_devices):
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        stats = result["stats"]
        assert stats["capacitors"] >= 1
        assert stats["resistors"] >= 1
        assert stats["pads"] >= 1
        assert stats["via_gnds"] >= 1
        assert stats["total"] == len(result["devices"])

    def test_exclusivity(self, sample_gds_with_devices):
        """Each polygon should be assigned to at most one device."""
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        all_poly_ids = []
        for dev in result["devices"]:
            all_poly_ids.extend(dev["polygon_ids"])
        assert len(all_poly_ids) == len(set(all_poly_ids)), \
            "Some polygons were assigned to multiple devices"

    def test_device_structure(self, sample_gds_with_devices):
        """Verify device dicts have the expected fields."""
        layout_data = parse_layout(str(sample_gds_with_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        for dev in result["devices"]:
            assert "id" in dev
            assert "type" in dev
            assert "value" in dev
            assert "unit" in dev
            assert "layers" in dev
            assert "bbox" in dev
            assert len(dev["bbox"]) == 4
            assert "polygon_ids" in dev
            assert "ports" in dev
            assert "metrics" in dev
            assert "area" in dev["metrics"]
            assert "width" in dev["metrics"]
            assert "length" in dev["metrics"]

    def test_empty_mapping(self):
        """No devices should be found with empty mapping."""
        result = recognize_devices([], {})
        assert result["devices"] == []
        assert result["stats"]["total"] == 0

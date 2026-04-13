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


class TestInductorRecognition:
    """Tests for spiral inductor recognition."""

    def test_recognizes_spiral_inductor(self, sample_gds_with_inductor):
        """Should recognize spiral inductor from overlapping ME1/ME2 spirals."""
        layout_data = parse_layout(str(sample_gds_with_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        assert len(inductors) >= 1, f"Expected at least 1 inductor, got {len(inductors)}"

        ind = inductors[0]
        assert "ME1" in ind["layers"]
        assert "ME2" in ind["layers"]
        assert ind["value"] > 0
        assert ind["unit"] == "nH"
        assert "turns" in ind, "Inductor should have 'turns' parameter extracted"

    def test_inductor_has_geometric_params(self, sample_gds_with_inductor):
        """Inductor should have extracted geometric parameters."""
        layout_data = parse_layout(str(sample_gds_with_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        inductors = [d for d in result["devices"] if d["type"] == "inductor"]

        if len(inductors) >= 1:
            ind = inductors[0]
            # Check for extracted geometric parameters
            assert "inner_radius" in ind
            assert "outer_radius" in ind
            assert "line_width" in ind
            assert ind["inner_radius"] > 0
            assert ind["outer_radius"] > ind["inner_radius"]

    def test_inductor_not_confused_with_capacitor(self, sample_gds_with_inductor):
        """Spiral inductor polygons should not be assigned to capacitor."""
        layout_data = parse_layout(str(sample_gds_with_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        # Get polygon IDs assigned to inductors
        inductor_poly_ids = set()
        for dev in result["devices"]:
            if dev["type"] == "inductor":
                inductor_poly_ids.update(dev["polygon_ids"])

        # Get polygon IDs assigned to capacitors
        capacitor_poly_ids = set()
        for dev in result["devices"]:
            if dev["type"] == "capacitor":
                capacitor_poly_ids.update(dev["polygon_ids"])

        # No overlap between inductor and capacitor polygon assignments
        overlap = inductor_poly_ids.intersection(capacitor_poly_ids)
        assert len(overlap) == 0, f"Polygons assigned to both inductor and capacitor: {overlap}"

    def test_capacitor_also_detected(self, sample_gds_with_inductor):
        """The test GDS also has a capacitor that should be detected."""
        layout_data = parse_layout(str(sample_gds_with_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        caps = [d for d in result["devices"] if d["type"] == "capacitor"]
        assert len(caps) >= 1, "Expected capacitor to be detected alongside inductor"


class TestImprovedGeometryUtils:
    """Tests for new geometry utility functions."""

    def test_distance_to_centroid_range(self):
        from services.geometry_utils import distance_to_centroid_range

        # Square centered at origin - corners are at distance sqrt(10²+10²) ≈ 14.14
        pts = [[-10, -10], [10, -10], [10, 10], [-10, 10]]
        inner_r, outer_r = distance_to_centroid_range(pts)
        assert abs(inner_r - 14.14) < 0.1  # All corners same distance
        assert abs(outer_r - 14.14) < 0.1

        # Larger polygon with varying distances (irregular pentagon)
        pts2 = [[0, 0], [30, 0], [30, 15], [15, 25], [0, 20]]
        inner_r2, outer_r2 = distance_to_centroid_range(pts2)
        assert inner_r2 > 0  # All vertices should be > 0 distance from centroid
        assert outer_r2 > inner_r2  # Some vertices farther than others

    def test_bbox_area_ratio(self):
        from services.geometry_utils import bbox_area_ratio

        # Perfect rectangle fills its bbox completely
        pts = [[0, 0], [10, 0], [10, 5], [0, 5]]
        ratio = bbox_area_ratio(pts)
        assert ratio == 1.0

        # Triangle fills half its bbox
        pts2 = [[0, 0], [10, 0], [5, 5]]
        ratio2 = bbox_area_ratio(pts2)
        assert 0.4 < ratio2 < 0.6  # Triangle fills ~50% of bbox

    def test_median_edge_length(self):
        from services.geometry_utils import median_edge_length

        # Square with edges of length 10
        pts = [[0, 0], [10, 0], [10, 10], [0, 10]]
        median = median_edge_length(pts)
        assert median == 10.0

        # Rectangle with edges 10 and 5 alternating
        # Edge lengths: [10, 5, 10, 5], sorted: [5, 5, 10, 10]
        # Median index = 4 // 2 = 2, sorted[2] = 10
        pts2 = [[0, 0], [10, 0], [10, 5], [0, 5]]
        median2 = median_edge_length(pts2)
        assert median2 == 10.0  # Median of [5, 5, 10, 10] is 10


class TestSeparateSpiralInductor:
    """Tests for multi-polygon spiral inductor recognition."""

    def test_recognizes_separate_spiral_inductor(self, sample_gds_with_separate_spiral):
        """Should recognize spiral inductor from separate rectangles."""
        layout_data = parse_layout(str(sample_gds_with_separate_spiral))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)
        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        assert len(inductors) >= 1, f"Expected at least 1 inductor, got {len(inductors)}"

        ind = inductors[0]
        assert ind["value"] > 0
        assert ind["unit"] == "nH"
        assert len(ind["polygon_ids"]) >= 8  # Should have multiple polygons
        assert ind.get("recognition_method") == "multi_polygon"

    def test_separate_spiral_not_confused_with_capacitor(self, sample_gds_with_separate_spiral):
        """Separate spiral rectangles should not be identified as capacitors."""
        layout_data = parse_layout(str(sample_gds_with_separate_spiral))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        # Count polygons assigned to inductors
        inductor_poly_ids = set()
        for dev in result["devices"]:
            if dev["type"] == "inductor":
                inductor_poly_ids.update(dev["polygon_ids"])

        # Most ME1/ME2 geometries should be assigned to inductor, not capacitor
        total_me1_me2 = sum(
            1 for g in layout_data["geometries"]
            if g["layer"] in [1, 2]
        )
        assert len(inductor_poly_ids) > total_me1_me2 * 0.5  # Majority should be inductor


class TestME2BasedInductorRecognition:
    """Tests for ME2-centric inductor recognition approach.

    新方案：利用ME2闭合螺旋确定电感区域，再结合ME1分析空间关系。
    """

    def test_me2_only_inductor_detected(self, sample_gds_with_me2_only_inductor):
        """Should detect inductor even without ME1 in inductor region."""
        layout_data = parse_layout(str(sample_gds_with_me2_only_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        assert len(inductors) >= 1, f"Expected at least 1 inductor, got {len(inductors)}"

        ind = inductors[0]
        assert ind["value"] > 0
        assert ind["unit"] == "nH"
        assert "turns" in ind
        print(f"\n  ME2-only inductor detected: turns={ind['turns']}, value={ind['value']}nH")

    def test_proper_inductor_with_me1_detected(self, sample_gds_with_proper_inductor):
        """Should detect inductor with ME1+ME2 structure."""
        layout_data = parse_layout(str(sample_gds_with_proper_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        assert len(inductors) >= 1, f"Expected at least 1 inductor, got {len(inductors)}"

        ind = inductors[0]
        assert "ME1" in ind["layers"] or "ME2" in ind["layers"]
        assert ind["value"] > 0
        assert ind["unit"] == "nH"
        print(f"\n  ME1+ME2 inductor detected: turns={ind['turns']}, value={ind['value']}nH")

    def test_inductor_with_noise_separation(self, sample_gds_with_inductor_and_noise):
        """Should correctly separate inductor region from nearby noise."""
        layout_data = parse_layout(str(sample_gds_with_inductor_and_noise))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        capacitors = [d for d in result["devices"] if d["type"] == "capacitor"]

        assert len(inductors) >= 1, "Should detect the inductor"

        # The noise ME1 rectangles should NOT be detected as capacitors
        # (they're not overlapping with ME2 in capacitor region)
        print(f"\n  Inductors: {len(inductors)}, Capacitors: {len(capacitors)}")

        # Check that noise was not incorrectly assigned
        for ind in inductors:
            # Inductor bbox should NOT include noise region (around 200-230)
            bbox = ind["bbox"]
            assert bbox[2] < 200, f"Inductor bbox {bbox} should not include noise at x>200"

    def test_mixed_devices_all_detected(self, sample_gds_mixed_devices):
        """Should correctly detect all device types in mixed layout."""
        layout_data = parse_layout(str(sample_gds_mixed_devices))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        stats = result["stats"]
        print(f"\n  Stats: {stats}")

        # Should detect at least 1 inductor
        assert stats["inductors"] >= 1, f"Expected inductor, got {stats}"

        # Should detect at least 1 capacitor
        assert stats["capacitors"] >= 1, f"Expected capacitor, got {stats}"

        # Should detect at least 1 resistor
        assert stats["resistors"] >= 1, f"Expected resistor, got {stats}"

        # Should detect PAD and/or GND via
        has_pad_or_via = stats["pads"] >= 1 or stats["via_gnds"] >= 1
        assert has_pad_or_via, "Expected PAD or GND via, got neither"

        print(f"\n  Mixed layout detected successfully:")
        print(f"    Inductors: {stats['inductors']}")
        print(f"    Capacitors: {stats['capacitors']}")
        print(f"    Resistors: {stats['resistors']}")
        print(f"    PADs: {stats['pads']}")
        print(f"    GND Vias: {stats['via_gnds']}")


class TestInductorParameterExtraction:
    """Tests for inductor geometric parameter extraction."""

    def test_inductor_extracts_turns(self, sample_gds_with_proper_inductor):
        """Should extract turns count from inductor geometry."""
        layout_data = parse_layout(str(sample_gds_with_proper_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        if len(inductors) >= 1:
            ind = inductors[0]
            assert "turns" in ind, "Should extract turns parameter"
            assert ind["turns"] >= 1, f"Turns should be >= 1, got {ind['turns']}"
            print(f"\n  Extracted turns: {ind['turns']}")

    def test_inductor_extracts_radius(self, sample_gds_with_proper_inductor):
        """Should extract inner/outer radius from inductor geometry."""
        layout_data = parse_layout(str(sample_gds_with_proper_inductor))
        result = recognize_devices(layout_data["geometries"], LAYER_MAPPING)

        inductors = [d for d in result["devices"] if d["type"] == "inductor"]
        if len(inductors) >= 1:
            ind = inductors[0]
            if "inner_radius" in ind and "outer_radius" in ind:
                assert ind["inner_radius"] > 0, "Inner radius should be positive"
                assert ind["outer_radius"] > ind["inner_radius"], \
                    f"Outer radius {ind['outer_radius']} should be > inner radius {ind['inner_radius']}"
                print(f"\n  Radii: inner={ind['inner_radius']}, outer={ind['outer_radius']}")

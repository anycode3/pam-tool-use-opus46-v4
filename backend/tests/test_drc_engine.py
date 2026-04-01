"""Tests for the DRC engine."""

import pytest

from services.drc_engine import (
    run_drc,
    parse_rules,
    parse_rule_file,
    validate_rule,
)


def _make_layout(geometries):
    """Helper to build a minimal layout_data dict."""
    return {"geometries": geometries, "layers": [], "bounds": {}}


def _rect_geom(gid, layer, datatype, x1, y1, x2, y2):
    """Create a rectangular geometry dict."""
    return {
        "id": gid,
        "type": "polygon",
        "layer": layer,
        "datatype": datatype,
        "points": [[x1, y1], [x2, y1], [x2, y2], [x1, y2]],
        "properties": {},
    }


# ---- Layer mapping used across tests ----
MAPPING = {"1/0": "ME1", "2/0": "ME2", "3/0": "TFR"}


class TestMinWidth:
    def test_violation(self):
        """A narrow polygon should trigger min_width violation."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 100, 3),  # width=100, height=3 → min=3
        ])
        rules = parse_rules([
            {"type": "min_width", "layer": "ME1", "value": 5.0, "description": "ME1 min width"},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        v = violations[0]
        assert v["rule_type"] == "min_width"
        assert v["actual_value"] == 3.0
        assert v["required_value"] == 5.0
        assert v["polygon_id"] == "p1"

    def test_passing(self):
        """A wide polygon should pass min_width check."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 100, 50),  # min dim = 50
        ])
        rules = parse_rules([
            {"type": "min_width", "layer": "ME1", "value": 5.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0

    def test_exact_boundary(self):
        """Polygon exactly at threshold should pass."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 100, 5),  # min dim = 5
        ])
        rules = parse_rules([
            {"type": "min_width", "layer": "ME1", "value": 5.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0


class TestMaxWidth:
    def test_violation(self):
        """A wide polygon should trigger max_width violation."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 200, 50),  # max dim = 200
        ])
        rules = parse_rules([
            {"type": "max_width", "layer": "ME1", "value": 100.0, "description": "ME1 max width"},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        assert violations[0]["actual_value"] == 200.0

    def test_passing(self):
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 50, 30),  # max dim = 50
        ])
        rules = parse_rules([
            {"type": "max_width", "layer": "ME1", "value": 100.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0


class TestMinArea:
    def test_violation(self):
        """A small polygon should trigger min_area violation."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 2, 3),  # area = 6
        ])
        rules = parse_rules([
            {"type": "min_area", "layer": "ME1", "value": 10.0, "description": "ME1 min area"},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        assert violations[0]["actual_value"] == 6.0
        assert violations[0]["required_value"] == 10.0

    def test_passing(self):
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),  # area = 100
        ])
        rules = parse_rules([
            {"type": "min_area", "layer": "ME1", "value": 10.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0


class TestMinSpacing:
    def test_violation_same_layer(self):
        """Two polygons too close on same layer should trigger spacing violation."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),
            _rect_geom("p2", 1, 0, 12, 0, 22, 10),  # gap = 2
        ])
        rules = parse_rules([
            {"type": "min_spacing", "layer": "ME1", "value": 5.0, "description": "ME1 spacing"},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        assert violations[0]["actual_value"] == 2.0

    def test_passing_same_layer(self):
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),
            _rect_geom("p2", 1, 0, 20, 0, 30, 10),  # gap = 10
        ])
        rules = parse_rules([
            {"type": "min_spacing", "layer": "ME1", "value": 5.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0

    def test_cross_layer_violation(self):
        """Spacing between two different layers."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),
            _rect_geom("p2", 2, 0, 11, 0, 21, 10),  # gap = 1
        ])
        rules = parse_rules([
            {"type": "min_spacing", "layer": "ME1", "layer2": "ME2", "value": 3.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        assert violations[0]["actual_value"] == 1.0

    def test_overlapping_bbox_zero_spacing(self):
        """Overlapping bboxes should report 0 spacing."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),
            _rect_geom("p2", 1, 0, 5, 0, 15, 10),  # overlapping
        ])
        rules = parse_rules([
            {"type": "min_spacing", "layer": "ME1", "value": 5.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        assert violations[0]["actual_value"] == 0.0


class TestMinOverlap:
    def test_violation(self):
        """Partially overlapping polygons with insufficient overlap area."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),
            _rect_geom("p2", 2, 0, 8, 0, 18, 10),  # overlap = 2*10 = 20
        ])
        rules = parse_rules([
            {"type": "min_overlap", "layer": "ME1", "layer2": "ME2", "value": 50.0, "description": "ME1-ME2 overlap"},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 1
        assert violations[0]["actual_value"] == 20.0

    def test_passing(self):
        """Sufficient overlap should pass."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 50, 50),
            _rect_geom("p2", 2, 0, 5, 5, 45, 45),  # overlap = 40*40 = 1600
        ])
        rules = parse_rules([
            {"type": "min_overlap", "layer": "ME1", "layer2": "ME2", "value": 50.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0

    def test_no_overlap_not_reported(self):
        """Non-overlapping polygons should NOT be reported as violation."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 10, 10),
            _rect_geom("p2", 2, 0, 100, 100, 110, 110),  # no overlap
        ])
        rules = parse_rules([
            {"type": "min_overlap", "layer": "ME1", "layer2": "ME2", "value": 50.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0


class TestCleanLayout:
    def test_no_violations(self):
        """A layout that satisfies all rules should produce no violations."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 100, 50),
            _rect_geom("p2", 1, 0, 200, 0, 300, 50),
            _rect_geom("p3", 2, 0, 5, 5, 95, 45),
        ])
        rules = parse_rules([
            {"type": "min_width", "layer": "ME1", "value": 5.0},
            {"type": "min_area", "layer": "ME1", "value": 10.0},
            {"type": "min_spacing", "layer": "ME1", "value": 50.0},
            {"type": "max_width", "layer": "ME1", "value": 500.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0


class TestMultipleRules:
    def test_multiple_violations(self):
        """Multiple rules can trigger multiple violations."""
        layout = _make_layout([
            _rect_geom("p1", 1, 0, 0, 0, 100, 2),   # narrow (min_dim=2) and small area=200
            _rect_geom("p2", 1, 0, 105, 0, 205, 2),  # narrow, small, close (gap=5)
        ])
        rules = parse_rules([
            {"type": "min_width", "layer": "ME1", "value": 5.0},
            {"type": "min_spacing", "layer": "ME1", "value": 10.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        # 2 width violations + 1 spacing violation = 3
        assert len(violations) == 3
        types = [v["rule_type"] for v in violations]
        assert types.count("min_width") == 2
        assert types.count("min_spacing") == 1


class TestUnmappedLayer:
    def test_unmapped_layer_ignored(self):
        """Geometries on unmapped layers should be ignored."""
        layout = _make_layout([
            _rect_geom("p1", 99, 0, 0, 0, 1, 1),  # layer 99 not in mapping
        ])
        rules = parse_rules([
            {"type": "min_width", "layer": "ME1", "value": 5.0},
        ])
        violations = run_drc(layout, rules, MAPPING)
        assert len(violations) == 0


class TestValidateRule:
    def test_valid_rule(self):
        assert validate_rule({"type": "min_width", "layer": "ME1", "value": 5.0}) is None

    def test_invalid_type(self):
        err = validate_rule({"type": "bad_type", "layer": "ME1", "value": 5.0})
        assert err is not None
        assert "Invalid rule type" in err

    def test_missing_layer(self):
        err = validate_rule({"type": "min_width", "value": 5.0})
        assert err is not None

    def test_missing_value(self):
        err = validate_rule({"type": "min_width", "layer": "ME1"})
        assert err is not None

    def test_min_overlap_requires_layer2(self):
        err = validate_rule({"type": "min_overlap", "layer": "ME1", "value": 5.0})
        assert err is not None
        assert "layer2" in err


class TestParseRuleFile:
    def test_parse_json(self):
        content = '{"rules": [{"type": "min_width", "layer": "ME1", "value": 5.0}]}'
        rules = parse_rule_file(content)
        assert len(rules) == 1
        assert rules[0]["type"] == "min_width"
        assert rules[0]["value"] == 5.0
        assert rules[0]["id"]  # auto-generated

    def test_parse_with_id(self):
        content = '{"rules": [{"id": "r1", "type": "min_area", "layer": "ME1", "value": 10}]}'
        rules = parse_rule_file(content)
        assert rules[0]["id"] == "r1"

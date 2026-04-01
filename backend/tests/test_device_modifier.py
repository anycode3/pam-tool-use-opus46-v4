"""Tests for device modification service."""

import math
import pytest

from services.device_modifier import modify_device, apply_modifications


def _make_capacitor(polygon_ids=None, value=1.0):
    """Create a test capacitor device."""
    if polygon_ids is None:
        polygon_ids = ["poly_000000", "poly_000001"]
    return {
        "id": "dev_001",
        "type": "capacitor",
        "value": value,
        "unit": "pF",
        "layers": ["ME1", "ME2"],
        "bbox": [0, 0, 50, 50],
        "polygon_ids": polygon_ids,
        "metrics": {"area": 2500, "width": 50, "length": 50},
    }


def _make_resistor(polygon_ids=None, value=500.0):
    """Create a test resistor device."""
    if polygon_ids is None:
        polygon_ids = ["poly_000002"]
    return {
        "id": "dev_002",
        "type": "resistor",
        "value": value,
        "unit": "Ohm",
        "layers": ["TFR"],
        "bbox": [100, 0, 200, 10],
        "polygon_ids": polygon_ids,
        "metrics": {"area": 1000, "width": 10, "length": 100},
    }


def _make_inductor(polygon_ids=None, value=2.0):
    """Create a test inductor device."""
    if polygon_ids is None:
        polygon_ids = ["poly_000003"]
    return {
        "id": "dev_003",
        "type": "inductor",
        "value": value,
        "unit": "nH",
        "layers": ["ME1"],
        "bbox": [0, 0, 100, 100],
        "polygon_ids": polygon_ids,
        "metrics": {"area": 10000, "width": 100, "length": 100},
    }


def _make_layout(*polygon_defs):
    """Create a layout_data dict from polygon definitions.

    Each polygon_def is (id, layer, datatype, points).
    """
    geometries = []
    for pid, layer, datatype, points in polygon_defs:
        geometries.append({
            "id": pid,
            "type": "polygon",
            "layer": layer,
            "datatype": datatype,
            "points": points,
            "properties": {},
        })
    return {
        "bounds": {"min_x": 0, "min_y": 0, "max_x": 500, "max_y": 500},
        "layers": [],
        "geometries": geometries,
    }


class TestCapacitorAutoModification:
    """Capacitor auto mode: area scales with value ratio."""

    def test_value_doubles_area_doubles(self):
        cap = _make_capacitor(value=1.0)
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
            ("poly_000001", 2, 0, [[5, 5], [45, 5], [45, 45], [5, 45]]),
        )
        mod = modify_device(cap, layout, new_value=2.0, mode="auto")

        assert mod["device_id"] == "dev_001"
        assert mod["device_type"] == "capacitor"
        assert mod["old_value"] == 1.0
        assert mod["new_value"] == 2.0
        assert len(mod["changes"]) == 2

        # For a square polygon (50x50), doubling area with one side fixed:
        # new_width = 50 * 2 = 100 (since w == h, it picks width)
        for change in mod["changes"]:
            old_pts = change["old_points"]
            new_pts = change["new_points"]
            assert len(new_pts) == 4
            # Area should approximately double
            old_w = max(p[0] for p in old_pts) - min(p[0] for p in old_pts)
            old_h = max(p[1] for p in old_pts) - min(p[1] for p in old_pts)
            new_w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
            new_h = max(p[1] for p in new_pts) - min(p[1] for p in new_pts)
            old_area = old_w * old_h
            new_area = new_w * new_h
            assert abs(new_area / old_area - 2.0) < 0.01

    def test_value_halves_area_halves(self):
        cap = _make_capacitor(value=2.0)
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [100, 0], [100, 50], [0, 50]]),
            ("poly_000001", 2, 0, [[0, 0], [100, 0], [100, 50], [0, 50]]),
        )
        mod = modify_device(cap, layout, new_value=1.0, mode="auto")

        for change in mod["changes"]:
            new_pts = change["new_points"]
            new_w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
            new_h = max(p[1] for p in new_pts) - min(p[1] for p in new_pts)
            new_area = new_w * new_h
            # Original area was 5000, should be 2500 now
            assert abs(new_area - 2500) < 1


class TestResistorAutoModification:
    """Resistor auto mode: length scales with value ratio."""

    def test_value_doubles_length_doubles(self):
        res = _make_resistor(value=500.0)
        layout = _make_layout(
            ("poly_000002", 3, 0, [[100, 0], [200, 0], [200, 10], [100, 10]]),
        )
        mod = modify_device(res, layout, new_value=1000.0, mode="auto")

        assert mod["device_id"] == "dev_002"
        assert mod["device_type"] == "resistor"
        assert len(mod["changes"]) == 1

        change = mod["changes"][0]
        old_pts = change["old_points"]
        new_pts = change["new_points"]
        old_length = max(p[0] for p in old_pts) - min(p[0] for p in old_pts)
        new_length = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
        # Length should double (100 -> 200)
        assert abs(new_length / old_length - 2.0) < 0.01

        # Width should stay the same
        old_width = max(p[1] for p in old_pts) - min(p[1] for p in old_pts)
        new_width = max(p[1] for p in new_pts) - min(p[1] for p in new_pts)
        assert abs(new_width - old_width) < 0.01

    def test_value_halves_length_halves(self):
        res = _make_resistor(value=1000.0)
        layout = _make_layout(
            ("poly_000002", 3, 0, [[100, 0], [300, 0], [300, 10], [100, 10]]),
        )
        mod = modify_device(res, layout, new_value=500.0, mode="auto")

        change = mod["changes"][0]
        new_pts = change["new_points"]
        new_length = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
        assert abs(new_length - 100) < 0.01


class TestManualMode:
    """Test manual mode with specified dimensions."""

    def test_capacitor_manual(self):
        cap = _make_capacitor(value=1.0)
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
            ("poly_000001", 2, 0, [[5, 5], [45, 5], [45, 45], [5, 45]]),
        )
        mod = modify_device(
            cap, layout, new_value=5.0, mode="manual",
            manual_params={"width": 70, "length": 30},
        )
        for change in mod["changes"]:
            new_pts = change["new_points"]
            new_w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
            new_h = max(p[1] for p in new_pts) - min(p[1] for p in new_pts)
            assert abs(new_w - 70) < 0.01
            assert abs(new_h - 30) < 0.01

    def test_resistor_manual(self):
        res = _make_resistor(value=500.0)
        layout = _make_layout(
            ("poly_000002", 3, 0, [[100, 0], [200, 0], [200, 10], [100, 10]]),
        )
        mod = modify_device(
            res, layout, new_value=1000.0, mode="manual",
            manual_params={"width": 20, "length": 150},
        )
        change = mod["changes"][0]
        new_pts = change["new_points"]
        new_w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
        new_h = max(p[1] for p in new_pts) - min(p[1] for p in new_pts)
        assert abs(new_w - 20) < 0.01
        assert abs(new_h - 150) < 0.01

    def test_inductor_manual_scale(self):
        ind = _make_inductor(value=2.0)
        layout = _make_layout(
            ("poly_000003", 1, 0, [[0, 0], [100, 0], [100, 100], [0, 100]]),
        )
        mod = modify_device(
            ind, layout, new_value=8.0, mode="manual",
            manual_params={"scale_factor": 2.0},
        )
        change = mod["changes"][0]
        new_pts = change["new_points"]
        new_w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
        # Scale factor 2.0 on 100-wide polygon -> 200
        assert abs(new_w - 200) < 0.01

    def test_manual_missing_params_raises(self):
        cap = _make_capacitor(value=1.0)
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
        )
        with pytest.raises(ValueError, match="Manual mode requires"):
            modify_device(cap, layout, new_value=2.0, mode="manual")


class TestInductorAutoModification:
    """Inductor auto mode: uniform scale by sqrt(ratio)."""

    def test_value_quadruples_scale_doubles(self):
        ind = _make_inductor(value=1.0)
        layout = _make_layout(
            ("poly_000003", 1, 0, [[0, 0], [100, 0], [100, 100], [0, 100]]),
        )
        mod = modify_device(ind, layout, new_value=4.0, mode="auto")

        change = mod["changes"][0]
        new_pts = change["new_points"]
        new_w = max(p[0] for p in new_pts) - min(p[0] for p in new_pts)
        # sqrt(4) = 2, so width should double
        assert abs(new_w - 200) < 0.01


class TestModificationPreviewStructure:
    """Validate the modification preview data structure."""

    def test_structure_has_required_fields(self):
        cap = _make_capacitor(value=1.0)
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
        )
        mod = modify_device(cap, layout, new_value=2.0, mode="auto")

        assert "id" in mod
        assert mod["id"].startswith("mod_")
        assert "device_id" in mod
        assert "device_type" in mod
        assert "old_value" in mod
        assert "new_value" in mod
        assert "changes" in mod
        assert isinstance(mod["changes"], list)

        for change in mod["changes"]:
            assert "polygon_id" in change
            assert "old_points" in change
            assert "new_points" in change

    def test_unsupported_type_raises(self):
        dev = {"id": "dev_x", "type": "transistor", "value": 1.0, "polygon_ids": []}
        layout = _make_layout()
        with pytest.raises(ValueError, match="Unsupported device type"):
            modify_device(dev, layout, new_value=2.0)

    def test_negative_value_raises(self):
        cap = _make_capacitor(value=1.0)
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
        )
        with pytest.raises(ValueError, match="positive"):
            modify_device(cap, layout, new_value=-1.0)


class TestApplyModifications:
    """Test applying modifications to layout data."""

    def test_apply_updates_points(self):
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
        )
        mods = [{
            "id": "mod_001",
            "device_id": "dev_001",
            "device_type": "capacitor",
            "old_value": 1.0,
            "new_value": 2.0,
            "changes": [{
                "polygon_id": "poly_000000",
                "old_points": [[0, 0], [50, 0], [50, 50], [0, 50]],
                "new_points": [[0, 0], [100, 0], [100, 50], [0, 50]],
            }],
        }]

        result = apply_modifications(layout, mods)
        geo = result["geometries"][0]
        assert geo["points"] == [[0, 0], [100, 0], [100, 50], [0, 50]]

    def test_apply_does_not_mutate_original(self):
        layout = _make_layout(
            ("poly_000000", 1, 0, [[0, 0], [50, 0], [50, 50], [0, 50]]),
        )
        mods = [{
            "id": "mod_001",
            "device_id": "dev_001",
            "device_type": "capacitor",
            "old_value": 1.0,
            "new_value": 2.0,
            "changes": [{
                "polygon_id": "poly_000000",
                "old_points": [[0, 0], [50, 0], [50, 50], [0, 50]],
                "new_points": [[0, 0], [100, 0], [100, 50], [0, 50]],
            }],
        }]

        apply_modifications(layout, mods)
        # Original should be unchanged
        assert layout["geometries"][0]["points"] == [[0, 0], [50, 0], [50, 50], [0, 50]]

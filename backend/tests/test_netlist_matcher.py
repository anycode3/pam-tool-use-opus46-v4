import pytest
from services.spice_models import SpiceDevice, SpiceNetlist, MatchResult
from services.netlist_matcher import match_devices, compute_confidence

LAYOUT_DEVICES = [
    {"id": "dev_001", "type": "inductor", "value": 5.0, "unit": "nH"},
    {"id": "dev_002", "type": "capacitor", "value": 2.0, "unit": "pF"},
    {"id": "dev_003", "type": "resistor", "value": 100.0, "unit": "Ω"},
]


def test_match_identical_values():
    spice_devices = [
        SpiceDevice(device_type="inductor", instance_name="L1", nodes=["a", "b"], parameters={"value": "5nH"}),
        SpiceDevice(device_type="capacitor", instance_name="C1", nodes=["b", "c"], parameters={"value": "2pF"}),
        SpiceDevice(device_type="resistor", instance_name="R1", nodes=["a", "c"], parameters={"value": "100"}),
    ]
    results = match_devices(spice_devices, LAYOUT_DEVICES)

    assert len(results) == 3
    l1_match = next(r for r in results if r.spice_device.instance_name == "L1")
    assert l1_match.layout_geometry_id == "dev_001"
    assert l1_match.confidence == 1.0


def test_match_close_values():
    spice_devices = [
        SpiceDevice(device_type="inductor", instance_name="L1", nodes=["a", "b"], parameters={"value": "5nH"}),
    ]
    layout = [{"id": "dev_001", "type": "inductor", "value": 5.05, "unit": "nH"}]
    results = match_devices(spice_devices, layout)

    assert len(results) == 1
    assert results[0].confidence > 0.9


def test_no_match_wrong_type():
    spice_devices = [
        SpiceDevice(device_type="inductor", instance_name="L1", nodes=["a", "b"], parameters={"value": "5nH"}),
    ]
    layout = [{"id": "dev_001", "type": "capacitor", "value": 5.0, "unit": "pF"}]
    results = match_devices(spice_devices, layout)

    assert len(results) == 0

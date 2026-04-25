"""Tests for SpiceDataClasses: SpiceDevice, SpiceNetlist, MatchResult."""

import pytest
from services.spice_models import SpiceDevice, SpiceNetlist, MatchResult


class TestSpiceDevice:
    def test_device_creation(self):
        dev = SpiceDevice(
            device_type="L",
            instance_name="L1",
            nodes=["VSS", "OUT"],
            parameters={"L": "10nH"},
        )
        assert dev.device_type == "L"
        assert dev.instance_name == "L1"
        assert dev.nodes == ["VSS", "OUT"]
        assert dev.parameters == {"L": "10nH"}

    def test_device_default_empty_params(self):
        dev = SpiceDevice(device_type="R", instance_name="R1", nodes=["1", "2"])
        assert dev.parameters == {}

    def test_device_str(self):
        dev = SpiceDevice(device_type="C", instance_name="C1", nodes=["VCC", "GND"])
        assert "C1" in str(dev)

    def test_device_equality(self):
        dev1 = SpiceDevice(device_type="L", instance_name="L1", nodes=["a", "b"])
        dev2 = SpiceDevice(device_type="L", instance_name="L1", nodes=["a", "b"])
        assert dev1 == dev2


class TestSpiceNetlist:
    def test_netlist_creation(self):
        netlist = SpiceNetlist(title="Test Circuit")
        assert netlist.title == "Test Circuit"
        assert netlist.devices == []

    def test_add_device(self):
        netlist = SpiceNetlist(title="My Circuit")
        dev = SpiceDevice(device_type="R", instance_name="R1", nodes=["1", "2"])
        netlist.add_device(dev)
        assert len(netlist.devices) == 1
        assert netlist.devices[0] == dev

    def test_add_multiple_devices(self):
        netlist = SpiceNetlist(title="My Circuit")
        devs = [
            SpiceDevice(device_type="R", instance_name="R1", nodes=["1", "2"]),
            SpiceDevice(device_type="C", instance_name="C1", nodes=["1", "3"]),
        ]
        for d in devs:
            netlist.add_device(d)
        assert len(netlist.devices) == 2

    def test_to_spice_string(self):
        netlist = SpiceNetlist(title="Simple Circuit")
        netlist.add_device(
            SpiceDevice(device_type="R", instance_name="R1", nodes=["1", "2"], parameters={"R": "1k"})
        )
        spice_str = netlist.to_spice_string()
        assert "Simple Circuit" in spice_str
        assert "R1 1 2 R=1k" in spice_str

    def test_to_spice_string_multiple_devices(self):
        netlist = SpiceNetlist(title="RC Circuit")
        netlist.add_device(SpiceDevice(device_type="R", instance_name="R1", nodes=["VCC", "OUT"]))
        netlist.add_device(SpiceDevice(device_type="C", instance_name="C1", nodes=["OUT", "GND"]))
        spice_str = netlist.to_spice_string()
        assert "R1" in spice_str
        assert "C1" in spice_str


class TestMatchResult:
    def test_match_result_creation(self):
        result = MatchResult(
            layout_geometry_id="geo_001",
            spice_device=SpiceDevice(
                device_type="L",
                instance_name="L1",
                nodes=["A", "B"],
            ),
            confidence=0.95,
        )
        assert result.layout_geometry_id == "geo_001"
        assert result.spice_device.instance_name == "L1"
        assert result.confidence == 0.95

    def test_match_result_default_confidence(self):
        result = MatchResult(
            layout_geometry_id="geo_002",
            spice_device=SpiceDevice(device_type="C", instance_name="C1", nodes=["1", "2"]),
        )
        assert result.confidence == 0.0

    def test_match_result_repr(self):
        result = MatchResult(
            layout_geometry_id="geo_003",
            spice_device=SpiceDevice(device_type="R", instance_name="R1", nodes=["a", "b"]),
            confidence=0.85,
        )
        repr_str = repr(result)
        assert "geo_003" in repr_str
        assert "R1" in repr_str
        assert "0.85" in repr_str

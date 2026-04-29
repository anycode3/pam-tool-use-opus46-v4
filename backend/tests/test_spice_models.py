"""Tests for SpiceDataClasses: SpiceDevice, SpiceNetlist, MatchResult."""

import pytest
from services.spice_models import SpiceDevice, SpiceNetlist, MatchResult


class TestSpiceDevice:
    def test_device_creation(self):
        dev = SpiceDevice(
            device_type="inductor",
            instance_name="L1",
            value=10.0,
            unit="nH",
            nets=["VSS", "OUT"],
        )
        assert dev.device_type == "inductor"
        assert dev.instance_name == "L1"
        assert dev.value == 10.0
        assert dev.unit == "nH"
        assert dev.nets == ["VSS", "OUT"]
        assert dev.subcircuit == ""

    def test_device_with_subcircuit(self):
        dev = SpiceDevice(
            device_type="capacitor",
            instance_name="C1",
            value=2.0,
            unit="pF",
            nets=["VCC", "GND"],
            subcircuit="MYCAP",
        )
        assert dev.subcircuit == "MYCAP"

    def test_device_str(self):
        dev = SpiceDevice(device_type="capacitor", instance_name="C1", value=2.0, unit="pF", nets=["VCC", "GND"])
        assert "C1" in str(dev)

    def test_device_equality(self):
        dev1 = SpiceDevice(device_type="inductor", instance_name="L1", value=5.0, unit="nH", nets=["a", "b"])
        dev2 = SpiceDevice(device_type="inductor", instance_name="L1", value=5.0, unit="nH", nets=["a", "b"])
        assert dev1 == dev2


class TestSpiceNetlist:
    def test_netlist_creation(self):
        netlist = SpiceNetlist()
        assert netlist.devices == []
        assert netlist.subcircuits == {}
        assert netlist.global_nets == set()

    def test_add_device(self):
        netlist = SpiceNetlist()
        dev = SpiceDevice(device_type="resistor", instance_name="R1", value=100.0, unit="Ω", nets=["1", "2"])
        netlist.devices.append(dev)
        assert len(netlist.devices) == 1
        assert netlist.devices[0] == dev

    def test_add_multiple_devices(self):
        netlist = SpiceNetlist()
        devs = [
            SpiceDevice(device_type="resistor", instance_name="R1", value=100.0, unit="Ω", nets=["1", "2"]),
            SpiceDevice(device_type="capacitor", instance_name="C1", value=2.0, unit="pF", nets=["1", "3"]),
        ]
        netlist.devices.extend(devs)
        assert len(netlist.devices) == 2

    def test_subcircuits(self):
        netlist = SpiceNetlist()
        cap_dev = SpiceDevice(device_type="capacitor", instance_name="X1.C1", value=2.0, unit="pF", nets=["a", "b"], subcircuit="MYCAP")
        netlist.subcircuits["MYCAP"] = [cap_dev]
        assert "MYCAP" in netlist.subcircuits
        assert len(netlist.subcircuits["MYCAP"]) == 1

    def test_global_nets(self):
        netlist = SpiceNetlist()
        dev = SpiceDevice(device_type="inductor", instance_name="L1", value=5.0, unit="nH", nets=["VCC", "OUT"])
        for net in dev.nets:
            if net.lower() != "gnd":
                netlist.global_nets.add(net)
        assert "VCC" in netlist.global_nets
        assert "OUT" in netlist.global_nets


class TestMatchResult:
    def test_match_result_creation(self):
        result = MatchResult(
            spice_name="L1",
            layout_id="dev_001",
            spice_value=5.0,
            layout_value=5.0,
            confidence=0.95,
            match_method="value_exact",
        )
        assert result.spice_name == "L1"
        assert result.layout_id == "dev_001"
        assert result.spice_value == 5.0
        assert result.layout_value == 5.0
        assert result.confidence == 0.95
        assert result.match_method == "value_exact"

    def test_match_result_default_confidence(self):
        result = MatchResult(
            spice_name="C1",
            layout_id="dev_002",
            spice_value=2.0,
            layout_value=2.0,
            confidence=0.0,
            match_method="value_close",
        )
        assert result.confidence == 0.0

    def test_match_result_repr(self):
        result = MatchResult(
            spice_name="R1",
            layout_id="dev_003",
            spice_value=100.0,
            layout_value=100.0,
            confidence=0.85,
            match_method="value_exact",
        )
        repr_str = repr(result)
        assert "dev_003" in repr_str
        assert "R1" in repr_str
        assert "0.85" in repr_str

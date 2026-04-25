import pytest
from services.spice_parser import parse_spice, SpiceNetlist

SIMPLE_NETLIST = """
* Simple test netlist
L1 net_a net_b 5nH
C1 net_b net_c 2pF
R1 net_a gnd 100
.END
"""

def test_parse_simple_netlist():
    netlist = parse_spice(SIMPLE_NETLIST)
    assert len(netlist.devices) == 3
    assert netlist.devices[0].instance_name == "L1"
    assert netlist.devices[0].device_type == "inductor"
    assert netlist.devices[0].value == 5.0
    assert netlist.devices[0].unit == "nH"
    assert netlist.devices[0].nets == ["net_a", "net_b"]

def test_parse_engineering_notation():
    netlist = parse_spice("L1 a b 5.6n\n.END")
    assert netlist.devices[0].value == 5.6
    assert netlist.devices[0].unit == "nH"

def test_parse_k_notation():
    netlist = parse_spice("R1 a b 4.7k\n.END")
    assert netlist.devices[0].value == 4.7
    assert netlist.devices[0].unit == "k"

def test_parse_subcircuit():
    netlist = parse_spice("""
.SUBCKT top in out
L1 in mid 3nH
C1 mid out 1pF
.ENDS top
.END
""")
    assert len(netlist.subcircuits) == 1
    assert "top" in netlist.subcircuits
    assert len(netlist.subcircuits["top"]) == 2
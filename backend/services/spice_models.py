"""Spice data classes for netlist representation and layout-device matching."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpiceDevice:
    """Represents a single SPICE device instance.

    Attributes:
        instance_name: Device name (e.g., "L1", "C2", "R3")
        device_type: Device type ("inductor", "capacitor", "resistor")
        value: Numeric value (already parsed to base SI units - H, F, or Ohm)
        unit: Unit string ("nH", "pF", "Ω", etc.)
        nets: List of connected net names
        subcircuit: Subcircuit name if inside a .SUBCKT, "" for top-level
    """

    instance_name: str
    device_type: str
    value: float
    unit: str
    nets: list[str] = field(default_factory=list)
    subcircuit: str = ""


@dataclass
class SpiceNetlist:
    """Represents a SPICE netlist containing multiple devices.

    Attributes:
        devices: List of top-level devices
        subcircuits: Dict of subcircuit_name -> list of devices
        global_nets: Set of global net names (e.g., "gnd", "vdd")
    """

    devices: list[SpiceDevice] = field(default_factory=list)
    subcircuits: dict[str, list[SpiceDevice]] = field(default_factory=dict)
    global_nets: set[str] = field(default_factory=set)


@dataclass
class MatchResult:
    """Result of matching a SPICE device to a layout device.

    Attributes:
        spice_name: SPICE instance name (e.g., "L1")
        layout_id: Layout device ID (e.g., "dev_001")
        spice_value: SPICE device value
        layout_value: Layout device value
        confidence: Match confidence score (0.0 - 1.0)
        match_method: How the match was determined ("value_exact", "value_close")
    """

    spice_name: str
    layout_id: str
    spice_value: float
    layout_value: float
    confidence: float
    match_method: str

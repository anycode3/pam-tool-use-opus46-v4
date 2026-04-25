"""Spice data classes for netlist representation and layout-device matching."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SpiceDevice:
    """Represents a single SPICE device instance."""

    device_type: str
    instance_name: str
    nodes: list[str]
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class SpiceNetlist:
    """Represents a SPICE netlist containing multiple devices."""

    title: str
    devices: list[SpiceDevice] = field(default_factory=list)

    def add_device(self, device: SpiceDevice) -> None:
        """Add a device to the netlist."""
        self.devices.append(device)

    def to_spice_string(self) -> str:
        """Generate SPICE netlist string."""
        lines = [self.title]
        for dev in self.devices:
            param_str = " ".join(f"{k}={v}" for k, v in dev.parameters.items())
            nodes_str = " ".join(dev.nodes)
            line = f"{dev.instance_name} {nodes_str}"
            if param_str:
                line += f" {param_str}"
            lines.append(line)
        return "\n".join(lines)


@dataclass
class MatchResult:
    """Result of matching a layout geometry to a SPICE device."""

    layout_geometry_id: str
    spice_device: SpiceDevice
    confidence: float = 0.0

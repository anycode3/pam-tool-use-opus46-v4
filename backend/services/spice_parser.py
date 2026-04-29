"""SPICE netlist parser for L/C/R devices and subcircuits."""

import re
from typing import Optional
from services.spice_models import SpiceDevice, SpiceNetlist


# Engineering notation prefixes
ENGINEERING_PREFIXES = {
    "f": 1e-15,   # femto
    "p": 1e-12,   # pico
    "n": 1e-9,    # nano
    "u": 1e-6,    # micro
    "m": 1e-3,    # milli
    "k": 1e3,     # kilo
    "meg": 1e6,   # mega
    "g": 1e9,     # giga
    "t": 1e12,    # tera
}


def parse_engineering(value_str: str, device_type: str = "") -> tuple[float, str]:
    """Parse engineering notation value (e.g., '5.6n', '4.7k', '5nH').

    Args:
        value_str: The value string from SPICE (e.g., '5nH', '4.7k', '100').
        device_type: Optional device type ('inductor', 'capacitor', 'resistor') to
                     infer implied unit when only a prefix is present.

    Returns:
        Tuple of (numeric_value, unit_string).
        The numeric_value is the raw number (not scaled).
        The unit_string is the full suffix (e.g., 'nH', 'pF', 'k').
    """
    value_str = value_str.strip()

    # Map device type to implied unit letter
    implied_unit = {"inductor": "H", "capacitor": "F"}

    # Regex to parse: number + optional (scale factor + optional unit letter)
    # Scale factors: f, p, n, u, m, k, g, t, or meg (multi-char)
    # Optional unit letter: H, F, R, Ohm (for resistor), etc.
    match = re.match(
        r"^([+-]?\d*\.?\d+)\s*([fpnumkgt]|meg)?([HFROhm]*)$",
        value_str,
        re.IGNORECASE
    )
    if not match:
        # Fallback: treat as raw number
        return float(value_str), ""

    number = float(match.group(1))
    scale = (match.group(2) or "").lower()
    explicit_unit = (match.group(3) or "")

    if not scale:
        return number, ""

    # Build the unit string: scale + explicit unit
    # If there's an explicit unit letter, use it; otherwise infer from device_type
    if explicit_unit:
        unit = scale + explicit_unit
    elif device_type and device_type in implied_unit:
        # Infer implied unit based on device type
        unit = scale + implied_unit[device_type]
    else:
        unit = scale

    return number, unit


def parse_device_line(line: str) -> Optional[SpiceDevice]:
    """Parse a single SPICE device line.

    Supported formats:
        L<name> <node1> <node2> <value>[<unit>]
        C<name> <node1> <node2> <value>[<unit>]
        R<name> <node1> <node2> <value>[<unit>]
    """
    line = line.strip()
    if not line or line.startswith("*") or line.startswith("."):
        return None

    parts = line.split()
    if len(parts) < 4:
        return None

    inst_name = parts[0]
    device_char = inst_name[0].upper()

    if device_char not in ("L", "C", "R"):
        return None

    device_type_map = {"L": "inductor", "C": "capacitor", "R": "resistor"}
    device_type = device_type_map[device_char]

    nets = [parts[1], parts[2]]
    raw_val = parts[3]

    value, unit = parse_engineering(raw_val, device_type=device_type)

    return SpiceDevice(
        instance_name=inst_name,
        device_type=device_type,
        value=value,
        unit=unit,
        nets=nets,
    )


def parse_spice(netlist_text: str) -> SpiceNetlist:
    """Parse a SPICE netlist string.

    Args:
        netlist_text: Raw SPICE netlist text.

    Returns:
        SpiceNetlist object containing parsed devices and subcircuits.
    """
    netlist = SpiceNetlist()

    lines = netlist_text.splitlines()
    current_subckt: Optional[str] = None
    current_subckt_devices: list[SpiceDevice] = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("*"):
            continue

        # Handle subcircuit start
        if stripped.upper().startswith(".SUBCKT"):
            parts = stripped.split()
            if len(parts) >= 2:
                current_subckt = parts[1]
                current_subckt_devices = []
            continue

        # Handle subcircuit end
        if stripped.upper().startswith(".ENDS"):
            if current_subckt is not None:
                netlist.subcircuits[current_subckt] = current_subckt_devices
                current_subckt = None
                current_subckt_devices = []
            continue

        # Handle end of netlist
        if stripped.upper() in (".END", ".END "):
            continue

        # Parse device line
        device = parse_device_line(stripped)
        if device is None:
            continue

        if current_subckt is not None:
            current_subckt_devices.append(device)
        else:
            netlist.devices.append(device)
            for net in device.nets:
                if net.lower() != "gnd":
                    netlist.global_nets.add(net)

    return netlist

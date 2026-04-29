"""Value-based matching between SPICE devices and layout devices."""

import numpy as np
from services.spice_models import SpiceDevice, SpiceNetlist, MatchResult

# Layout unit -> multiplier to get base unit (H for inductors, F for capacitors, Ω for resistors)
LAYOUT_UNIT_MULTIPLIERS = {
    "nH": 1e-9, "mH": 1e-3, "H": 1.0,
    "pF": 1e-12, "uF": 1e-6, "fF": 1e-15, "F": 1.0,
    "Ω": 1.0, "kΩ": 1e3, "MΩ": 1e6,
}


def _get_layout_base_value(layout_dev: dict) -> tuple[float, float]:
    """Get layout device value and multiplier.

    Returns (value_in_base_units, multiplier).
    """
    value = layout_dev.get("value", 0)
    unit = layout_dev.get("unit", "Ω")
    multiplier = LAYOUT_UNIT_MULTIPLIERS.get(unit, 1)
    return value * multiplier, multiplier


def _value_similarity(v1: float, v2: float) -> float:
    """Compute similarity between two values. 1.0 = identical, 0.0 = very different.

    Uses ratio-based comparison to handle values spanning many orders of magnitude.
    """
    if v1 == 0 and v2 == 0:
        return 1.0
    if v1 == 0 or v2 == 0:
        return 0.0
    # Ratio-based similarity: min/max gives 1.0 for identical, lower for different
    return min(abs(v1), abs(v2)) / max(abs(v1), abs(v2))


def _type_compatible(spice_type: str, layout_type: str) -> bool:
    """Check if device types are compatible."""
    type_map = {
        "inductor": "inductor",
        "capacitor": "capacitor",
        "resistor": "resistor",
    }
    return type_map.get(spice_type) == type_map.get(layout_type)


def _compute_confidence(similarity: float) -> float:
    """Compute confidence from similarity score."""
    if similarity >= 0.98:
        return 1.0
    elif similarity >= 0.9:
        return 0.9
    elif similarity >= 0.7:
        return 0.7
    elif similarity >= 0.5:
        return 0.5
    else:
        return 0.2


def match_devices(spice_devices: list[SpiceDevice], layout_devices: list[dict]) -> list[MatchResult]:
    """Match SPICE devices to layout devices using Hungarian algorithm.

    Returns list of MatchResult with confidence scores.
    Unmatched devices are not included in results.
    """
    if not spice_devices or not layout_devices:
        return []

    # Build cost matrix
    n_spice = len(spice_devices)
    n_layout = len(layout_devices)

    # Initialize with high cost (no match)
    cost_matrix = np.full((n_spice, n_layout), 1.0)

    for i, spice_dev in enumerate(spice_devices):
        spice_val = spice_dev.value
        spice_unit = spice_dev.unit

        # Convert SPICE value to base units if needed
        if spice_unit in LAYOUT_UNIT_MULTIPLIERS:
            spice_val = spice_val * LAYOUT_UNIT_MULTIPLIERS[spice_unit]
        elif spice_unit == "nH":
            spice_val = spice_val * 1e-9
        elif spice_unit == "pF":
            spice_val = spice_val * 1e-12

        for j, layout_dev in enumerate(layout_devices):
            if not _type_compatible(spice_dev.device_type, layout_dev.get("type", "")):
                continue

            # Get layout value in base SI units
            layout_val, layout_mult = _get_layout_base_value(layout_dev)

            # Skip if either is zero
            if spice_val <= 0 or layout_val <= 0:
                continue

            similarity = _value_similarity(spice_val, layout_val)
            # Only consider if similarity > 0.2 (within 5x range)
            if similarity > 0.2:
                cost_matrix[i, j] = 1.0 - similarity

    # Apply Hungarian algorithm
    try:
        from scipy.optimize import linear_sum_assignment
        row_ind, col_ind = linear_sum_assignment(cost_matrix)
    except ImportError:
        # Fallback to greedy matching
        return _greedy_match(spice_devices, layout_devices, cost_matrix)

    results = []
    for i, j in zip(row_ind, col_ind):
        if cost_matrix[i, j] < 0.8:  # Only if similarity > 0.2
            spice_dev = spice_devices[i]
            layout_dev = layout_devices[j]
            similarity = 1.0 - cost_matrix[i, j]

            results.append(MatchResult(
                spice_name=spice_dev.instance_name,
                layout_id=layout_dev["id"],
                spice_value=spice_dev.value,
                layout_value=layout_dev.get("value", 0),
                confidence=_compute_confidence(similarity),
                match_method="value_exact" if similarity >= 0.98 else "value_close",
            ))

    return results


def _greedy_match(spice_devices: list[SpiceDevice], layout_devices: list[dict], cost_matrix: np.ndarray) -> list[MatchResult]:
    """Fallback greedy matching when scipy unavailable."""
    results = []
    matched_layout = set()

    # Sort by best similarity
    candidates = []
    for i, spice_dev in enumerate(spice_devices):
        for j, layout_dev in enumerate(layout_devices):
            if j not in matched_layout:
                similarity = 1.0 - cost_matrix[i, j]
                if similarity > 0.2:
                    candidates.append((similarity, i, j, spice_dev, layout_dev))

    candidates.sort(reverse=True)

    for similarity, i, j, spice_dev, layout_dev in candidates:
        if j not in matched_layout:
            results.append(MatchResult(
                spice_name=spice_dev.instance_name,
                layout_id=layout_dev["id"],
                spice_value=spice_dev.value,
                layout_value=layout_dev.get("value", 0),
                confidence=_compute_confidence(similarity),
                match_method="value_exact" if similarity >= 0.98 else "value_close",
            ))
            matched_layout.add(j)

    return results

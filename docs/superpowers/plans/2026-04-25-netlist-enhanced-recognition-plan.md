# Netlist-Enhanced Device Recognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add SPICE netlist upload and value-based matching to enhance layout device recognition accuracy.

**Architecture:** SPICE parser extracts L/C/R devices with values and net connections. Value-based Hungarian algorithm matches them to geometry-recognized layout devices. Confidence scoring reports match quality.

**Tech Stack:** Python (backend), FastAPI (API), React (frontend), scipy.optimize.linear_sum_assignment (matching)

---

## File Map

### New Files
| File | Responsibility |
|------|---------------|
| `backend/services/spice_parser.py` | Parse SPICE netlist → SpiceNetlist dataclass |
| `backend/services/netlist_matcher.py` | Build cost matrix + Hungarian matching |
| `backend/services/spice_models.py` | SpiceDevice, SpiceNetlist, MatchResult dataclasses |
| `backend/tests/test_spice_parser.py` | SPICE parser unit tests |
| `backend/tests/test_netlist_matcher.py` | Matcher unit tests |
| `frontend/src/components/NetlistUploadDialog.tsx` | Upload + preview SPICE file |
| `frontend/src/components/DeviceMatchPanel.tsx` | Show match results |
| `frontend/src/types/spice.ts` | TypeScript types for SPICE data |

### Modified Files
| File | Change |
|------|--------|
| `backend/routers/projects.py` | Add `/netlist/upload`, `/{project_id}/devices/match` endpoints |
| `backend/services/storage.py` | Add `save_netlist()`, `load_netlist()` |
| `backend/services/device_recognition.py` | Accept optional `spice_devices` param for enhanced recognition |
| `frontend/src/store/useProjectStore.ts` | Add netlist state + match actions |
| `frontend/src/types/index.ts` | Add SpiceDevice, MatchResult TypeScript types |

---

## Phase 1: SPICE Parser

### Task 1: Create SpiceDataClasses

**Files:**
- Create: `backend/services/spice_models.py`

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SpiceDevice:
    instance_name: str
    device_type: str  # "inductor" | "capacitor" | "resistor"
    value: float
    unit: str  # "nH" | "pF" | "Ω"
    nets: list[str] = field(default_factory=list)
    subcircuit: str = ""

@dataclass
class SpiceNetlist:
    devices: list[SpiceDevice] = field(default_factory=list)
    subcircuits: dict[str, list[SpiceDevice]] = field(default_factory=dict)
    global_nets: set[str] = field(default_factory=set)

@dataclass
class MatchResult:
    spice_name: str
    layout_id: str
    spice_value: float
    layout_value: float
    confidence: float  # 0.0-1.0
    match_method: str  # "value_exact" | "value_close"
```

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_spice_models.py
import pytest
from services.spice_models import SpiceDevice, SpiceNetlist, MatchResult

def test_spice_device_creation():
    dev = SpiceDevice(instance_name="L1", device_type="inductor",
                      value=5.0, unit="nH", nets=["net_a", "net_b"])
    assert dev.instance_name == "L1"
    assert dev.device_type == "inductor"
    assert dev.value == 5.0

def test_spice_netlist_empty():
    netlist = SpiceNetlist()
    assert netlist.devices == []
    assert netlist.subcircuits == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_spice_models.py -v`
Expected: `ERROR - import error (spice_models not found)`

- [ ] **Step 3: Write minimal SpiceModels**

```python
# backend/services/spice_models.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SpiceDevice:
    instance_name: str
    device_type: str
    value: float
    unit: str
    nets: list[str] = field(default_factory=list)
    subcircuit: str = ""

@dataclass
class SpiceNetlist:
    devices: list[SpiceDevice] = field(default_factory=list)
    subcircuits: dict[str, list[SpiceDevice]] = field(default_factory=dict)
    global_nets: set[str] = field(default_factory=set)

@dataclass
class MatchResult:
    spice_name: str
    layout_id: str
    spice_value: float
    layout_value: float
    confidence: float
    match_method: str
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_spice_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /root/pam/pam-tool-use-opus-v4
git add backend/services/spice_models.py backend/tests/test_spice_models.py
git commit -m "feat(backend): add SpiceDevice, SpiceNetlist, MatchResult dataclasses"
```

---

### Task 2: Write SPICE Parser

**Files:**
- Create: `backend/services/spice_parser.py`
- Modify: `backend/tests/test_spice_parser.py` (create test file)

- [ ] **Step 1: Write failing test for basic SPICE parsing**

```python
# backend/tests/test_spice_parser.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_spice_parser.py -v`
Expected: FAIL with "module 'services.spice_parser' has no attribute 'parse_spice'"

- [ ] **Step 3: Write minimal parse_spice function**

```python
# backend/services/spice_parser.py
"""SPICE netlist parser for L/C/R devices."""

import re
from services.spice_models import SpiceDevice, SpiceNetlist

# Engineering notation suffixes
UNIT_PREFIXES = {
    "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6,
    "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9
}

# Device type prefixes
DEVICE_TYPES = {
    "L": ("inductor", "nH"),
    "C": ("capacitor", "pF"),
    "R": ("resistor", "Ω"),
}

def _parse_value(value_str: str) -> tuple[float, str]:
    """Parse value string like '5nH', '4.7k', '2.3pF' into (float, unit)."""
    value_str = value_str.strip()
    
    # Try engineering notation suffix
    for suffix, multiplier in UNIT_PREFIXES.items():
        if value_str.lower().endswith(suffix):
            num_str = value_str[:-len(suffix)].strip()
            try:
                val = float(num_str) * multiplier
                return (val, _get_unit_suffix(suffix))
            except ValueError:
                pass
    
    # Try unit at end: 5nH, 2pF
    pattern = r'^([+-]?\d+\.?\d*)([fpnumk]?)(H|F|Ω)?'
    m = re.match(pattern, value_str, re.IGNORECASE)
    if m:
        num = float(m.group(1))
        prefix = m.group(2).lower() if m.group(2) else ""
        unit = m.group(3) if m.group(3) else ""
        multiplier = UNIT_PREFIXES.get(prefix, 1)
        return (num * multiplier, _map_unit(unit, prefix))
    
    # Default: plain number -> Ohm
    try:
        return (float(value_str), "Ω")
    except ValueError:
        return (0.0, "Ω")

def _get_unit_suffix(prefix: str) -> str:
    mapping = {"f": "f", "p": "pF", "n": "nH", "u": "uF", "m": "mH", "k": "kΩ", "meg": "MΩ", "g": "GHz"}
    return mapping.get(prefix, "Ω")

def _map_unit(unit: str, prefix: str) -> str:
    if unit in ("H", "Henry"):
        return "nH"
    if unit in ("F", "Farad"):
        return "pF"
    return "Ω"

def parse_spice(content: str) -> SpiceNetlist:
    """Parse SPICE netlist content into SpiceNetlist."""
    netlist = SpiceNetlist()
    current_subckt = ""
    line_num = 0
    
    for raw_line in content.splitlines():
        line_num += 1
        line = raw_line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('*'):
            continue
        
        # End of subcircuit
        if line.startswith('.ENDS'):
            current_subckt = ""
            continue
        
        # Subcircuit definition
        m = re.match(r'\.SUBCKT\s+(\S+)\s*(.*)', line, re.IGNORECASE)
        if m:
            current_subckt = m.group(1)
            continue
        
        # End marker
        if line.startswith('.END') and not current_subckt:
            break
        
        # Device lines: Lname Net+ Net- Value
        m = re.match(r'^([LCR])\w+\s+(\S+)\s+(\S+)\s+(.+)', line)
        if m:
            prefix = m.group(1)
            nets = [m.group(2), m.group(3)]
            value_str = m.group(4).strip()
            
            if prefix in DEVICE_TYPES:
                dev_type, default_unit = DEVICE_TYPES[prefix]
                value, unit = _parse_value(value_str)
                # Normalize unit for matching
                if unit == "nH" or unit == "mH" or dev_type == "inductor":
                    unit = "nH"
                elif unit == "pF" or unit == "uF" or unit == "fF":
                    unit = "pF"
                
                device = SpiceDevice(
                    instance_name=line.split()[0],
                    device_type=dev_type,
                    value=value,
                    unit=unit,
                    nets=nets,
                    subcircuit=current_subckt,
                )
                if current_subckt:
                    if current_subckt not in netlist.subcircuits:
                        netlist.subcircuits[current_subckt] = []
                    netlist.subcircuits[current_subckt].append(device)
                else:
                    netlist.devices.append(device)
    
    return netlist
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_spice_parser.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/services/spice_parser.py backend/tests/test_spice_parser.py
git commit -m "feat(backend): add SPICE netlist parser for L/C/R devices"
```

---

## Phase 2: Netlist Matcher

### Task 3: Write Value-Based Matcher

**Files:**
- Create: `backend/services/netlist_matcher.py`
- Create: `backend/tests/test_netlist_matcher.py`

- [ ] **Step 1: Write failing test for matcher**

```python
# backend/tests/test_netlist_matcher.py
import pytest
from services.spice_models import SpiceDevice, SpiceNetlist
from services.netlist_matcher import match_devices, compute_confidence

# Mock layout devices (from recognize_devices output)
LAYOUT_DEVICES = [
    {"id": "dev_001", "type": "inductor", "value": 5.0, "unit": "nH"},
    {"id": "dev_002", "type": "capacitor", "value": 2.0, "unit": "pF"},
    {"id": "dev_003", "type": "resistor", "value": 100.0, "unit": "Ω"},
]

def test_match_identical_values():
    spice_devices = [
        SpiceDevice("L1", "inductor", 5.0, "nH", ["a", "b"]),
        SpiceDevice("C1", "capacitor", 2.0, "pF", ["b", "c"]),
        SpiceDevice("R1", "resistor", 100.0, "Ω", ["a", "c"]),
    ]
    results = match_devices(spice_devices, LAYOUT_DEVICES)
    
    assert len(results) == 3
    l1_match = next(r for r in results if r.spice_name == "L1")
    assert l1_match.layout_id == "dev_001"
    assert l1_match.confidence == 1.0

def test_match_close_values():
    spice_devices = [
        SpiceDevice("L1", "inductor", 5.0, "nH", ["a", "b"]),  # vs 5.05 in layout
    ]
    layout = [{"id": "dev_001", "type": "inductor", "value": 5.05, "unit": "nH"}]
    results = match_devices(spice_devices, layout)
    
    assert len(results) == 1
    assert results[0].confidence > 0.9

def test_no_match_wrong_type():
    spice_devices = [
        SpiceDevice("L1", "inductor", 5.0, "nH", ["a", "b"]),
    ]
    layout = [{"id": "dev_001", "type": "capacitor", "value": 5.0, "unit": "pF"}]
    results = match_devices(spice_devices, layout)
    
    assert len(results) == 0  # No match for wrong type
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_netlist_matcher.py -v`
Expected: FAIL with "module 'services.netlist_matcher' has no attribute 'match_devices'"

- [ ] **Step 3: Write minimal matcher**

```python
# backend/services/netlist_matcher.py
"""Value-based matching between SPICE devices and layout devices."""

import numpy as np
from typing import Optional
from services.spice_models import SpiceDevice, SpiceNetlist, MatchResult

def _value_similarity(v1: float, v2: float) -> float:
    """Compute similarity between two values. 1.0 = identical, 0.0 = very different."""
    if v1 == 0 and v2 == 0:
        return 1.0
    if v1 == 0 or v2 == 0:
        return 0.0
    return 1.0 - abs(v1 - v2) / max(abs(v1), abs(v2))

def _type_compatible(spice_type: str, layout_type: str) -> bool:
    """Check if device types are compatible."""
    type_map = {
        "inductor": "inductor",
        "capacitor": "capacitor", 
        "resistor": "resistor",
    }
    return type_map.get(spice_type) == type_map.get(layout_type)

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
        for j, layout_dev in enumerate(layout_devices):
            if not _type_compatible(spice_dev.device_type, layout_dev.get("type", "")):
                continue
            
            # Only match if values are somewhat close (within 5x range)
            spice_val = spice_dev.value
            layout_val = layout_dev.get("value", 0)
            
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
                match_method="value_close" if similarity < 0.98 else "value_exact",
            ))
    
    return results

def _greedy_match(spice_devices, layout_devices, cost_matrix):
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
                match_method="value_close",
            ))
            matched_layout.add(j)
    
    return results

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_netlist_matcher.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/services/netlist_matcher.py backend/tests/test_netlist_matcher.py
git commit -m "feat(backend): add value-based netlist matcher with Hungarian algorithm"
```

---

## Phase 3: API Integration

### Task 4: Add Netlist Upload Endpoint

**Files:**
- Modify: `backend/routers/projects.py`
- Modify: `backend/services/storage.py`
- Modify: `config.py` (add .sp, .cir to ALLOWED_EXTENSIONS)

- [ ] **Step 1: Write failing test for netlist upload**

```python
# backend/tests/test_netlist_api.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_upload_netlist_unauthorized():
    """Without project, should fail."""
    response = client.post(
        "/api/projects/nonexistent/netlist/upload",
        files={"file": ("test.sp", "* Simple netlist\nL1 a b 5nH\n.END")}
    )
    assert response.status_code == 404

def test_upload_netlist_invalid_type():
    """Wrong extension should fail."""
    response = client.post(
        "/api/projects/nonexistent/netlist/upload",
        files={"file": ("test.txt", "not a netlist")}
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_netlist_api.py::test_upload_netlist_invalid_type -v`
Expected: FAIL (endpoint not defined)

- [ ] **Step 3: Add .sp/.cir to ALLOWED_EXTENSIONS in config.py**

```python
# backend/config.py
ALLOWED_EXTENSIONS = {".gds", ".gds2", ".gdsii", ".dxf", ".sp", ".cir", ".net"}
```

- [ ] **Step 4: Add storage methods**

Add to `backend/services/storage.py`:
```python
def save_netlist(self, project_id: str, netlist_data: dict) -> None:
    """Save parsed SPICE netlist."""
    self.save_json(project_id, "netlist.json", netlist_data)

def load_netlist(self, project_id: str) -> dict | None:
    """Load parsed SPICE netlist."""
    return self.load_json(project_id, "netlist.json")
```

- [ ] **Step 5: Add netlist upload endpoint**

Add to `backend/routers/projects.py`:
```python
@router.post("/{project_id}/netlist/upload")
async def upload_netlist(project_id: str, file: UploadFile = File(...)):
    """Upload and parse SPICE netlist for device matching."""
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".sp", ".cir", ".net"}:
        raise HTTPException(400, f"Unsupported netlist format: {suffix}")

    content = await file.read()
    
    try:
        netlist_data = parse_spice(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(400, f"Failed to parse SPICE: {e}")

    storage.save_netlist(project_id, {
        "devices": [
            {
                "instance_name": d.instance_name,
                "device_type": d.device_type,
                "value": d.value,
                "unit": d.unit,
                "nets": d.nets,
                "subcircuit": d.subcircuit,
            }
            for d in netlist_data.devices
        ],
        "subcircuits": netlist_data.subcircuits,
        "global_nets": list(netlist_data.global_nets),
    })

    return {"status": "uploaded", "device_count": len(netlist_data.devices)}
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_netlist_api.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/routers/projects.py backend/services/storage.py backend/config.py
git commit -m "feat(backend): add SPICE netlist upload endpoint"
```

---

### Task 5: Add Device Match Endpoint

**Files:**
- Modify: `backend/routers/projects.py`

- [ ] **Step 1: Write failing test**

```python
def test_match_devices_endpoint():
    """After uploading netlist, can match devices."""
    # First create project with layout
    # Then upload netlist
    # Then call match endpoint
    response = client.post(f"/api/projects/{project_id}/devices/match")
    assert response.status_code == 200
    data = response.json()
    assert "matches" in data
    assert "unmatched_spice" in data
```

- [ ] **Step 2: Run test to verify it fails**

Expected: FAIL (endpoint not defined)

- [ ] **Step 3: Add match endpoint**

Add to `backend/routers/projects.py`:
```python
@router.post("/{project_id}/devices/match")
def match_project_devices(project_id: str):
    """Match SPICE devices to layout devices."""
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    netlist_data = storage.load_netlist(project_id)
    if not netlist_data or not netlist_data.get("devices"):
        raise HTTPException(400, "No netlist uploaded. Upload SPICE file first.")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(400, "No layout data. Upload layout file first.")

    devices_data = storage.load_json(project_id, "devices.json")
    if not devices_data or not devices_data.get("devices"):
        raise HTTPException(400, "No devices recognized. Run recognition first.")

    # Parse SpiceDevice list
    spice_devices = [
        SpiceDevice(
            instance_name=d["instance_name"],
            device_type=d["device_type"],
            value=d["value"],
            unit=d["unit"],
            nets=d.get("nets", []),
            subcircuit=d.get("subcircuit", ""),
        )
        for d in netlist_data["devices"]
    ]

    # Run matching
    matches = match_devices(spice_devices, devices_data["devices"])

    # Build response
    matched_spice = {m.spice_name for m in matches}
    matched_layout = {m.layout_id for m in matches}

    return {
        "matches": [
            {
                "spice_name": m.spice_name,
                "layout_id": m.layout_id,
                "spice_value": m.spice_value,
                "layout_value": m.layout_value,
                "confidence": m.confidence,
                "match_method": m.match_method,
            }
            for m in matches
        ],
        "unmatched_spice": [
            d["instance_name"] for d in netlist_data["devices"]
            if d["instance_name"] not in matched_spice
        ],
        "unmatched_layout": [
            d["id"] for d in devices_data["devices"]
            if d["id"] not in matched_layout
        ],
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /root/pam/pam-tool-use-opus-v4/backend && python -m pytest tests/test_netlist_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/routers/projects.py
git commit -m "feat(backend): add device match endpoint"
```

---

## Phase 4: Frontend Integration

### Task 6: Add TypeScript Types

**Files:**
- Modify: `frontend/src/types/index.ts`

- [ ] **Step 1: Add TypeScript interfaces**

```typescript
// Add to frontend/src/types/index.ts

export interface SpiceDevice {
  instance_name: string;
  device_type: 'inductor' | 'capacitor' | 'resistor';
  value: number;
  unit: string;
  nets: string[];
  subcircuit: string;
}

export interface SpiceNetlist {
  devices: SpiceDevice[];
  subcircuits: Record<string, SpiceDevice[]>;
  global_nets: string[];
}

export interface MatchResult {
  spice_name: string;
  layout_id: string;
  spice_value: number;
  layout_value: number;
  confidence: number;
  match_method: string;
}

export interface MatchResponse {
  matches: MatchResult[];
  unmatched_spice: string[];
  unmatched_layout: string[];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): add SpiceDevice, MatchResult TypeScript types"
```

---

### Task 7: Add Netlist Upload Dialog

**Files:**
- Create: `frontend/src/components/NetlistUploadDialog.tsx`

- [ ] **Step 1: Create component**

```tsx
// frontend/src/components/NetlistUploadDialog.tsx
import React, { useState } from 'react';
import { Modal, Upload, Button, message, List, Tag } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { useProjectStore } from '../store/useProjectStore';
import type { SpiceDevice, SpiceNetlist } from '../types';

interface Props {
  open: boolean;
  onClose: () => void;
  projectId: string;
}

export const NetlistUploadDialog: React.FC<Props> = ({ open, onClose, projectId }) => {
  const [uploading, setUploading] = useState(false);
  const [netlist, setNetlist] = useState<SpiceNetlist | null>(null);
  const { uploadNetlist } = useProjectStore();

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const result = await uploadNetlist(projectId, file);
      message.success(`Uploaded ${result.device_count} devices`);
      // Fetch parsed netlist
      const resp = await fetch(`/api/projects/${projectId}/netlist`);
      const data = await resp.json();
      setNetlist(data);
    } catch (e: any) {
      message.error(e.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
    return false; // Prevent auto upload
  };

  const deviceTypeColor = (type: string) => {
    switch (type) {
      case 'inductor': return 'blue';
      case 'capacitor': return 'green';
      case 'resistor': return 'orange';
      default: return 'default';
    }
  };

  return (
    <Modal title="Upload SPICE Netlist" open={open} onCancel={onClose} footer={null} width={600}>
      <Upload.Dragger accept=".sp,.cir,.net" beforeUpload={handleUpload} showUploadList={false}>
        <p><UploadOutlined style={{ fontSize: 40 }} /></p>
        <p>Click or drag SPICE netlist file</p>
        <p style={{ color: '#999' }}>.sp, .cir, .net formats</p>
      </Upload.Dragger>
      
      {netlist && (
        <>
          <h3>Parsed Devices ({netlist.devices.length})</h3>
          <List
            size="small"
            dataSource={netlist.devices}
            renderItem={(dev: SpiceDevice) => (
              <List.Item>
                <Tag color={deviceTypeColor(dev.device_type)}>{dev.device_type.toUpperCase()}</Tag>
                <strong>{dev.instance_name}</strong>
                <span style={{ marginLeft: 8 }}>
                  {dev.value.toFixed(2)} {dev.unit}
                </span>
                <span style={{ color: '#999', marginLeft: 8 }}>
                  nets: {dev.nets.join(', ')}
                </span>
              </List.Item>
            )}
          />
        </>
      )}
    </Modal>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/NetlistUploadDialog.tsx
git commit -m "feat(frontend): add NetlistUploadDialog component"
```

---

### Task 8: Wire to ProjectStore

**Files:**
- Modify: `frontend/src/store/useProjectStore.ts`

- [ ] **Step 1: Add uploadNetlist action**

Add to `useProjectStore.ts`:
```typescript
uploadNetlist: async (projectId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const resp = await fetch(`/api/projects/${projectId}/netlist/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!resp.ok) throw new Error('Upload failed');
  return resp.json();
},
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/store/useProjectStore.ts
git commit -m "feat(frontend): add uploadNetlist action to project store"
```

---

## Verification

### Run All Tests
```bash
cd /root/pam/pam-tool-use-opus-v4/backend
python -m pytest tests/test_spice_parser.py tests/test_netlist_matcher.py -v
```

### Manual Verification
1. Upload a GDS layout with known devices
2. Upload a SPICE netlist with matching devices
3. Click "Match Devices" - verify matches appear with confidence scores
4. Verify unmatched devices are listed separately

---

## Self-Review Checklist

- [ ] All spec requirements covered: SPICE parser, value matching, API endpoints, frontend
- [ ] No placeholders or TODOs in code
- [ ] Type signatures consistent across files
- [ ] Error handling: parse errors, no scipy fallback tested
- [ ] No test depends on external network/files

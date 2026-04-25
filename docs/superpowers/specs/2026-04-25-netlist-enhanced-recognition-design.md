# Netlist-Enhanced Device Recognition Design

## Context

当前器件识别仅基于几何特征（紧密度、顶点数、内/外径比等），在版图形态复杂时准确率不足。用户上传SPICE网表后，网表直接包含器件类型、值、连接关系，这些信息可大幅提升识别准确率。

本设计在现有几何识别基础上，引入SPICE网表作为"答案"，通过约束二分图匹配为版图器件打上网表实例标签。

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     Input Phase                              │
│  GDS/DXF Layout File              SPICE Netlist File        │
│         │                              │                     │
│         ▼                              ▼                     │
│  ┌─────────────┐               ┌─────────────┐              │
│  │   Parser    │               │ SPICE      │              │
│  │  (existing) │               │  Parser    │              │
│  └──────┬──────┘               └──────┬──────┘              │
│         │                              │                     │
│         ▼                              ▼                     │
│  ┌─────────────┐               ┌─────────────┐              │
│  │  Geometry   │               │ SpiceDevice│              │
│  │  Recognition│               │    List    │              │
│  └──────┬──────┘               └──────┬──────┘              │
│         │                              │                     │
│         │         Matching Phase       │                     │
│         │  ┌────────────────────────────────┐               │
│         └──┼──▶│  Value-Based Cost Matrix   │◀──┘          │
│            │   │  (type filter + score)     │               │
│            │   └────────────┬───────────────┘               │
│            │                ▼                                │
│            │   ┌─────────────────────┐                     │
│            │   │  Hungarian Algorithm  │                     │
│            │   │ (optimal assignment) │                     │
│            │   └────────────┬─────────┘                     │
│            │                ▼                                │
│            │   ┌─────────────────────┐                      │
│            │   │  Matched Devices    │                      │
│            │   │  + Confidence Score │                      │
│            └──▶└─────────────────────┘                      │
└──────────────────────────────────────────────────────────────┘
```

## Data Structures

### SpiceDevice

```python
@dataclass
class SpiceDevice:
    instance_name: str           # "L1", "C1"
    device_type: str            # "inductor" | "capacitor" | "resistor"
    value: float               # numeric value
    unit: str                  # "nH" | "pF" | "Ω"
    nets: list[str]            # connected net names, e.g. ["net_a", "net_b"]
    subcircuit: str             # "" for top-level
```

### SpiceNetlist

```python
@dataclass
class SpiceNetlist:
    devices: list[SpiceDevice]
    subcircuits: dict[str, list[SpiceDevice]]  # subckt_name -> devices
    global_nets: set[str]                       # VDD, GND, etc.
```

### MatchResult

```python
@dataclass
class MatchResult:
    spice_device: SpiceDevice
    layout_device: dict        # device from recognize_devices output
    confidence: float          # 0.0 - 1.0
    match_method: str         # "value_exact" | "value_close" | "connectivity"
```

## Components

### 1. SPICE Parser (`backend/services/spice_parser.py`)

Parses SPICE netlist into `SpiceNetlist`.

**Supported syntax:**
- Device lines: `Lname Net+ Net- <value>` (HSpice, ngSPICE, Spectre)
- Subcircuits: `.SUBCKT name net ...` / `.ENDS`
- Comments: `* comment`
- End markers: `.END`, `.ENDS`
- Continuation: `+ line continuation`

**Value parsing:**
- Plain: `5nH`, `2pF`, `100` → (5.0, "nH"), (2.0, "pF"), (100.0, "Ω")
- Engineering: `5.6n`, `2.3p`, `4.7k`, `1.2meg`, `10p`
- Scientific: `5.6e-9`, `2.3e-12`

**Device type mapping:**
| Prefix | Type | Unit |
|--------|------|------|
| L | inductor | nH |
| C | capacitor | pF |
| R | resistor | Ω |

### 2. Value Matcher (`backend/services/netlist_matcher.py`)

Matches SPICE devices to layout devices using value similarity.

**Algorithm: Hungarian Algorithm with Type Filter**

```python
def build_cost_matrix(spice_devices, layout_devices) -> np.ndarray:
    """Build cost matrix for Hungarian algorithm.

    Rows: SPICE devices
    Cols: Layout devices (from recognize_devices)

    cost[i][j] = 1 - similarity_score(spice_i, layout_j)
    similarity = 1 - |v1 - v2| / max(v1, v2)  [if same type]
    similarity = 0                                          [if different type]
    """
    # Filter: only same device type can match
    # Score: value proximity (relative error)
    # Solve: scipy.optimize.linear_sum_assignment (Hungarian)
```

**Confidence scoring:**
```python
def compute_confidence(best_match, second_best, spice_dev, layout_dev) -> float:
    # If best and second-best are close → low confidence
    # If best is much better → high confidence
    gap = second_best_score - best_score
    if gap > 0.1:   return 1.0   # clear winner
    elif gap > 0.05: return 0.8   # probable
    elif gap > 0.02: return 0.5   # uncertain
    else:            return 0.2   # ambiguous
```

### 3. API Extension

**New endpoint:**
```
POST /api/projects/{project_id}/netlist/upload
  Body: multipart file (.sp, .cir, .net)
  Response: { "devices": [...], "subcircuits": {...}, "global_nets": [...] }
```

**Enhanced recognize endpoint:**
```
POST /api/projects/{project_id}/devices/recognize
  Body: { "method": "geometry" | "netlist_enhanced" }
  Response: devices with new fields: spice_instance, confidence, matched
```

**New matching endpoint:**
```
POST /api/projects/{project_id}/devices/match
  Body: { "spice_netlist_id": "xxx" }
  Response: { "matches": [...], "unmatched_spice": [...], "unmatched_layout": [...] }
```

## File Structure

```
backend/services/
├── spice_parser.py       # NEW: SPICE netlist parser (~150 lines)
├── netlist_matcher.py    # NEW: Value-based matching + Hungarian (~200 lines)
├── parser.py             # MODIFY: add netlist branch
├── device_recognition.py  # MODIFY: accept optional spice_devices param
└── ...

backend/routers/projects.py  # MODIFY: add netlist upload, match endpoints

frontend/src/
├── components/
│   ├── NetlistUploadDialog.tsx   # NEW: upload + preview SPICE
│   ├── DeviceMatchPanel.tsx       # NEW: show match results, confidence
│   └── DevicePanel.tsx            # MODIFY: show spice_instance label
├── store/useProjectStore.ts        # MODIFY: add netlist state, match actions
└── types/index.ts                 # MODIFY: add SpiceDevice, MatchResult types
```

## Implementation Phases

### Phase 1: SPICE Parser
- Parse basic device lines (L/C/R)
- Parse subcircuits
- Handle engineering notation
- Write unit tests

### Phase 2: Value Matcher
- Build cost matrix by type
- Apply Hungarian algorithm
- Compute confidence scores
- Handle unmatched devices

### Phase 3: API Integration
- Add netlist upload endpoint
- Add netlist storage
- Add match endpoint
- Wire to frontend

### Phase 4: Frontend
- Netlist upload dialog
- Match result display
- Confidence indicators
- User override for ambiguous matches

## Key Decisions

1. **No connectivity matching in P1** - SPICE net names are strings; layout has no net labels. Connectivity-based disambiguation deferred to P2 when net extraction from layout is implemented.

2. **降级模式** - If no netlist uploaded, `recognize_devices` falls back to geometry-only (existing behavior). If netlist uploaded but match fails, results still usable with lower confidence.

3. **No subcircuit expansion** - P1 treats subcircuits as flat list. Hierarchical matching deferred.

4. **scipy dependency** - `scipy.optimize.linear_sum_assignment` is standard scientific Python; if unavailable, falls back to greedy matching (O(n²)).

## Testing

- `backend/tests/test_spice_parser.py` - Parse all SPICE variants, verify device extraction
- `backend/tests/test_netlist_matcher.py` - Known examples with known-good matches
- Integration test: Upload FreePDK45 CDL as netlist, verify matching

## Out of Scope (P1)

- SPICE model parameters (MOS, diode)
- Netlist vs layout LVS verification
- Layout net extraction and connectivity matching
- Hierarchical subcircuit matching
- DC/AC simulation back-annotation

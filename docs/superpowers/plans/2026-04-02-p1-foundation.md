# P1: Foundation — File Upload, Parsing & Layout Visualization

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend + frontend foundation: upload GDS/DXF files, parse them into JSON geometry data, and render the layout in an interactive deck.gl viewer with pan/zoom/select.

**Architecture:** FastAPI backend with gdstk (GDS) and ezdxf (DXF) parsers that convert layout files into a unified JSON geometry format. React frontend with deck.gl SolidPolygonLayer for rendering. File storage is local filesystem under `storage/projects/{id}/`.

**Tech Stack:** Python 3.13, FastAPI, gdstk, ezdxf, uvicorn | React 18, TypeScript, Vite, deck.gl, Ant Design 5, Zustand, Axios

---

## File Structure

### Backend (`backend/`)

```
backend/
  requirements.txt              # Python dependencies
  main.py                       # FastAPI app entry point, CORS, router mounting
  config.py                     # Storage paths, constants
  routers/
    projects.py                 # /api/projects/* endpoints
  services/
    storage.py                  # File system operations (save, load, delete projects)
    parser_gds.py               # GDS file parsing via gdstk
    parser_dxf.py               # DXF file parsing via ezdxf
    parser.py                   # Unified parser interface (dispatches by file type)
  models/
    project.py                  # Pydantic models: Project, LayoutData, Geometry, LayerInfo, Bounds
  tests/
    conftest.py                 # Shared fixtures (tmp storage dir, sample GDS/DXF generators)
    test_parser_gds.py          # GDS parser unit tests
    test_parser_dxf.py          # DXF parser unit tests
    test_storage.py             # Storage service tests
    test_api_projects.py        # API integration tests
    fixtures/                   # Generated test GDS/DXF files (created by conftest)
```

### Frontend (`frontend/`)

```
frontend/
  package.json
  vite.config.ts
  tsconfig.json
  index.html
  src/
    main.tsx                    # React entry
    App.tsx                     # Root layout with header, panels, viewer
    api/
      client.ts                # Axios instance + base config
      projects.ts              # API calls: upload, list, get, delete, getLayout
    store/
      useProjectStore.ts       # Zustand store: current project, layout data, loading states
    components/
      FileUpload.tsx            # Drag-and-drop upload with progress
      LayoutViewer.tsx          # deck.gl viewer with SolidPolygonLayer
      ProjectList.tsx           # List of uploaded projects
    types/
      index.ts                 # TypeScript interfaces: Project, LayoutData, Geometry, etc.
```

---

## Task 1: Backend Project Scaffolding & Dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/config.py`
- Create: `backend/main.py`
- Create: `backend/models/project.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.12
uvicorn==0.34.2
python-multipart==0.0.20
gdstk==0.9.60
ezdxf==1.4.2
pydantic==2.11.3
pytest==8.4.0
httpx==0.28.1
```

- [ ] **Step 2: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`
Expected: All packages install successfully.

- [ ] **Step 3: Create config.py**

```python
from pathlib import Path

STORAGE_DIR = Path(__file__).parent.parent / "storage" / "projects"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".gds", ".gds2", ".gdsii", ".dxf"}
MAX_FILE_SIZE_MB = 100
```

- [ ] **Step 4: Create Pydantic models in models/project.py**

```python
from pydantic import BaseModel


class Bounds(BaseModel):
    min_x: float
    min_y: float
    max_x: float
    max_y: float


class LayerInfo(BaseModel):
    layer: int
    datatype: int
    name: str
    polygon_count: int


class Geometry(BaseModel):
    id: str
    type: str  # "polygon" or "path"
    layer: int
    datatype: int
    points: list[list[float]]
    properties: dict = {}


class LayoutData(BaseModel):
    bounds: Bounds
    layers: list[LayerInfo]
    geometries: list[Geometry]


class ProjectInfo(BaseModel):
    id: str
    name: str
    file_type: str
    file_size: int
    created_at: str
    layer_count: int
    geometry_count: int
```

- [ ] **Step 5: Create main.py with CORS and health check**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PAM Layout Optimization Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 6: Verify server starts**

Run: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 &`
Then: `curl http://localhost:8000/api/health`
Expected: `{"status":"ok"}`
Then: kill the background server.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI project with models and config"
```

---

## Task 2: Storage Service

**Files:**
- Create: `backend/services/storage.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_storage.py`

- [ ] **Step 1: Write the failing test for storage service**

Create `backend/tests/conftest.py`:

```python
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_storage(monkeypatch):
    """Create a temporary storage directory and patch config to use it."""
    tmp = Path(tempfile.mkdtemp())
    import config
    monkeypatch.setattr(config, "STORAGE_DIR", tmp)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)
```

Create `backend/tests/test_storage.py`:

```python
from pathlib import Path

from services.storage import StorageService


def test_create_project(tmp_storage):
    svc = StorageService()
    project_id = svc.create_project("test.gds", b"fake gds content")
    assert (tmp_storage / project_id).is_dir()
    assert (tmp_storage / project_id / "original.gds").read_bytes() == b"fake gds content"


def test_create_project_dxf(tmp_storage):
    svc = StorageService()
    project_id = svc.create_project("layout.dxf", b"fake dxf content")
    assert (tmp_storage / project_id / "original.dxf").read_bytes() == b"fake dxf content"


def test_list_projects_empty(tmp_storage):
    svc = StorageService()
    assert svc.list_projects() == []


def test_list_projects(tmp_storage):
    svc = StorageService()
    svc.create_project("a.gds", b"data")
    svc.create_project("b.dxf", b"data")
    projects = svc.list_projects()
    assert len(projects) == 2


def test_get_project(tmp_storage):
    svc = StorageService()
    pid = svc.create_project("test.gds", b"data")
    info = svc.get_project(pid)
    assert info["name"] == "test.gds"
    assert info["file_type"] == "gds"


def test_delete_project(tmp_storage):
    svc = StorageService()
    pid = svc.create_project("test.gds", b"data")
    svc.delete_project(pid)
    assert not (tmp_storage / pid).exists()


def test_get_nonexistent_project(tmp_storage):
    svc = StorageService()
    assert svc.get_project("nonexistent") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_storage.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.storage'`

- [ ] **Step 3: Implement StorageService**

Create `backend/services/__init__.py` (empty file).

Create `backend/services/storage.py`:

```python
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import config


class StorageService:
    def _root(self) -> Path:
        return config.STORAGE_DIR

    def create_project(self, filename: str, content: bytes) -> str:
        project_id = uuid.uuid4().hex[:12]
        project_dir = self._root() / project_id
        project_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(filename).suffix.lower()
        file_type = "dxf" if suffix == ".dxf" else "gds"
        original_file = project_dir / f"original.{file_type}"
        original_file.write_bytes(content)

        meta = {
            "id": project_id,
            "name": filename,
            "file_type": file_type,
            "file_size": len(content),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (project_dir / "meta.json").write_text(json.dumps(meta))
        return project_id

    def list_projects(self) -> list[dict]:
        root = self._root()
        if not root.exists():
            return []
        projects = []
        for d in sorted(root.iterdir()):
            meta_file = d / "meta.json"
            if meta_file.exists():
                projects.append(json.loads(meta_file.read_text()))
        return projects

    def get_project(self, project_id: str) -> dict | None:
        meta_file = self._root() / project_id / "meta.json"
        if not meta_file.exists():
            return None
        return json.loads(meta_file.read_text())

    def delete_project(self, project_id: str) -> bool:
        project_dir = self._root() / project_id
        if not project_dir.exists():
            return False
        shutil.rmtree(project_dir)
        return True

    def get_project_dir(self, project_id: str) -> Path | None:
        project_dir = self._root() / project_id
        return project_dir if project_dir.exists() else None

    def save_json(self, project_id: str, filename: str, data: dict) -> None:
        project_dir = self._root() / project_id
        (project_dir / filename).write_text(json.dumps(data))

    def load_json(self, project_id: str, filename: str) -> dict | None:
        f = self._root() / project_id / filename
        if not f.exists():
            return None
        return json.loads(f.read_text())
```

Also create `backend/models/__init__.py` (empty file).

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_storage.py -v`
Expected: All 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/ backend/tests/ backend/models/__init__.py
git commit -m "feat(backend): add storage service with file system operations"
```

---

## Task 3: GDS Parser

**Files:**
- Create: `backend/services/parser_gds.py`
- Create: `backend/tests/test_parser_gds.py`

- [ ] **Step 1: Write the failing test with a generated test GDS file**

Add to `backend/tests/conftest.py`:

```python
import gdstk


@pytest.fixture
def sample_gds_path(tmp_path):
    """Generate a simple GDS file with known geometry for testing."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # Layer 1: a rectangle (ME1)
    rect1 = gdstk.rectangle((0, 0), (100, 50), layer=1, datatype=0)
    cell.add(rect1)

    # Layer 2: a rectangle (ME2)
    rect2 = gdstk.rectangle((10, 10), (90, 40), layer=2, datatype=0)
    cell.add(rect2)

    # Layer 3: a polygon (TFR - resistor strip)
    poly = gdstk.rectangle((200, 0), (250, 10), layer=3, datatype=0)
    cell.add(poly)

    # Layer 1: another polygon
    rect3 = gdstk.rectangle((0, 100), (30, 130), layer=1, datatype=0)
    cell.add(rect3)

    gds_path = tmp_path / "test.gds"
    lib.write_gds(str(gds_path))
    return gds_path
```

Create `backend/tests/test_parser_gds.py`:

```python
from services.parser_gds import parse_gds


def test_parse_gds_returns_layout_data(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    assert "bounds" in result
    assert "layers" in result
    assert "geometries" in result


def test_parse_gds_bounds(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    b = result["bounds"]
    assert b["min_x"] == 0.0
    assert b["min_y"] == 0.0
    assert b["max_x"] == 250.0
    assert b["max_y"] == 130.0


def test_parse_gds_layers(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    layers = result["layers"]
    layer_names = {l["name"] for l in layers}
    assert "1/0" in layer_names
    assert "2/0" in layer_names
    assert "3/0" in layer_names


def test_parse_gds_geometry_count(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    assert len(result["geometries"]) == 4


def test_parse_gds_geometry_structure(sample_gds_path):
    result = parse_gds(str(sample_gds_path))
    geo = result["geometries"][0]
    assert "id" in geo
    assert "type" in geo
    assert "layer" in geo
    assert "datatype" in geo
    assert "points" in geo
    assert isinstance(geo["points"], list)
    assert len(geo["points"]) >= 3  # at least a triangle
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_parser_gds.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.parser_gds'`

- [ ] **Step 3: Implement GDS parser**

Create `backend/services/parser_gds.py`:

```python
import gdstk


def parse_gds(file_path: str) -> dict:
    """Parse a GDS file and return unified layout data dict."""
    lib = gdstk.read_gds(file_path)

    all_polygons = []
    for cell in lib.cells:
        all_polygons.extend(_collect_cell_polygons(cell))

    if not all_polygons:
        return {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0},
            "layers": [],
            "geometries": [],
        }

    # Build geometries
    geometries = []
    layer_stats: dict[str, int] = {}
    all_x, all_y = [], []

    for idx, (layer, datatype, points) in enumerate(all_polygons):
        geo_id = f"poly_{idx:06d}"
        geometries.append({
            "id": geo_id,
            "type": "polygon",
            "layer": layer,
            "datatype": datatype,
            "points": points,
            "properties": {},
        })

        layer_name = f"{layer}/{datatype}"
        layer_stats[layer_name] = layer_stats.get(layer_name, 0) + 1

        for x, y in points:
            all_x.append(x)
            all_y.append(y)

    bounds = {
        "min_x": min(all_x),
        "min_y": min(all_y),
        "max_x": max(all_x),
        "max_y": max(all_y),
    }

    layers = []
    for name, count in sorted(layer_stats.items()):
        parts = name.split("/")
        layers.append({
            "layer": int(parts[0]),
            "datatype": int(parts[1]),
            "name": name,
            "polygon_count": count,
        })

    return {"bounds": bounds, "layers": layers, "geometries": geometries}


def _collect_cell_polygons(cell) -> list[tuple[int, int, list[list[float]]]]:
    """Collect all polygons from a cell, flattening references."""
    results = []

    for polygon in cell.polygons:
        points = polygon.points.tolist()
        results.append((polygon.layer, polygon.datatype, points))

    for path in cell.paths:
        for polygon in path.to_polygons():
            points = polygon.points.tolist()
            results.append((polygon.layer, polygon.datatype, points))

    for ref in cell.references:
        ref_polygons = ref.cell.get_polygons()
        for polygon in ref_polygons:
            points = polygon.points.tolist()
            results.append((polygon.layer, polygon.datatype, points))

    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_parser_gds.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/parser_gds.py backend/tests/test_parser_gds.py backend/tests/conftest.py
git commit -m "feat(backend): add GDS parser using gdstk"
```

---

## Task 4: DXF Parser

**Files:**
- Create: `backend/services/parser_dxf.py`
- Create: `backend/tests/test_parser_dxf.py`

- [ ] **Step 1: Write the failing test with a generated test DXF file**

Add to `backend/tests/conftest.py`:

```python
import ezdxf


@pytest.fixture
def sample_dxf_path(tmp_path):
    """Generate a simple DXF file with known geometry for testing."""
    doc = ezdxf.new()
    msp = doc.modelspace()

    # Create layers
    doc.layers.add("LAYER1", color=1)
    doc.layers.add("LAYER2", color=2)
    doc.layers.add("LAYER3", color=3)

    # LAYER1: a closed polyline (rectangle)
    msp.add_lwpolyline(
        [(0, 0), (100, 0), (100, 50), (0, 50)],
        close=True,
        dxfattribs={"layer": "LAYER1"},
    )

    # LAYER2: a closed polyline
    msp.add_lwpolyline(
        [(10, 10), (90, 10), (90, 40), (10, 40)],
        close=True,
        dxfattribs={"layer": "LAYER2"},
    )

    # LAYER3: a closed polyline (resistor strip)
    msp.add_lwpolyline(
        [(200, 0), (250, 0), (250, 10), (200, 10)],
        close=True,
        dxfattribs={"layer": "LAYER3"},
    )

    dxf_path = tmp_path / "test.dxf"
    doc.saveas(str(dxf_path))
    return dxf_path
```

Create `backend/tests/test_parser_dxf.py`:

```python
from services.parser_dxf import parse_dxf


def test_parse_dxf_returns_layout_data(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    assert "bounds" in result
    assert "layers" in result
    assert "geometries" in result


def test_parse_dxf_bounds(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    b = result["bounds"]
    assert b["min_x"] == 0.0
    assert b["min_y"] == 0.0
    assert b["max_x"] == 250.0
    assert b["max_y"] == 50.0


def test_parse_dxf_layers(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    layer_names = {l["name"] for l in result["layers"]}
    assert "LAYER1" in layer_names
    assert "LAYER2" in layer_names
    assert "LAYER3" in layer_names


def test_parse_dxf_geometry_count(sample_dxf_path):
    result = parse_dxf(str(sample_dxf_path))
    assert len(result["geometries"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_parser_dxf.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.parser_dxf'`

- [ ] **Step 3: Implement DXF parser**

Create `backend/services/parser_dxf.py`:

```python
import ezdxf


def parse_dxf(file_path: str) -> dict:
    """Parse a DXF file and return unified layout data dict."""
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()

    # Build a layer name -> integer index mapping
    layer_index: dict[str, int] = {}
    for i, layer_def in enumerate(doc.layers):
        layer_index[layer_def.dxf.name] = i

    geometries = []
    layer_stats: dict[str, int] = {}
    all_x: list[float] = []
    all_y: list[float] = []
    poly_idx = 0

    for entity in msp:
        points = _entity_to_points(entity)
        if not points:
            continue

        layer_name = entity.dxf.layer
        layer_num = layer_index.get(layer_name, 0)

        geo_id = f"poly_{poly_idx:06d}"
        geometries.append({
            "id": geo_id,
            "type": "polygon",
            "layer": layer_num,
            "datatype": 0,
            "points": points,
            "properties": {"dxf_layer": layer_name},
        })
        poly_idx += 1

        layer_stats[layer_name] = layer_stats.get(layer_name, 0) + 1
        for x, y in points:
            all_x.append(x)
            all_y.append(y)

    if not geometries:
        return {
            "bounds": {"min_x": 0, "min_y": 0, "max_x": 0, "max_y": 0},
            "layers": [],
            "geometries": [],
        }

    bounds = {
        "min_x": min(all_x),
        "min_y": min(all_y),
        "max_x": max(all_x),
        "max_y": max(all_y),
    }

    layers = []
    for name, count in sorted(layer_stats.items()):
        layers.append({
            "layer": layer_index.get(name, 0),
            "datatype": 0,
            "name": name,
            "polygon_count": count,
        })

    return {"bounds": bounds, "layers": layers, "geometries": geometries}


def _entity_to_points(entity) -> list[list[float]] | None:
    """Convert a DXF entity to a list of [x, y] points. Returns None if unsupported."""
    dxf_type = entity.dxftype()

    if dxf_type == "LWPOLYLINE":
        return [[p[0], p[1]] for p in entity.get_points(format="xy")]

    if dxf_type == "LINE":
        s = entity.dxf.start
        e = entity.dxf.end
        return [[s.x, s.y], [e.x, e.y]]

    if dxf_type == "CIRCLE":
        import math
        cx, cy = entity.dxf.center.x, entity.dxf.center.y
        r = entity.dxf.radius
        n = 32
        return [
            [cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)]
            for i in range(n)
        ]

    if dxf_type == "POLYLINE":
        return [[v.dxf.location.x, v.dxf.location.y] for v in entity.vertices]

    if dxf_type == "HATCH":
        points = []
        for path in entity.paths:
            if hasattr(path, "vertices"):
                points.extend([[v[0], v[1]] for v in path.vertices])
        return points if points else None

    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_parser_dxf.py -v`
Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/parser_dxf.py backend/tests/test_parser_dxf.py backend/tests/conftest.py
git commit -m "feat(backend): add DXF parser using ezdxf"
```

---

## Task 5: Unified Parser Interface

**Files:**
- Create: `backend/services/parser.py`
- Create: `backend/tests/test_parser.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_parser.py`:

```python
import pytest
from services.parser import parse_layout


def test_parse_gds(sample_gds_path):
    result = parse_layout(str(sample_gds_path))
    assert len(result["geometries"]) == 4


def test_parse_dxf(sample_dxf_path):
    result = parse_layout(str(sample_dxf_path))
    assert len(result["geometries"]) == 3


def test_parse_unknown_format(tmp_path):
    f = tmp_path / "test.xyz"
    f.write_text("garbage")
    with pytest.raises(ValueError, match="Unsupported file format"):
        parse_layout(str(f))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_parser.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement unified parser**

Create `backend/services/parser.py`:

```python
from pathlib import Path

from services.parser_gds import parse_gds
from services.parser_dxf import parse_dxf


def parse_layout(file_path: str) -> dict:
    """Parse a layout file (GDS or DXF) and return unified geometry data."""
    suffix = Path(file_path).suffix.lower()

    if suffix in (".gds", ".gds2", ".gdsii"):
        return parse_gds(file_path)
    elif suffix == ".dxf":
        return parse_dxf(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_parser.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/services/parser.py backend/tests/test_parser.py
git commit -m "feat(backend): add unified parser interface for GDS/DXF"
```

---

## Task 6: API Endpoints (Projects CRUD + Layout)

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/projects.py`
- Create: `backend/tests/test_api_projects.py`
- Modify: `backend/main.py` — mount the router

- [ ] **Step 1: Write the failing API tests**

Create `backend/routers/__init__.py` (empty file).

Create `backend/tests/test_api_projects.py`:

```python
import io
import gdstk
import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(tmp_storage):
    return TestClient(app)


@pytest.fixture
def gds_bytes():
    """Generate a minimal GDS file in memory."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")
    cell.add(gdstk.rectangle((0, 0), (100, 50), layer=1))
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".gds", delete=False)
    lib.write_gds(tmp.name)
    data = open(tmp.name, "rb").read()
    os.unlink(tmp.name)
    return data


def test_upload_gds(client, gds_bytes):
    resp = client.post(
        "/api/projects/upload",
        files={"file": ("test.gds", io.BytesIO(gds_bytes), "application/octet-stream")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["name"] == "test.gds"


def test_list_projects(client, gds_bytes):
    client.post("/api/projects/upload", files={"file": ("a.gds", io.BytesIO(gds_bytes))})
    client.post("/api/projects/upload", files={"file": ("b.gds", io.BytesIO(gds_bytes))})
    resp = client.get("/api/projects")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_project(client, gds_bytes):
    upload = client.post("/api/projects/upload", files={"file": ("test.gds", io.BytesIO(gds_bytes))})
    pid = upload.json()["id"]
    resp = client.get(f"/api/projects/{pid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == pid


def test_get_project_not_found(client):
    resp = client.get("/api/projects/nonexistent")
    assert resp.status_code == 404


def test_delete_project(client, gds_bytes):
    upload = client.post("/api/projects/upload", files={"file": ("test.gds", io.BytesIO(gds_bytes))})
    pid = upload.json()["id"]
    resp = client.delete(f"/api/projects/{pid}")
    assert resp.status_code == 200
    resp2 = client.get(f"/api/projects/{pid}")
    assert resp2.status_code == 404


def test_get_layout(client, gds_bytes):
    upload = client.post("/api/projects/upload", files={"file": ("test.gds", io.BytesIO(gds_bytes))})
    pid = upload.json()["id"]
    resp = client.get(f"/api/projects/{pid}/layout")
    assert resp.status_code == 200
    data = resp.json()
    assert "bounds" in data
    assert "layers" in data
    assert "geometries" in data
    assert len(data["geometries"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_projects.py -v`
Expected: FAIL — 404 errors because router not mounted.

- [ ] **Step 3: Implement projects router**

Create `backend/routers/projects.py`:

```python
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pathlib import Path

from services.storage import StorageService
from services.parser import parse_layout
import config

router = APIRouter(prefix="/api/projects", tags=["projects"])
storage = StorageService()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    content = await file.read()
    if len(content) > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"File too large (max {config.MAX_FILE_SIZE_MB}MB)")

    project_id = storage.create_project(file.filename, content)

    # Parse immediately and cache
    project_dir = storage.get_project_dir(project_id)
    meta = storage.get_project(project_id)
    original_file = project_dir / f"original.{meta['file_type']}"
    layout_data = parse_layout(str(original_file))
    storage.save_json(project_id, "layout_data.json", layout_data)

    # Update meta with counts
    meta["layer_count"] = len(layout_data["layers"])
    meta["geometry_count"] = len(layout_data["geometries"])
    storage.save_json(project_id, "meta.json", meta)

    return meta


@router.get("")
def list_projects():
    return storage.list_projects()


@router.get("/{project_id}")
def get_project(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")
    return info


@router.delete("/{project_id}")
def delete_project(project_id: str):
    if not storage.delete_project(project_id):
        raise HTTPException(404, "Project not found")
    return {"status": "deleted"}


@router.get("/{project_id}/layout")
def get_layout(
    project_id: str,
    layers: str | None = Query(None, description="Comma-separated layer numbers to filter"),
):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(404, "Layout data not found. Re-upload the file.")

    if layers:
        layer_set = {int(l.strip()) for l in layers.split(",")}
        layout_data["geometries"] = [
            g for g in layout_data["geometries"] if g["layer"] in layer_set
        ]

    return layout_data
```

- [ ] **Step 4: Mount router in main.py**

Update `backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.projects import router as projects_router

app = FastAPI(title="PAM Layout Optimization Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_projects.py -v`
Expected: All 6 tests PASS.

- [ ] **Step 6: Run ALL backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS (storage + gds parser + dxf parser + parser + api).

- [ ] **Step 7: Commit**

```bash
git add backend/routers/ backend/tests/test_api_projects.py backend/main.py
git commit -m "feat(backend): add project CRUD and layout API endpoints"
```

---

## Task 7: Frontend Scaffolding

**Files:**
- Create: `frontend/` (entire Vite + React + TypeScript project)

- [ ] **Step 1: Scaffold the Vite React project**

Run:
```bash
cd /root/pam/pam-tool-use-opus-v4
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install deck.gl @deck.gl/core @deck.gl/layers @deck.gl/react @luma.gl/engine @luma.gl/webgl
npm install antd @ant-design/icons
npm install zustand axios
```

Expected: Project scaffolded, all deps installed.

- [ ] **Step 2: Create TypeScript types**

Create `frontend/src/types/index.ts`:

```typescript
export interface Bounds {
  min_x: number;
  min_y: number;
  max_x: number;
  max_y: number;
}

export interface LayerInfo {
  layer: number;
  datatype: number;
  name: string;
  polygon_count: number;
}

export interface Geometry {
  id: string;
  type: string;
  layer: number;
  datatype: number;
  points: number[][];
  properties: Record<string, unknown>;
}

export interface LayoutData {
  bounds: Bounds;
  layers: LayerInfo[];
  geometries: Geometry[];
}

export interface ProjectInfo {
  id: string;
  name: string;
  file_type: string;
  file_size: number;
  created_at: string;
  layer_count?: number;
  geometry_count?: number;
}
```

- [ ] **Step 3: Create API client**

Create `frontend/src/api/client.ts`:

```typescript
import axios from "axios";

const apiClient = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 60000,
});

export default apiClient;
```

Create `frontend/src/api/projects.ts`:

```typescript
import apiClient from "./client";
import type { ProjectInfo, LayoutData } from "../types";

export async function uploadFile(file: File): Promise<ProjectInfo> {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await apiClient.post("/api/projects/upload", formData);
  return resp.data;
}

export async function listProjects(): Promise<ProjectInfo[]> {
  const resp = await apiClient.get("/api/projects");
  return resp.data;
}

export async function getProject(id: string): Promise<ProjectInfo> {
  const resp = await apiClient.get(`/api/projects/${id}`);
  return resp.data;
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/api/projects/${id}`);
}

export async function getLayout(
  id: string,
  layers?: number[]
): Promise<LayoutData> {
  const params: Record<string, string> = {};
  if (layers && layers.length > 0) {
    params.layers = layers.join(",");
  }
  const resp = await apiClient.get(`/api/projects/${id}/layout`, { params });
  return resp.data;
}
```

- [ ] **Step 4: Create Zustand store**

Create `frontend/src/store/useProjectStore.ts`:

```typescript
import { create } from "zustand";
import type { ProjectInfo, LayoutData } from "../types";
import * as projectsApi from "../api/projects";

interface ProjectState {
  projects: ProjectInfo[];
  currentProject: ProjectInfo | null;
  layoutData: LayoutData | null;
  loading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  selectProject: (id: string) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  projects: [],
  currentProject: null,
  layoutData: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await projectsApi.listProjects();
      set({ projects, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  uploadFile: async (file: File) => {
    set({ loading: true, error: null });
    try {
      const project = await projectsApi.uploadFile(file);
      set((s) => ({
        projects: [...s.projects, project],
        currentProject: project,
        loading: false,
      }));
      // Auto-load layout after upload
      await get().selectProject(project.id);
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  selectProject: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const [project, layoutData] = await Promise.all([
        projectsApi.getProject(id),
        projectsApi.getLayout(id),
      ]);
      set({ currentProject: project, layoutData, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  deleteProject: async (id: string) => {
    try {
      await projectsApi.deleteProject(id);
      set((s) => ({
        projects: s.projects.filter((p) => p.id !== id),
        currentProject: s.currentProject?.id === id ? null : s.currentProject,
        layoutData: s.currentProject?.id === id ? null : s.layoutData,
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  clearError: () => set({ error: null }),
}));
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold React+Vite project with types, API client, and store"
```

---

## Task 8: FileUpload Component

**Files:**
- Create: `frontend/src/components/FileUpload.tsx`

- [ ] **Step 1: Implement FileUpload component**

Create `frontend/src/components/FileUpload.tsx`:

```tsx
import { Upload, message } from "antd";
import { InboxOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";

const { Dragger } = Upload;

export default function FileUpload() {
  const { uploadFile, loading } = useProjectStore();

  const handleUpload = async (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["gds", "gds2", "gdsii", "dxf"].includes(ext)) {
      message.error("仅支持 GDS 和 DXF 格式文件");
      return false;
    }
    try {
      await uploadFile(file);
      message.success(`${file.name} 上传解析成功`);
    } catch {
      message.error(`${file.name} 上传失败`);
    }
    return false; // prevent default upload
  };

  return (
    <Dragger
      accept=".gds,.gds2,.gdsii,.dxf"
      showUploadList={false}
      beforeUpload={handleUpload}
      disabled={loading}
      style={{ padding: "20px" }}
    >
      <p className="ant-upload-drag-icon">
        <InboxOutlined />
      </p>
      <p className="ant-upload-text">点击或拖拽版图文件到此区域上传</p>
      <p className="ant-upload-hint">支持 GDS、DXF 格式</p>
    </Dragger>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/FileUpload.tsx
git commit -m "feat(frontend): add FileUpload component with drag-and-drop"
```

---

## Task 9: LayoutViewer Component (deck.gl)

**Files:**
- Create: `frontend/src/components/LayoutViewer.tsx`

- [ ] **Step 1: Implement LayoutViewer with deck.gl**

Create `frontend/src/components/LayoutViewer.tsx`:

```tsx
import { useMemo, useState, useCallback } from "react";
import DeckGL from "@deck.gl/react";
import { SolidPolygonLayer } from "@deck.gl/layers";
import { OrthographicView } from "@deck.gl/core";
import { useProjectStore } from "../store/useProjectStore";
import type { Geometry } from "../types";

// Distinct colors per layer
const LAYER_COLORS: Record<number, [number, number, number, number]> = {
  0: [65, 105, 225, 160],   // Royal Blue
  1: [220, 20, 60, 160],    // Crimson
  2: [50, 205, 50, 160],    // Lime Green
  3: [255, 165, 0, 160],    // Orange
  4: [148, 103, 189, 160],  // Purple
  5: [255, 215, 0, 160],    // Gold
  6: [0, 206, 209, 160],    // Dark Turquoise
  7: [255, 99, 71, 160],    // Tomato
};

const HIGHLIGHT_COLOR: [number, number, number, number] = [255, 255, 0, 220];

function getLayerColor(layer: number): [number, number, number, number] {
  return LAYER_COLORS[layer % Object.keys(LAYER_COLORS).length] ?? [128, 128, 128, 160];
}

export default function LayoutViewer() {
  const { layoutData } = useProjectStore();
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const initialViewState = useMemo(() => {
    if (!layoutData) return { target: [0, 0, 0], zoom: 0 };
    const { bounds } = layoutData;
    const cx = (bounds.min_x + bounds.max_x) / 2;
    const cy = (bounds.min_y + bounds.max_y) / 2;
    const dx = bounds.max_x - bounds.min_x;
    const dy = bounds.max_y - bounds.min_y;
    const span = Math.max(dx, dy, 1);
    // Fit into roughly 800px viewport
    const zoom = Math.log2(800 / span);
    return { target: [cx, cy, 0], zoom };
  }, [layoutData]);

  const onHover = useCallback((info: any) => {
    setHoveredId(info.object?.id ?? null);
  }, []);

  const onClick = useCallback((info: any) => {
    setSelectedId(info.object?.id ?? null);
  }, []);

  const layers = useMemo(() => {
    if (!layoutData || layoutData.geometries.length === 0) return [];

    return [
      new SolidPolygonLayer<Geometry>({
        id: "layout-polygons",
        data: layoutData.geometries,
        getPolygon: (d: Geometry) => d.points as any,
        getFillColor: (d: Geometry) => {
          if (d.id === selectedId || d.id === hoveredId) return HIGHLIGHT_COLOR;
          return getLayerColor(d.layer);
        },
        getLineColor: [0, 0, 0, 255],
        lineWidthMinPixels: 1,
        pickable: true,
        updateTriggers: {
          getFillColor: [hoveredId, selectedId],
        },
      }),
    ];
  }, [layoutData, hoveredId, selectedId]);

  if (!layoutData) {
    return (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#999",
          fontSize: 16,
        }}
      >
        请上传版图文件
      </div>
    );
  }

  return (
    <DeckGL
      views={new OrthographicView({ id: "ortho" })}
      initialViewState={initialViewState}
      controller={true}
      layers={layers}
      onHover={onHover}
      onClick={onClick}
      style={{ width: "100%", height: "100%" }}
      getCursor={({ isHovering }: { isHovering: boolean }) =>
        isHovering ? "pointer" : "grab"
      }
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/LayoutViewer.tsx
git commit -m "feat(frontend): add deck.gl LayoutViewer with polygon rendering and selection"
```

---

## Task 10: ProjectList Component

**Files:**
- Create: `frontend/src/components/ProjectList.tsx`

- [ ] **Step 1: Implement ProjectList**

Create `frontend/src/components/ProjectList.tsx`:

```tsx
import { useEffect } from "react";
import { List, Button, Typography, Popconfirm, Tag, Empty } from "antd";
import { DeleteOutlined, FolderOpenOutlined } from "@ant-design/icons";
import { useProjectStore } from "../store/useProjectStore";

const { Text } = Typography;

export default function ProjectList() {
  const { projects, currentProject, fetchProjects, selectProject, deleteProject } =
    useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  if (projects.length === 0) {
    return <Empty description="暂无项目" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <List
      size="small"
      dataSource={projects}
      renderItem={(item) => (
        <List.Item
          style={{
            cursor: "pointer",
            backgroundColor: currentProject?.id === item.id ? "#e6f4ff" : undefined,
            padding: "8px 12px",
          }}
          onClick={() => selectProject(item.id)}
          actions={[
            <Popconfirm
              title="确定删除此项目？"
              onConfirm={(e) => {
                e?.stopPropagation();
                deleteProject(item.id);
              }}
              onCancel={(e) => e?.stopPropagation()}
              key="delete"
            >
              <Button
                type="text"
                danger
                size="small"
                icon={<DeleteOutlined />}
                onClick={(e) => e.stopPropagation()}
              />
            </Popconfirm>,
          ]}
        >
          <List.Item.Meta
            avatar={<FolderOpenOutlined style={{ fontSize: 18 }} />}
            title={<Text ellipsis={{ tooltip: item.name }}>{item.name}</Text>}
            description={
              <span>
                <Tag color={item.file_type === "gds" ? "blue" : "green"}>
                  {item.file_type.toUpperCase()}
                </Tag>
                {item.geometry_count != null && (
                  <Text type="secondary">{item.geometry_count} 个图形</Text>
                )}
              </span>
            }
          />
        </List.Item>
      )}
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ProjectList.tsx
git commit -m "feat(frontend): add ProjectList component"
```

---

## Task 11: App Layout Assembly & Integration Test

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/index.html`

- [ ] **Step 1: Update App.tsx with full layout**

Replace `frontend/src/App.tsx`:

```tsx
import { Layout, Typography, Spin, Alert } from "antd";
import FileUpload from "./components/FileUpload";
import ProjectList from "./components/ProjectList";
import LayoutViewer from "./components/LayoutViewer";
import { useProjectStore } from "./store/useProjectStore";

const { Header, Sider, Content, Footer } = Layout;
const { Title } = Typography;

export default function App() {
  const { loading, error, clearError, currentProject } = useProjectStore();

  return (
    <Layout style={{ height: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          background: "#001529",
          padding: "0 24px",
        }}
      >
        <Title level={4} style={{ color: "#fff", margin: 0 }}>
          PAM 版图优化工具
        </Title>
        {currentProject && (
          <Typography.Text style={{ color: "#aaa" }}>
            当前: {currentProject.name}
          </Typography.Text>
        )}
        {loading && <Spin size="small" />}
      </Header>

      {error && (
        <Alert
          message={error}
          type="error"
          closable
          onClose={clearError}
          style={{ margin: 0 }}
        />
      )}

      <Layout>
        <Sider width={280} theme="light" style={{ padding: 12, overflowY: "auto" }}>
          <FileUpload />
          <div style={{ marginTop: 16 }}>
            <Typography.Text strong>项目列表</Typography.Text>
            <ProjectList />
          </div>
        </Sider>

        <Content style={{ position: "relative", background: "#1a1a2e" }}>
          <LayoutViewer />
        </Content>
      </Layout>

      <Footer style={{ textAlign: "center", padding: "8px 24px", fontSize: 12 }}>
        PAM Layout Optimization Tool v0.1
      </Footer>
    </Layout>
  );
}
```

- [ ] **Step 2: Update main.tsx**

Replace `frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ConfigProvider locale={zhCN}>
      <App />
    </ConfigProvider>
  </StrictMode>
);
```

- [ ] **Step 3: Update index.css for full-height layout**

Replace `frontend/src/index.css`:

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #root {
  height: 100%;
  width: 100%;
}
```

Delete `frontend/src/App.css` if it exists (not used).

- [ ] **Step 4: Update vite.config.ts to proxy API requests**

Replace `frontend/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

If using the proxy, also update `frontend/src/api/client.ts` to remove the hardcoded base URL:

```typescript
import axios from "axios";

const apiClient = axios.create({
  baseURL: "",
  timeout: 60000,
});

export default apiClient;
```

- [ ] **Step 5: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build completes without errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): assemble App layout with viewer, upload, and project list"
```

---

## Task 12: End-to-End Smoke Test

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 2: Start backend server**

Run: `cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000 &`

- [ ] **Step 3: Test upload via curl with a generated GDS**

Run:
```bash
cd backend && python -c "
import gdstk
lib = gdstk.Library()
cell = lib.new_cell('TOP')
cell.add(gdstk.rectangle((0,0),(100,50), layer=1))
cell.add(gdstk.rectangle((10,10),(90,40), layer=2))
lib.write_gds('/tmp/test_smoke.gds')
print('Generated test GDS')
"
curl -X POST http://localhost:8000/api/projects/upload \
  -F "file=@/tmp/test_smoke.gds" | python -m json.tool
```

Expected: JSON response with project id, name, layer_count, geometry_count.

- [ ] **Step 4: Test layout endpoint**

Run: `curl http://localhost:8000/api/projects | python -m json.tool` — should list the project.
Then get the project id from the response and: `curl http://localhost:8000/api/projects/{id}/layout | python -m json.tool` — should return bounds, layers, geometries.

- [ ] **Step 5: Stop backend, create .gitignore, final commit**

Create root `.gitignore`:

```
__pycache__/
*.pyc
.pytest_cache/
node_modules/
dist/
.vite/
storage/
*.egg-info/
.env
```

```bash
kill %1  # stop background server
git add .gitignore
git commit -m "chore: add .gitignore and complete P1 smoke test"
```

- [ ] **Step 6: Push to remote**

```bash
git push -u origin main
```

Expected: Push succeeds to https://github.com/anycode3/pam-tool-use-opus46-v4

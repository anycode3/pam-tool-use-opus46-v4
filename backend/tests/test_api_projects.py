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

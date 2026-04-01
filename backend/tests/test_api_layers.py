import io
import os
import tempfile

import gdstk
from fastapi.testclient import TestClient

from main import app


def _upload_gds(client):
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")
    cell.add(gdstk.rectangle((0, 0), (100, 50), layer=1))
    cell.add(gdstk.rectangle((10, 10), (90, 40), layer=2))
    cell.add(gdstk.rectangle((200, 0), (250, 10), layer=3))
    tmp = tempfile.NamedTemporaryFile(suffix=".gds", delete=False)
    lib.write_gds(tmp.name)
    data = open(tmp.name, "rb").read()
    os.unlink(tmp.name)
    resp = client.post("/api/projects/upload", files={"file": ("test.gds", io.BytesIO(data))})
    return resp.json()["id"]


def test_get_layers(client):
    pid = _upload_gds(client)
    resp = client.get(f"/api/projects/{pid}/layers")
    assert resp.status_code == 200
    layers = resp.json()["layers"]
    assert len(layers) == 3
    names = {l["name"] for l in layers}
    assert "1/0" in names


def test_get_layer_mapping_empty(client):
    pid = _upload_gds(client)
    resp = client.get(f"/api/projects/{pid}/layer-mapping")
    assert resp.status_code == 200
    assert resp.json()["mappings"] == {}


def test_put_layer_mapping(client):
    pid = _upload_gds(client)
    mapping = {"1/0": "ME1", "2/0": "ME2", "3/0": "TFR"}
    resp = client.put(f"/api/projects/{pid}/layer-mapping", json={"mappings": mapping})
    assert resp.status_code == 200
    assert resp.json()["mappings"] == mapping


def test_get_layer_mapping_after_save(client):
    pid = _upload_gds(client)
    mapping = {"1/0": "ME1", "2/0": "ME2"}
    client.put(f"/api/projects/{pid}/layer-mapping", json={"mappings": mapping})
    resp = client.get(f"/api/projects/{pid}/layer-mapping")
    assert resp.json()["mappings"] == mapping


def test_put_layer_mapping_invalid_value(client):
    pid = _upload_gds(client)
    resp = client.put(f"/api/projects/{pid}/layer-mapping", json={"mappings": {"1/0": "INVALID"}})
    assert resp.status_code == 400

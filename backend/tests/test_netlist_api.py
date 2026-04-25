import io
import pytest


SIMPLE_SPICE = """* Simple SPICE netlist
L1 VDD NET1 5.6nH
C1 NET1 GND 4.7p
R1 NET1 NET2 10k
"""


SUB_CIRCUIT_SPICE = """* Netlist with subcircuit
L1 VDD NET1 5.6nH
X1 NET1 NET2 MYCAP
R1 NET2 GND 10k

.SUBCKT MYCAP A B
C1 A B 10p
R1 A B 1meg
.ENDS
"""


@pytest.fixture
def project_with_gds(client):
    """Create a project with a minimal GDS to satisfy storage requirements."""
    import gdstk
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")
    cell.add(gdstk.rectangle((0, 0), (100, 50), layer=1))
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".gds", delete=False)
    lib.write_gds(tmp.name)
    data = open(tmp.name, "rb").read()
    os.unlink(tmp.name)
    resp = client.post(
        "/api/projects/upload",
        files={"file": ("test.gds", io.BytesIO(data), "application/octet-stream")},
    )
    return resp.json()["id"]


def test_upload_netlist_sp(project_with_gds, client):
    pid = project_with_gds
    resp = client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.sp", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "uploaded"
    assert data["device_count"] == 3


def test_upload_netlist_cir(project_with_gds, client):
    pid = project_with_gds
    resp = client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.cir", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_count"] == 3


def test_upload_netlist_net(project_with_gds, client):
    pid = project_with_gds
    resp = client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.net", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    assert resp.status_code == 200
    assert resp.json()["device_count"] == 3


def test_upload_netlist_unsupported_extension(project_with_gds, client):
    pid = project_with_gds
    resp = client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.txt", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    assert resp.status_code == 400


def test_upload_netlist_subcircuit(project_with_gds, client):
    pid = project_with_gds
    resp = client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.sp", io.BytesIO(SUB_CIRCUIT_SPICE.encode()))},
    )
    assert resp.status_code == 200
    data = resp.json()
    # X1 is a subcircuit instance, not a primitive device
    assert data["device_count"] == 2  # Top-level: L1, R1 (X1 is subcircuit instance)


def test_get_netlist(project_with_gds, client):
    pid = project_with_gds
    client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.sp", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    resp = client.get(f"/api/projects/{pid}/netlist")
    assert resp.status_code == 200
    data = resp.json()
    assert "raw" in data
    assert "devices" in data
    assert len(data["devices"]) == 3


def test_get_netlist_device_details(project_with_gds, client):
    pid = project_with_gds
    client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.sp", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    resp = client.get(f"/api/projects/{pid}/netlist")
    data = resp.json()
    devices = {d["instance_name"]: d for d in data["devices"]}
    assert devices["L1"]["device_type"] == "inductor"
    assert devices["C1"]["device_type"] == "capacitor"
    assert devices["R1"]["device_type"] == "resistor"


def test_get_netlist_subcircuits(project_with_gds, client):
    pid = project_with_gds
    client.post(
        f"/api/projects/{pid}/netlist/upload",
        files={"file": ("test.sp", io.BytesIO(SUB_CIRCUIT_SPICE.encode()))},
    )
    resp = client.get(f"/api/projects/{pid}/netlist")
    data = resp.json()
    assert "MYCAP" in data["subcircuits"]
    subckt_devices = data["subcircuits"]["MYCAP"]
    assert len(subckt_devices) == 2  # C1 and R1 inside subcircuit


def test_get_netlist_not_found(client):
    resp = client.get("/api/projects/nonexistent/netlist")
    assert resp.status_code == 404


def test_get_netlist_no_netlist_uploaded(project_with_gds, client):
    pid = project_with_gds
    resp = client.get(f"/api/projects/{pid}/netlist")
    assert resp.status_code == 404


def test_upload_netlist_project_not_found(client):
    resp = client.post(
        "/api/projects/nonexistent/netlist/upload",
        files={"file": ("test.sp", io.BytesIO(SIMPLE_SPICE.encode()))},
    )
    assert resp.status_code == 404

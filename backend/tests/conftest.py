import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client(tmp_storage):
    return TestClient(app)


@pytest.fixture
def tmp_storage(monkeypatch):
    """Create a temporary storage directory and patch config to use it."""
    tmp = Path(tempfile.mkdtemp())
    import config
    monkeypatch.setattr(config, "STORAGE_DIR", tmp)
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


import gdstk
import ezdxf


@pytest.fixture
def sample_gds_path(tmp_path):
    """Generate a simple GDS file with known geometry for testing."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")
    rect1 = gdstk.rectangle((0, 0), (100, 50), layer=1, datatype=0)
    cell.add(rect1)
    rect2 = gdstk.rectangle((10, 10), (90, 40), layer=2, datatype=0)
    cell.add(rect2)
    poly = gdstk.rectangle((200, 0), (250, 10), layer=3, datatype=0)
    cell.add(poly)
    rect3 = gdstk.rectangle((0, 100), (30, 130), layer=1, datatype=0)
    cell.add(rect3)
    gds_path = tmp_path / "test.gds"
    lib.write_gds(str(gds_path))
    return gds_path


@pytest.fixture
def sample_dxf_path(tmp_path):
    """Generate a simple DXF file with known geometry for testing."""
    doc = ezdxf.new()
    msp = doc.modelspace()
    doc.layers.add("LAYER1", color=1)
    doc.layers.add("LAYER2", color=2)
    doc.layers.add("LAYER3", color=3)
    msp.add_lwpolyline(
        [(0, 0), (100, 0), (100, 50), (0, 50)],
        close=True,
        dxfattribs={"layer": "LAYER1"},
    )
    msp.add_lwpolyline(
        [(10, 10), (90, 10), (90, 40), (10, 40)],
        close=True,
        dxfattribs={"layer": "LAYER2"},
    )
    msp.add_lwpolyline(
        [(200, 0), (250, 0), (250, 10), (200, 10)],
        close=True,
        dxfattribs={"layer": "LAYER3"},
    )
    dxf_path = tmp_path / "test.dxf"
    doc.saveas(str(dxf_path))
    return dxf_path


@pytest.fixture
def sample_gds_with_devices(tmp_path):
    """GDS with recognizable device patterns."""
    lib = gdstk.Library()
    cell = lib.new_cell("TOP")

    # Capacitor: overlapping ME1 and ME2 rectangles
    cell.add(gdstk.rectangle((0, 0), (50, 50), layer=1, datatype=0))    # ME1
    cell.add(gdstk.rectangle((5, 5), (45, 45), layer=2, datatype=0))    # ME2

    # Resistor: thin strip on TFR layer
    cell.add(gdstk.rectangle((100, 0), (150, 5), layer=3, datatype=0))  # TFR

    # PAD: overlapping on ME1, ME2, VA1
    cell.add(gdstk.rectangle((200, 200), (220, 220), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((200, 200), (220, 220), layer=2, datatype=0))  # ME2
    cell.add(gdstk.rectangle((200, 200), (220, 220), layer=4, datatype=0))  # VA1

    # GND via: overlapping on GND, ME1, ME2, VA1
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=5, datatype=0))  # GND
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=1, datatype=0))  # ME1
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=2, datatype=0))  # ME2
    cell.add(gdstk.rectangle((300, 300), (310, 310), layer=4, datatype=0))  # VA1

    gds_path = tmp_path / "devices.gds"
    lib.write_gds(str(gds_path))
    return gds_path

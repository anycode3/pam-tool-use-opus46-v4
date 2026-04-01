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


import gdstk


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

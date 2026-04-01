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

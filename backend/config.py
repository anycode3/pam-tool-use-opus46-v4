from pathlib import Path

STORAGE_DIR = Path(__file__).parent.parent / "storage" / "projects"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".gds", ".gds2", ".gdsii", ".dxf"}
MAX_FILE_SIZE_MB = 100

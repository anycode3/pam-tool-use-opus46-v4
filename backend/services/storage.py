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

    def save_netlist(self, project_id: str, filename: str, content: str) -> None:
        project_dir = self._root() / project_id
        (project_dir / filename).write_text(content)

    def load_netlist(self, project_id: str, filename: str) -> str | None:
        f = self._root() / project_id / filename
        if not f.exists():
            return None
        return f.read_text()

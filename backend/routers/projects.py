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

import base64

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel

from services.storage import StorageService
from services.parser import parse_layout
from services.device_recognition import recognize_devices
from services.device_modifier import modify_device, apply_modifications
from services.layout_diff import compute_diff
from services.layout_writer import write_layout
from services.drc_engine import run_drc, parse_rules, parse_rule_file, validate_rule
import config

router = APIRouter(prefix="/api/projects", tags=["projects"])
storage = StorageService()

VALID_TARGET_LAYERS = {"ME1", "ME2", "TFR", "VA1", "GND"}


class LayerMappingRequest(BaseModel):
    mappings: dict[str, str]


class RecognizeRequest(BaseModel):
    method: str = "geometry"


class ModifyDeviceRequest(BaseModel):
    new_value: float
    mode: str = "auto"
    manual_params: dict | None = None


class ApplyModificationsRequest(BaseModel):
    modifications: list[str]


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


@router.get("/{project_id}/layers")
def get_layers(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(404, "Layout data not found. Re-upload the file.")

    layers = []
    for layer_info in layout_data.get("layers", []):
        layer_num = layer_info["layer"]
        datatype = layer_info.get("datatype", 0)
        name = f"{layer_num}/{datatype}"
        polygon_count = sum(
            1 for g in layout_data.get("geometries", [])
            if g["layer"] == layer_num
        )
        layers.append({
            "layer": layer_num,
            "datatype": datatype,
            "name": name,
            "polygon_count": polygon_count,
        })

    return {"layers": layers}


@router.get("/{project_id}/layer-mapping")
def get_layer_mapping(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    mapping_data = storage.load_json(project_id, "layer_mapping.json")
    if not mapping_data:
        return {"mappings": {}}
    return mapping_data


@router.put("/{project_id}/layer-mapping")
def put_layer_mapping(project_id: str, body: LayerMappingRequest):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    invalid = [v for v in body.mappings.values() if v not in VALID_TARGET_LAYERS]
    if invalid:
        raise HTTPException(
            400,
            f"Invalid target layer name(s): {invalid}. Must be one of {sorted(VALID_TARGET_LAYERS)}",
        )

    data = {"mappings": body.mappings}
    storage.save_json(project_id, "layer_mapping.json", data)
    return data


@router.post("/{project_id}/devices/recognize")
def recognize_project_devices(project_id: str, body: RecognizeRequest):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    if body.method != "geometry":
        raise HTTPException(400, f"Unsupported recognition method: {body.method}")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(404, "Layout data not found. Upload a file first.")

    mapping_data = storage.load_json(project_id, "layer_mapping.json")
    if not mapping_data or not mapping_data.get("mappings"):
        raise HTTPException(400, "Layer mapping not set. Configure layer mapping first.")

    result = recognize_devices(
        geometries=layout_data.get("geometries", []),
        layer_mapping=mapping_data["mappings"],
    )

    storage.save_json(project_id, "devices.json", result)
    return result


@router.get("/{project_id}/devices")
def list_devices(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    devices_data = storage.load_json(project_id, "devices.json")
    if not devices_data:
        return {"devices": []}
    return {"devices": devices_data.get("devices", [])}


@router.get("/{project_id}/devices/{device_id}")
def get_device(project_id: str, device_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    devices_data = storage.load_json(project_id, "devices.json")
    if not devices_data:
        raise HTTPException(404, "No devices found. Run recognition first.")

    for dev in devices_data.get("devices", []):
        if dev["id"] == device_id:
            return dev

    raise HTTPException(404, f"Device {device_id} not found")


@router.post("/{project_id}/devices/{device_id}/modify")
def modify_project_device(project_id: str, device_id: str, body: ModifyDeviceRequest):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    devices_data = storage.load_json(project_id, "devices.json")
    if not devices_data:
        raise HTTPException(404, "No devices found. Run recognition first.")

    device = None
    for dev in devices_data.get("devices", []):
        if dev["id"] == device_id:
            device = dev
            break
    if device is None:
        raise HTTPException(404, f"Device {device_id} not found")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(404, "Layout data not found.")

    try:
        modification = modify_device(
            device=device,
            layout_data=layout_data,
            new_value=body.new_value,
            mode=body.mode,
            manual_params=body.manual_params,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    # Store modification previews
    mods_data = storage.load_json(project_id, "modifications.json") or {"modifications": []}
    mods_data["modifications"].append(modification)
    storage.save_json(project_id, "modifications.json", mods_data)

    return modification


@router.post("/{project_id}/apply-modifications")
def apply_project_modifications(project_id: str, body: ApplyModificationsRequest):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(404, "Layout data not found.")

    mods_data = storage.load_json(project_id, "modifications.json")
    if not mods_data:
        raise HTTPException(404, "No modifications found.")

    # Filter to requested modification IDs
    requested_ids = set(body.modifications)
    selected_mods = [
        m for m in mods_data.get("modifications", [])
        if m["id"] in requested_ids
    ]
    if not selected_mods:
        raise HTTPException(400, "None of the specified modifications were found.")

    # Store original layout for diff
    storage.save_json(project_id, "layout_data_original.json", layout_data)

    # Apply modifications
    modified_layout = apply_modifications(layout_data, selected_mods)
    storage.save_json(project_id, "layout_data.json", modified_layout)

    # Write modified file
    file_type = info.get("file_type", "gds")
    project_dir = storage.get_project_dir(project_id)
    output_path = project_dir / f"modified.{file_type}"
    write_layout(modified_layout, str(output_path), file_type)

    return {
        "status": "applied",
        "modifications_applied": len(selected_mods),
        "download_url": f"/api/projects/{project_id}/download",
    }


@router.get("/{project_id}/diff")
def get_project_diff(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    original = storage.load_json(project_id, "layout_data_original.json")
    if not original:
        raise HTTPException(404, "No original layout data found. Apply modifications first.")

    current = storage.load_json(project_id, "layout_data.json")
    if not current:
        raise HTTPException(404, "Layout data not found.")

    changes = compute_diff(
        original.get("geometries", []),
        current.get("geometries", []),
    )

    return {"changes": changes}


@router.get("/{project_id}/download")
def download_project(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    file_type = info.get("file_type", "gds")
    project_dir = storage.get_project_dir(project_id)

    # Prefer modified file, fall back to original
    modified_file = project_dir / f"modified.{file_type}"
    original_file = project_dir / f"original.{file_type}"

    if modified_file.exists():
        target = modified_file
    elif original_file.exists():
        target = original_file
    else:
        raise HTTPException(404, "No layout file found.")

    media_type = "application/octet-stream"
    filename = f"{info.get('name', 'layout')}"
    if not filename.endswith(f".{file_type}"):
        filename = f"layout.{file_type}"

    return FileResponse(
        path=str(target),
        media_type=media_type,
        filename=filename,
    )


# ---- DRC endpoints ----

class DrcRulesRequest(BaseModel):
    rules: list[dict] | None = None
    rule_file: str | None = None  # base64-encoded JSON rule file


@router.post("/{project_id}/drc/rules")
def save_drc_rules(project_id: str, body: DrcRulesRequest):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    all_rules: list[dict] = []

    # From direct rules list
    if body.rules:
        all_rules.extend(body.rules)

    # From base64-encoded rule file
    if body.rule_file:
        try:
            decoded = base64.b64decode(body.rule_file).decode("utf-8")
            file_rules = parse_rule_file(decoded)
            all_rules.extend(file_rules)
        except Exception as e:
            raise HTTPException(400, f"Failed to parse rule file: {e}")

    if not all_rules:
        raise HTTPException(400, "No rules provided")

    # Validate
    for r in all_rules:
        err = validate_rule(r)
        if err:
            raise HTTPException(400, err)

    parsed = parse_rules(all_rules)
    storage.save_json(project_id, "drc_rules.json", {"rules": parsed})
    return {"rules": parsed}


@router.get("/{project_id}/drc/rules")
def get_drc_rules(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    data = storage.load_json(project_id, "drc_rules.json")
    if not data:
        return {"rules": []}
    return data


@router.post("/{project_id}/drc/run")
def run_project_drc(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    layout_data = storage.load_json(project_id, "layout_data.json")
    if not layout_data:
        raise HTTPException(404, "Layout data not found. Upload a file first.")

    mapping_data = storage.load_json(project_id, "layer_mapping.json")
    if not mapping_data or not mapping_data.get("mappings"):
        raise HTTPException(400, "Layer mapping not set. Configure layer mapping first.")

    rules_data = storage.load_json(project_id, "drc_rules.json")
    if not rules_data or not rules_data.get("rules"):
        raise HTTPException(400, "No DRC rules defined. Save rules first.")

    violations = run_drc(
        layout_data=layout_data,
        rules=rules_data["rules"],
        layer_mapping=mapping_data["mappings"],
    )

    errors = sum(1 for v in violations if v["severity"] == "error")
    warnings = sum(1 for v in violations if v["severity"] == "warning")

    result = {
        "violations": violations,
        "summary": {
            "total": len(violations),
            "errors": errors,
            "warnings": warnings,
        },
        "passed": len(violations) == 0,
    }

    storage.save_json(project_id, "drc_results.json", result)
    return result


@router.get("/{project_id}/drc/results")
def get_drc_results(project_id: str):
    info = storage.get_project(project_id)
    if not info:
        raise HTTPException(404, "Project not found")

    data = storage.load_json(project_id, "drc_results.json")
    if not data:
        raise HTTPException(404, "No DRC results found. Run DRC first.")
    return data

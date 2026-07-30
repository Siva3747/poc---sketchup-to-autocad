import os
import json
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.models.database import get_db, Project
from backend.api.schemas import FloorPlanSchema, ProjectResponse, CorrectionsRequest
from backend.services.project_service import ProjectService
from backend.utils.config import settings
from backend.utils.logger import logger
from backend.parser.ruby_exporter import RUBY_EXPORTER_SCRIPT
from backend.parser.skp_parser import parse_skp_file
from backend.geometry.detector import detect_architectural_elements
from backend.json_builder.builder import validate_and_format_json
from backend.dxf_generator.generator import generate_dxf_file
from backend.dwg_converter.converter import convert_dxf_to_dwg
from backend.parser.convert_floorplan_to_skpjson import convert_floorplan_dict
from backend.ai.detector import run_ai_detection, apply_user_corrections
from backend.exporters.skp_exporter import generate_skp_ruby_script

router = APIRouter()

SUPPORTED_UPLOAD_EXTS = [".skp", ".json", ".dxf", ".dwg"]

# ─────────────────────────────────────────────────────────────────────────────
# Upload & Pipeline
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=Dict[str, Any])
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a .skp, .dxf, .dwg, or .json file and run the full conversion pipeline."""
    logger.info(f"Upload request: {file.filename}")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_UPLOAD_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Accepted: {', '.join(SUPPORTED_UPLOAD_EXTS)}"
        )
    try:
        content = file.file.read()
        project = ProjectService.create_project(db, file.filename, content)
        return {
            "id": project.id,
            "filename": project.filename,
            "source_format": project.source_format,
            "status": project.status,
            "error": project.error_message,
            "created_at": project.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process upload: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# Convert endpoint (explicit format conversion)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/convert", response_model=Dict[str, Any])
def convert_format(
    file: UploadFile = File(...),
    target_format: str = Query("dxf", regex="^(dxf|dwg|json|skp)$"),
    db: Session = Depends(get_db),
):
    """Upload a file and immediately get back a specific output format."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in SUPPORTED_UPLOAD_EXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported source format: {ext}")
    try:
        content = file.file.read()
        project = ProjectService.create_project(db, file.filename, content)
        if project.status == "FAILED":
            raise HTTPException(status_code=500, detail=project.error_message)
        return {
            "id": project.id,
            "filename": project.filename,
            "source_format": project.source_format,
            "target_format": target_format,
            "status": project.status,
            "download_url": f"/api/v1/download/{project.id}?format={target_format}",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# AI Detection
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/detect", response_model=Dict[str, Any])
def run_detection(
    project_id: str,
    threshold: float = Query(0.80, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    """Run (or re-run) AI detection on a project's canonical JSON."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.json_path or not os.path.exists(project.json_path):
        raise HTTPException(status_code=400, detail="Canonical JSON not yet available.")
    try:
        with open(project.json_path, "r", encoding="utf-8") as f:
            canonical = json.load(f)
        enhanced = run_ai_detection(canonical, threshold=threshold)
        ai_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}_ai.json")
        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(enhanced, f, indent=2)
        project.ai_json_path = ai_path
        db.commit()
        return enhanced
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/correct", response_model=Dict[str, Any])
def apply_corrections(payload: CorrectionsRequest, db: Session = Depends(get_db)):
    """Apply user accept/reject/reclassify corrections to AI detections."""
    project = db.query(Project).filter(Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if not project.ai_json_path or not os.path.exists(project.ai_json_path):
        raise HTTPException(status_code=400, detail="AI JSON not available.")
    try:
        with open(project.ai_json_path, "r", encoding="utf-8") as f:
            enhanced = json.load(f)
        corrections = [c.model_dump() for c in payload.corrections]
        updated = apply_user_corrections(enhanced, corrections)
        with open(project.ai_json_path, "w", encoding="utf-8") as f:
            json.dump(updated, f, indent=2)
        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Viewer (GET canonical / AI JSON, PUT to save edits)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/viewer/{project_id}", response_model=Dict[str, Any])
def get_viewer_data(project_id: str, db: Session = Depends(get_db)):
    """Get canonical + AI-enhanced JSON for the browser viewer."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.status == "FAILED":
        raise HTTPException(status_code=400, detail=f"Project failed: {project.error_message}")
    if not project.json_path or not os.path.exists(project.json_path):
        try:
            ProjectService.process_pipeline(db, project)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    try:
        with open(project.json_path, "r", encoding="utf-8") as f:
            floorplan = json.load(f)
        ai_data = None
        if project.ai_json_path and os.path.exists(project.ai_json_path):
            with open(project.ai_json_path, "r", encoding="utf-8") as f:
                ai_data = json.load(f)
        return {
            "id": project.id,
            "filename": project.filename,
            "source_format": getattr(project, "source_format", "skp"),
            "status": project.status,
            "has_dxf": bool(project.dxf_path and os.path.exists(project.dxf_path)),
            "has_dwg": bool(project.dwg_path and os.path.exists(project.dwg_path)),
            "has_skp_script": bool(project.skp_script_path and os.path.exists(project.skp_script_path)),
            "has_ai": ai_data is not None,
            "floorplan": floorplan,
            "ai_detections": ai_data.get("ai_detections", []) if ai_data else [],
            "ai_metadata": ai_data.get("ai_metadata") if ai_data else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/viewer/{project_id}", response_model=Dict[str, Any])
def update_viewer_data(project_id: str, floorplan: FloorPlanSchema, db: Session = Depends(get_db)):
    """Save browser edits, regenerate DXF/DWG/SKP script."""
    try:
        data_dict = floorplan.model_dump()
        project = ProjectService.update_project_json(db, project_id, data_dict)
        return {
            "id": project.id,
            "status": project.status,
            "has_dxf": bool(project.dxf_path and os.path.exists(project.dxf_path)),
            "has_dwg": bool(project.dwg_path and os.path.exists(project.dwg_path)),
            "has_skp_script": bool(project.skp_script_path and os.path.exists(project.skp_script_path)),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Export / Download
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/download/{project_id}")
def download_project_file(
    project_id: str,
    format: str = Query(..., regex="^(json|dxf|dwg|skp)$"),
    db: Session = Depends(get_db),
):
    """Download json | dxf | dwg | skp (Ruby script) for a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    file_path, media_type, suffix = None, "application/octet-stream", f".{format}"

    if format == "json":
        file_path = project.json_path
        media_type = "application/json"
    elif format == "dxf":
        file_path = project.dxf_path
        media_type = "image/vnd.dxf"
    elif format == "dwg":
        if project.dwg_path and os.path.exists(project.dwg_path):
            file_path = project.dwg_path
            media_type = "image/vnd.dwg"
        else:
            logger.warning("DWG not available; falling back to DXF.")
            file_path = project.dxf_path
            media_type = "image/vnd.dxf"
            suffix = ".dxf"
    elif format == "skp":
        file_path = getattr(project, "skp_script_path", None)
        media_type = "text/plain"
        suffix = ".rb"

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Format '{format}' not available for this project.")

    stem = os.path.splitext(project.filename)[0]
    return FileResponse(path=file_path, media_type=media_type, filename=f"{stem}{suffix}")


# ─────────────────────────────────────────────────────────────────────────────
# Export helpers
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/export/dxf", response_model=Dict[str, Any])
def export_dxf(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.json_path:
        raise HTTPException(status_code=404, detail="Project or canonical JSON not found.")
    with open(project.json_path) as f:
        data = json.load(f)
    dxf_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dxf")
    generate_dxf_file(data, dxf_path)
    project.dxf_path = dxf_path
    db.commit()
    return {"project_id": project_id, "dxf_generated": True}


@router.post("/export/dwg", response_model=Dict[str, Any])
def export_dwg(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.dxf_path:
        raise HTTPException(status_code=400, detail="DXF must exist before DWG export.")
    dwg_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dwg")
    try:
        convert_dxf_to_dwg(project.dxf_path, dwg_path)
        project.dwg_path = dwg_path
        db.commit()
        return {"project_id": project_id, "dwg_generated": True}
    except FileNotFoundError:
        raise HTTPException(status_code=501, detail="ODA File Converter not installed on this server.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/skp", response_model=Dict[str, Any])
def export_skp(project_id: str, db: Session = Depends(get_db)):
    """Generate a SketchUp Ruby reconstruction script from the canonical JSON."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.json_path:
        raise HTTPException(status_code=404, detail="Project or canonical JSON not found.")
    with open(project.json_path) as f:
        data = json.load(f)
    script_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.rb")
    generate_skp_ruby_script(data, script_path)
    project.skp_script_path = script_path
    db.commit()
    return {"project_id": project_id, "skp_script_generated": True}


# ─────────────────────────────────────────────────────────────────────────────
# Projects list
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/projects", response_model=List[Dict[str, Any]])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "filename": p.filename,
            "source_format": getattr(p, "source_format", "skp"),
            "status": p.status,
            "error": p.error_message,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
            "has_dxf": bool(p.dxf_path and os.path.exists(p.dxf_path)),
            "has_dwg": bool(p.dwg_path and os.path.exists(p.dwg_path)),
            "has_skp_script": bool(getattr(p, "skp_script_path", None) and os.path.exists(p.skp_script_path)),
            "has_ai": bool(getattr(p, "ai_json_path", None) and os.path.exists(p.ai_json_path)),
        })
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Misc
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sketchup-exporter", response_class=PlainTextResponse)
def get_sketchup_exporter():
    return RUBY_EXPORTER_SCRIPT


@router.post("/upload-floorplan-json", response_model=Dict[str, Any])
def upload_floorplan_json(file: UploadFile = File(...), db: Session = Depends(get_db)):
    logger.info(f"Floorplan JSON upload: {file.filename}")
    try:
        raw = file.file.read()
        payload = json.loads(raw.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON upload")
    try:
        converted = convert_floorplan_dict(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")

    import uuid as _uuid
    project_id = str(_uuid.uuid4())
    original_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.json")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(original_path, "wb") as f:
        f.write(raw)

    project = Project(id=project_id, filename=file.filename, original_file_path=original_path, status="UPLOADED")
    db.add(project)
    db.commit()

    json_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.json")
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(converted, jf, indent=2)
    project.json_path = json_path
    db.commit()

    dxf_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dxf")
    try:
        generate_dxf_file(converted, dxf_path)
        project.dxf_path = dxf_path
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DXF generation failed: {str(e)}")

    try:
        dwg_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dwg")
        convert_dxf_to_dwg(project.dxf_path, dwg_path)
        project.dwg_path = dwg_path
    except FileNotFoundError:
        project.dwg_path = None
    except Exception:
        project.dwg_path = None

    try:
        enhanced = run_ai_detection(converted)
        ai_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}_ai.json")
        with open(ai_path, "w") as f:
            json.dump(enhanced, f, indent=2)
        project.ai_json_path = ai_path
    except Exception:
        pass

    project.status = "COMPLETED"
    db.commit()
    return {"project_id": project_id, "json_path": project.json_path, "dxf_path": project.dxf_path}


# Legacy endpoints kept for backwards compat
@router.post("/parse", response_model=Dict[str, Any])
def parse_project_file(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    raw_geom = parse_skp_file(project.original_file_path)
    return {"project_id": project_id, "raw_geometry": raw_geom.get("raw_geometry", {})}


@router.post("/extract", response_model=Dict[str, Any])
def extract_elements(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    raw_geom = parse_skp_file(project.original_file_path)
    detected = detect_architectural_elements(raw_geom)
    return {"project_id": project_id, "elements": detected}


@router.post("/generate-json", response_model=Dict[str, Any])
def generate_json_schema(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.json_path or not os.path.exists(project.json_path):
        raise HTTPException(status_code=400, detail="JSON not available.")
    with open(project.json_path) as f:
        return json.load(f)


@router.post("/generate-dxf", response_model=Dict[str, Any])
def generate_dxf(project_id: str, db: Session = Depends(get_db)):
    return export_dxf(project_id, db)


@router.post("/generate-dwg", response_model=Dict[str, Any])
def generate_dwg(project_id: str, db: Session = Depends(get_db)):
    return export_dwg(project_id, db)

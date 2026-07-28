import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from backend.models.database import get_db, Project
from backend.api.schemas import FloorPlanSchema, ProjectResponse
from backend.services.project_service import ProjectService
from backend.utils.config import settings
from backend.utils.logger import logger
from backend.parser.ruby_exporter import RUBY_EXPORTER_SCRIPT
from backend.parser.skp_parser import parse_skp_file
from backend.geometry.detector import detect_architectural_elements
from backend.json_builder.builder import validate_and_format_json
from backend.dxf_generator.generator import generate_dxf_file
from backend.dwg_converter.converter import convert_dxf_to_dwg

router = APIRouter()

@router.post("/upload", response_model=Dict[str, Any])
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    POST /upload
    Accepts .skp or .json file uploads, saves them, and initiates a Project conversion.
    """
    logger.info(f"Received file upload request: {file.filename}")
    
    # Validation
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".skp", ".json"]:
        raise HTTPException(status_code=400, detail="Only .skp and .json files are supported.")
        
    try:
        content = file.file.read()
        project = ProjectService.create_project(db, file.filename, content)
        
        return {
            "id": project.id,
            "filename": project.filename,
            "status": project.status,
            "error": project.error_message,
            "created_at": project.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file upload: {str(e)}")

@router.post("/parse", response_model=Dict[str, Any])
def parse_project_file(project_id: str, db: Session = Depends(get_db)):
    """
    POST /parse
    Extracts raw geometry (faces, edges, instances) from the uploaded file of a project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    try:
        raw_geom = parse_skp_file(project.original_file_path)
        return {"project_id": project_id, "raw_geometry": raw_geom.get("raw_geometry", {})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse file: {str(e)}")

@router.post("/extract", response_model=Dict[str, Any])
def extract_elements(project_id: str, db: Session = Depends(get_db)):
    """
    POST /extract
    Executes geometric algorithms to group lines and faces into walls, doors, windows, and rooms.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    try:
        raw_geom = parse_skp_file(project.original_file_path)
        detected_elements = detect_architectural_elements(raw_geom)
        return {"project_id": project_id, "elements": detected_elements}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to extract elements: {str(e)}")

@router.post("/generate-json", response_model=FloorPlanSchema)
def generate_json_schema(project_id: str, db: Session = Depends(get_db)):
    """
    POST /generate-json
    Validates and outputs the final clean JSON representation of the floor plan.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    if not project.json_path or not os.path.exists(project.json_path):
        raise HTTPException(status_code=400, detail="Floor plan JSON has not been generated for this project.")
        
    try:
        with open(project.json_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load floor plan JSON: {str(e)}")

@router.post("/generate-dxf", response_model=Dict[str, Any])
def generate_dxf(project_id: str, db: Session = Depends(get_db)):
    """
    POST /generate-dxf
    Creates/Regenerates the CAD DXF drawing from the project's current JSON model.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    if not project.json_path or not os.path.exists(project.json_path):
        raise HTTPException(status_code=400, detail="Floor plan JSON is missing. Cannot generate DXF.")
        
    try:
        with open(project.json_path, "r", encoding="utf-8") as f:
            import json
            data = json.load(f)
            
        dxf_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dxf")
        generate_dxf_file(data, dxf_path)
        
        project.dxf_path = dxf_path
        db.commit()
        
        return {"project_id": project_id, "dxf_generated": True, "path": dxf_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DXF: {str(e)}")

@router.post("/generate-dwg", response_model=Dict[str, Any])
def generate_dwg(project_id: str, db: Session = Depends(get_db)):
    """
    POST /generate-dwg
    Converts the project's current DXF file into a DWG file.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    if not project.dxf_path or not os.path.exists(project.dxf_path):
        raise HTTPException(status_code=400, detail="DXF file is missing. Please generate DXF first.")
        
    try:
        dwg_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dwg")
        convert_dxf_to_dwg(project.dxf_path, dwg_path)
        
        project.dwg_path = dwg_path
        db.commit()
        
        return {"project_id": project_id, "dwg_generated": True, "path": dwg_path}
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=501, detail="DWG converter tool is not configured on this server.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate DWG: {str(e)}")

@router.get("/viewer/{project_id}", response_model=Dict[str, Any])
def get_viewer_data(project_id: str, db: Session = Depends(get_db)):
    """
    GET /viewer/{id}
    Retrieves the complete structured JSON model of the floor plan to populate the browser 2D viewer.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    # Check if conversion has completed or is in progress
    if project.status == "FAILED":
        return {
            "id": project.id,
            "filename": project.filename,
            "status": project.status,
            "error": project.error_message,
            "floorplan": None
        }
        
    if not project.json_path or not os.path.exists(project.json_path):
        # Trigger processing if somehow missing
        try:
            ProjectService.process_pipeline(db, project)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")
            
    try:
        with open(project.json_path, "r", encoding="utf-8") as f:
            import json
            floorplan_data = json.load(f)
            
        return {
            "id": project.id,
            "filename": project.filename,
            "status": project.status,
            "has_dxf": project.dxf_path is not None and os.path.exists(project.dxf_path),
            "has_dwg": project.dwg_path is not None and os.path.exists(project.dwg_path),
            "floorplan": floorplan_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project data: {str(e)}")

@router.put("/viewer/{project_id}", response_model=Dict[str, Any])
def update_viewer_data(project_id: str, floorplan: FloorPlanSchema, db: Session = Depends(get_db)):
    """
    PUT /viewer/{id}
    Updates the floor plan JSON model (after browser modifications) and regenerates the CAD deliverables.
    """
    try:
        # Convert schema to dict
        data_dict = floorplan.model_dump()
        project = ProjectService.update_project_json(db, project_id, data_dict)
        
        return {
            "id": project.id,
            "status": project.status,
            "has_dxf": project.dxf_path is not None and os.path.exists(project.dxf_path),
            "has_dwg": project.dwg_path is not None and os.path.exists(project.dwg_path)
        }
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update floor plan: {str(e)}")

@router.get("/download/{project_id}")
def download_project_file(project_id: str, format: str = Query(..., regex="^(json|dxf|dwg)$"), db: Session = Depends(get_db)):
    """
    GET /download/{id}?format=json|dxf|dwg
    Downloads the corresponding output file for the project.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    file_path = None
    media_type = "application/octet-stream"
    filename_suffix = ""
    
    if format == "json":
        file_path = project.json_path
        media_type = "application/json"
        filename_suffix = ".json"
    elif format == "dxf":
        file_path = project.dxf_path
        media_type = "image/vnd.dxf"
        filename_suffix = ".dxf"
    elif format == "dwg":
        if project.dwg_path and os.path.exists(project.dwg_path):
            file_path = project.dwg_path
            media_type = "image/vnd.dwg"
            filename_suffix = ".dwg"
        else:
            logger.warning(f"DWG file not found for project {project_id}. Falling back to DXF deliverable.")
            file_path = project.dxf_path
            media_type = "image/vnd.dxf"
            filename_suffix = ".dxf"
        
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Requested format '{format}' is not available for this project.")
        
    download_name = f"{os.path.splitext(project.filename)[0]}{filename_suffix}"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=download_name
    )

@router.get("/sketchup-exporter", response_class=PlainTextResponse)
def get_sketchup_exporter_ruby_script():
    """
    GET /sketchup-exporter
    Downloads the SketchUp Ruby script extension that users can run inside SketchUp to export JSON directly.
    """
    return RUBY_EXPORTER_SCRIPT

@router.get("/projects", response_model=List[Dict[str, Any]])
def list_projects(db: Session = Depends(get_db)):
    """
    Lists all conversion projects in the system.
    """
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "filename": p.filename,
            "status": p.status,
            "error": p.error_message,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
            "has_dxf": p.dxf_path is not None and os.path.exists(p.dxf_path),
            "has_dwg": p.dwg_path is not None and os.path.exists(p.dwg_path)
        })
    return result

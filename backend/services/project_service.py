import os
import uuid
import datetime
from sqlalchemy.orm import Session
from backend.models.database import Project
from backend.utils.config import settings
from backend.utils.logger import logger
from backend.parser.skp_parser import parse_skp_file
from backend.geometry.detector import detect_architectural_elements
from backend.json_builder.builder import validate_and_format_json
from backend.dxf_generator.generator import generate_dxf_file
from backend.dwg_converter.converter import convert_dxf_to_dwg

class ProjectService:
    @staticmethod
    def create_project(db: Session, filename: str, file_content: bytes) -> Project:
        """
        Creates a new project record, saves the uploaded file, and starts the conversion pipeline.
        """
        project_id = str(uuid.uuid4())
        logger.info(f"Creating project {project_id} for file: {filename}")
        
        # Save original file
        file_ext = os.path.splitext(filename)[1].lower()
        original_filename = f"{project_id}{file_ext}"
        original_path = os.path.join(settings.UPLOAD_DIR, original_filename)
        
        with open(original_path, "wb") as f:
            f.write(file_content)
            
        # Create DB project
        project = Project(
            id=project_id,
            filename=filename,
            original_file_path=original_path,
            status="UPLOADED"
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Run conversion pipeline
        ProjectService.process_pipeline(db, project)
        
        return project

    @staticmethod
    def process_pipeline(db: Session, project: Project):
        """
        Runs the full conversion pipeline synchronously.
        UPLOADED -> PARSING -> EXTRACTING -> COMPLETED
        Handles failures gracefully and records logs.
        """
        project_id = project.id
        try:
            # 1. Parse File
            project.status = "PARSING"
            db.commit()
            
            raw_geom = parse_skp_file(project.original_file_path)
            
            # 2. Geometry Extraction & Element Detection
            project.status = "EXTRACTING"
            db.commit()
            
            floorplan_data = detect_architectural_elements(raw_geom)
            
            # Normalize and validate JSON
            floorplan_data = validate_and_format_json(floorplan_data)
            
            # Save structured JSON
            json_filename = f"{project_id}.json"
            json_path = os.path.join(settings.UPLOAD_DIR, json_filename)
            with open(json_path, "w", encoding="utf-8") as f:
                import json
                json.dump(floorplan_data, f, indent=2)
                
            project.json_path = json_path
            
            # 3. Generate DXF
            dxf_filename = f"{project_id}.dxf"
            dxf_path = os.path.join(settings.UPLOAD_DIR, dxf_filename)
            generate_dxf_file(floorplan_data, dxf_path)
            project.dxf_path = dxf_path
            
            # 4. Generate DWG
            dwg_filename = f"{project_id}.dwg"
            dwg_path = os.path.join(settings.UPLOAD_DIR, dwg_filename)
            try:
                convert_dxf_to_dwg(dxf_path, dwg_path)
                project.dwg_path = dwg_path
            except Exception as dwg_err:
                logger.warning(f"DWG conversion skipped or failed for project {project_id}: {dwg_err}")
                # We do not crash the pipeline if ODA is not installed
                project.dwg_path = None
                
            project.status = "COMPLETED"
            project.error_message = None
            db.commit()
            logger.info(f"Project {project_id} conversion completed successfully!")
            
        except Exception as e:
            logger.error(f"Error processing conversion pipeline for project {project_id}: {e}", exc_info=True)
            project.status = "FAILED"
            project.error_message = str(e)
            db.commit()

    @staticmethod
    def update_project_json(db: Session, project_id: str, floorplan_data: Dict[str, Any]) -> Project:
        """
        Updates a project's JSON model (from frontend edits) and regenerates the CAD DXF & DWG drawings.
        """
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Project not found.")
            
        logger.info(f"Updating floorplan JSON for project: {project_id}")
        
        # Validate data
        floorplan_data = validate_and_format_json(floorplan_data)
        
        # Save JSON
        json_path = project.json_path
        if not json_path:
            json_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.json")
            project.json_path = json_path
            
        with open(json_path, "w", encoding="utf-8") as f:
            import json
            json.dump(floorplan_data, f, indent=2)
            
        # Regenerate DXF
        dxf_path = project.dxf_path
        if not dxf_path:
            dxf_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dxf")
            project.dxf_path = dxf_path
        generate_dxf_file(floorplan_data, dxf_path)
        
        # Regenerate DWG
        dwg_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dwg")
        try:
            convert_dxf_to_dwg(dxf_path, dwg_path)
            project.dwg_path = dwg_path
        except Exception as dwg_err:
            logger.warning(f"DWG regeneration failed for project {project_id}: {dwg_err}")
            # If ODA Converter fails or is missing, keep the DWG path empty
            project.dwg_path = None
            
        project.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(project)
        
        return project

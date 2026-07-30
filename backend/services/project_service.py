import os
import uuid
import datetime
import json
from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.models.database import Project
from backend.utils.config import settings
from backend.utils.logger import logger
from backend.parser.skp_parser import parse_skp_file
from backend.geometry.detector import detect_architectural_elements
from backend.json_builder.builder import validate_and_format_json
from backend.dxf_generator.generator import generate_dxf_file
from backend.dwg_converter.converter import convert_dxf_to_dwg
from backend.ai.detector import run_ai_detection
from backend.exporters.skp_exporter import generate_skp_ruby_script


def _detect_source_format(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    return {"skp": "skp", ".skp": "skp", ".dxf": "dxf", ".dwg": "dwg", ".json": "json"}.get(ext, "skp")


class ProjectService:
    @staticmethod
    def create_project(db: Session, filename: str, file_content: bytes) -> Project:
        project_id = str(uuid.uuid4())
        logger.info(f"Creating project {project_id} for file: {filename}")

        file_ext = os.path.splitext(filename)[1].lower()
        original_filename = f"{project_id}{file_ext}"
        original_path = os.path.join(settings.UPLOAD_DIR, original_filename)
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        with open(original_path, "wb") as f:
            f.write(file_content)

        source_fmt = _detect_source_format(filename)
        project = Project(
            id=project_id,
            filename=filename,
            source_format=source_fmt,
            original_file_path=original_path,
            status="UPLOADED",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

        ProjectService.process_pipeline(db, project)
        return project

    @staticmethod
    def process_pipeline(db: Session, project: Project):
        pid = project.id
        try:
            # ── 1. Parse ──────────────────────────────────────────────────
            project.status = "PARSING"
            db.commit()

            src_fmt = getattr(project, "source_format", None) or _detect_source_format(project.filename)

            if src_fmt == "dxf":
                from backend.parsers.dxf_parser import parse_dxf_file
                raw_geom = parse_dxf_file(project.original_file_path)
            elif src_fmt == "dwg":
                # DWG → convert to DXF first if ODA available, else treat as opaque
                try:
                    tmp_dxf = os.path.join(settings.UPLOAD_DIR, f"{pid}_input.dxf")
                    convert_dxf_to_dwg(project.original_file_path, tmp_dxf)  # reverse flags
                    from backend.parsers.dxf_parser import parse_dxf_file
                    raw_geom = parse_dxf_file(tmp_dxf)
                except Exception:
                    logger.warning("DWG→DXF conversion not available; falling back to mock.")
                    raw_geom = parse_skp_file(project.original_file_path)
            else:
                raw_geom = parse_skp_file(project.original_file_path)

            # ── 2. Element detection ──────────────────────────────────────
            project.status = "EXTRACTING"
            db.commit()

            floorplan_data = detect_architectural_elements(raw_geom)
            floorplan_data = validate_and_format_json(floorplan_data)

            json_path = os.path.join(settings.UPLOAD_DIR, f"{pid}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(floorplan_data, f, indent=2)
            project.json_path = json_path

            # ── 3. AI Detection ───────────────────────────────────────────
            project.status = "DETECTING"
            db.commit()

            enhanced = run_ai_detection(floorplan_data)
            ai_path = os.path.join(settings.UPLOAD_DIR, f"{pid}_ai.json")
            with open(ai_path, "w", encoding="utf-8") as f:
                json.dump(enhanced, f, indent=2)
            project.ai_json_path = ai_path

            # ── 4. DXF ────────────────────────────────────────────────────
            dxf_path = os.path.join(settings.UPLOAD_DIR, f"{pid}.dxf")
            generate_dxf_file(floorplan_data, dxf_path)
            project.dxf_path = dxf_path

            # ── 5. DWG ────────────────────────────────────────────────────
            dwg_path = os.path.join(settings.UPLOAD_DIR, f"{pid}.dwg")
            try:
                convert_dxf_to_dwg(dxf_path, dwg_path)
                project.dwg_path = dwg_path
            except Exception as e:
                logger.warning(f"DWG conversion skipped: {e}")
                project.dwg_path = None

            # ── 6. SKP Ruby Script ────────────────────────────────────────
            skp_script_path = os.path.join(settings.UPLOAD_DIR, f"{pid}.rb")
            generate_skp_ruby_script(floorplan_data, skp_script_path)
            project.skp_script_path = skp_script_path

            project.status = "COMPLETED"
            project.error_message = None
            db.commit()
            logger.info(f"Project {pid} pipeline complete.")

        except Exception as e:
            logger.error(f"Pipeline error for {pid}: {e}", exc_info=True)
            project.status = "FAILED"
            project.error_message = str(e)
            db.commit()

    @staticmethod
    def update_project_json(db: Session, project_id: str, floorplan_data: Dict[str, Any]) -> Project:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Project not found.")

        floorplan_data = validate_and_format_json(floorplan_data)

        json_path = project.json_path or os.path.join(settings.UPLOAD_DIR, f"{project_id}.json")
        project.json_path = json_path
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(floorplan_data, f, indent=2)

        # Re-run AI
        enhanced = run_ai_detection(floorplan_data)
        ai_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}_ai.json")
        with open(ai_path, "w", encoding="utf-8") as f:
            json.dump(enhanced, f, indent=2)
        project.ai_json_path = ai_path

        dxf_path = project.dxf_path or os.path.join(settings.UPLOAD_DIR, f"{project_id}.dxf")
        project.dxf_path = dxf_path
        generate_dxf_file(floorplan_data, dxf_path)

        dwg_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.dwg")
        try:
            convert_dxf_to_dwg(dxf_path, dwg_path)
            project.dwg_path = dwg_path
        except Exception as e:
            logger.warning(f"DWG regen failed: {e}")
            project.dwg_path = None

        skp_path = os.path.join(settings.UPLOAD_DIR, f"{project_id}.rb")
        generate_skp_ruby_script(floorplan_data, skp_path)
        project.skp_script_path = skp_path

        project.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(project)
        return project

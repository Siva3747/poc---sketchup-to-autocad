import uuid
from typing import Dict, Any, List
from backend.geometry.processor import (
    project_faces_to_2d_segments,
    merge_colinear_segments,
    detect_rooms_from_walls
)
from backend.utils.logger import logger

def detect_architectural_elements(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes raw geometry to extract walls, doors, windows, and rooms.
    - If the input already contains these arrays populated (as in our structured exports),
      we return them directly (with minor validation/refining).
    - Otherwise, we execute geometric rules to segment them.
    """
    # 1. If it's already a completed structural layout, just pass it through
    if raw_data.get("walls") and len(raw_data["walls"]) > 0:
        logger.info("Structured elements already exist in uploaded data. Skipping detection.")
        
        # If rooms are missing, generate them automatically based on the walls!
        if not raw_data.get("rooms") or len(raw_data["rooms"]) == 0:
            logger.info("Rooms missing in structured payload. Running auto-detection...")
            raw_data["rooms"] = detect_rooms_from_walls(raw_data["walls"])
            
        return {
            "metadata": raw_data.get("metadata", {"unit": "mm", "scale": 1.0}),
            "walls": raw_data["walls"],
            "doors": raw_data.get("doors", []),
            "windows": raw_data.get("windows", []),
            "rooms": raw_data["rooms"]
        }
        
    logger.info("Raw geometry found. Running element detection heuristics...")
    
    raw_geom = raw_data.get("raw_geometry", {})
    faces = raw_geom.get("faces", [])
    edges = raw_geom.get("edges", [])
    instances = raw_geom.get("instances", [])
    
    walls = []
    doors = []
    windows = []
    
    # 2. Extract Walls from Faces or Edges
    # Project faces to 2D segments
    segments = project_faces_to_2d_segments(faces)
    
    # If no faces but edges exist, we can use edges as segments
    if not segments and edges:
        for e in edges:
            start = e.get("start", {})
            end = e.get("end", {})
            # Ignore vertical lines in Z
            if abs(start.get("x", 0) - end.get("x", 0)) > 10 or abs(start.get("y", 0) - end.get("y", 0)) > 10:
                segments.append(((start["x"], start["y"]), (end["x"], end["y"])))
                
    # Merge overlapping/colinear segments to form wall centerlines
    wall_lines = merge_colinear_segments(segments, tolerance=150.0)
    
    for i, line in enumerate(wall_lines):
        start_pt, end_pt = line[0], line[1]
        walls.append({
            "id": f"w_{uuid.uuid4().hex[:6]}",
            "start": {"x": round(start_pt[0], 1), "y": round(start_pt[1], 1)},
            "end": {"x": round(end_pt[0], 1), "y": round(end_pt[1], 1)},
            "thickness": 200, # default thickness
            "height": 2800,   # default height
            "layer": "Walls"
        })
        
    # 3. Extract Doors & Windows from instances
    # If SketchUp component instances were exported with classification
    for inst in instances:
        inst_type = inst.get("type")
        center = inst.get("center", {"x": 0, "y": 0})
        width = inst.get("width", 900)
        
        # Find the closest wall to snap the component to
        closest_wall_id = None
        min_dist = float("inf")
        snap_pos_ratio = 0.5
        
        for w in walls:
            # Simple distance to line segment calculation
            x1, y1 = w["start"]["x"], w["start"]["y"]
            x2, y2 = w["end"]["x"], w["end"]["y"]
            px, py = center["x"], center["y"]
            
            dx, dy = x2 - x1, y2 - y1
            line_len_sq = dx*dx + dy*dy
            if line_len_sq < 1e-3:
                continue
                
            # Project point onto segment
            t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / line_len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            
            dist = ((px - proj_x)**2 + (py - proj_y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_wall_id = w["id"]
                snap_pos_ratio = float(t)
                
        # If it snaps to a wall within a reasonable distance (e.g. 500mm)
        if closest_wall_id and min_dist < 500:
            if inst_type == "door":
                doors.append({
                    "id": inst.get("id", f"d_{uuid.uuid4().hex[:6]}"),
                    "wallId": closest_wall_id,
                    "position": round(snap_pos_ratio, 3),
                    "width": round(width, 1),
                    "height": round(inst.get("height", 2100), 1),
                    "hand": "left",
                    "direction": "in",
                    "layer": "Doors"
                })
            elif inst_type == "window":
                windows.append({
                    "id": inst.get("id", f"wnd_{uuid.uuid4().hex[:6]}"),
                    "wallId": closest_wall_id,
                    "position": round(snap_pos_ratio, 3),
                    "width": round(width, 1),
                    "height": round(inst.get("height", 1200), 1),
                    "elevation": round(inst.get("depth", 900), 1), # elevation from ground
                    "layer": "Windows"
                })

    # 4. Generate rooms based on the detected walls
    rooms = detect_rooms_from_walls(walls)
    
    # 5. Build output model
    detected_data = {
        "metadata": {
            "name": raw_data.get("metadata", {}).get("name", "Converted Model"),
            "unit": raw_data.get("metadata", {}).get("unit", "mm"),
            "scale": 1.0,
            "created_at": raw_data.get("metadata", {}).get("created_at", ""),
            "updated_at": raw_data.get("metadata", {}).get("updated_at", "")
        },
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "rooms": rooms
    }
    
    return detected_data

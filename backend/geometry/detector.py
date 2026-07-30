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
    # 1. If it's already a completed structural layout, return it and optionally detect missing openings.
    def detect_openings_from_wall_gaps(walls_list):
        openings_doors = []
        openings_windows = []
        # Allow smaller gaps to be classified as doors for floorplans that omit door components.
        min_door = 300.0  # mm
        max_door = 1400.0
        min_window = 1400.0
        max_window = 5000.0

        def vec(a, b):
            return (b[0]-a[0], b[1]-a[1])

        def length(v):
            return (v[0]*v[0] + v[1]*v[1])**0.5

        def dot(u, v):
            return u[0]*v[0] + u[1]*v[1]

        for i, wi in enumerate(walls_list):
            x1, y1 = wi["start"]["x"], wi["start"]["y"]
            x2, y2 = wi["end"]["x"], wi["end"]["y"]
            ui = vec((x1, y1), (x2, y2))
            len_ui = length(ui)
            if len_ui < 1e-3:
                continue
            ui_norm = (ui[0]/len_ui, ui[1]/len_ui)

            for j, wj in enumerate(walls_list):
                if i >= j:
                    continue
                x3, y3 = wj["start"]["x"], wj["start"]["y"]
                x4, y4 = wj["end"]["x"], wj["end"]["y"]
                uj = vec((x3, y3), (x4, y4))
                len_uj = length(uj)
                if len_uj < 1e-3:
                    continue
                uj_norm = (uj[0]/len_uj, uj[1]/len_uj)

                cosang = abs(dot(ui_norm, uj_norm))
                if cosang < 0.995:
                    continue

                def proj_t(px, py):
                    return dot((px - x1, py - y1), ui_norm)

                t_i0 = 0.0
                t_i1 = len_ui
                t_j0 = proj_t(x3, y3)
                t_j1 = proj_t(x4, y4)
                a0, a1 = min(t_i0, t_i1), max(t_i0, t_i1)
                b0, b1 = min(t_j0, t_j1), max(t_j0, t_j1)

                if b1 < a0:
                    gap = a0 - b1
                    gap_center_t = (a0 + b1) / 2.0
                elif a1 < b0:
                    gap = b0 - a1
                    gap_center_t = (a1 + b0) / 2.0
                else:
                    continue

                gx = x1 + ui_norm[0] * gap_center_t
                gy = y1 + ui_norm[1] * gap_center_t
                s = dot((gx - x3, gy - y3), uj_norm)
                projx = x3 + uj_norm[0] * s
                projy = y3 + uj_norm[1] * s
                perp_dist = ((gx - projx)**2 + (gy - projy)**2)**0.5

                if perp_dist > 200.0:
                    continue

                if min_door <= gap <= max_door:
                    openings_doors.append((gx, gy, gap))
                elif min_window <= gap <= max_window:
                    openings_windows.append((gx, gy, gap))

        return openings_doors, openings_windows

    if raw_data.get("walls") and len(raw_data["walls"]) > 0:
        logger.info("Structured elements already exist in uploaded data. Skipping full detection.")

        if not raw_data.get("rooms") or len(raw_data["rooms"]) == 0:
            logger.info("Rooms missing in structured payload. Running auto-detection...")
            raw_data["rooms"] = detect_rooms_from_walls(raw_data["walls"])

        doors = raw_data.get("doors")
        if doors is None:
            doors = []
            raw_data["doors"] = doors
        windows = raw_data.get("windows")
        if windows is None:
            windows = []
            raw_data["windows"] = windows
        if not doors or not windows:
            gap_doors, gap_windows = detect_openings_from_wall_gaps(raw_data["walls"])
            for gx, gy, gap in gap_doors:
                closest_wall = None
                min_dist = float("inf")
                snap_t = 0.5
                for w in raw_data["walls"]:
                    x1, y1 = w["start"]["x"], w["start"]["y"]
                    x2, y2 = w["end"]["x"], w["end"]["y"]
                    dx, dy = x2 - x1, y2 - y1
                    line_len_sq = dx*dx + dy*dy
                    if line_len_sq < 1e-6:
                        continue
                    t = max(0.0, min(1.0, ((gx - x1) * dx + (gy - y1) * dy) / line_len_sq))
                    proj_x = x1 + t * dx
                    proj_y = y1 + t * dy
                    dist = ((gx - proj_x)**2 + (gy - proj_y)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_wall = w["id"]
                        snap_t = t
                doors.append({
                    "id": f"d_gap_{uuid.uuid4().hex[:6]}",
                    "wallId": closest_wall,
                    "position": round(snap_t, 3),
                    "width": round(gap, 1),
                    "height": 2100,
                    "hand": "left",
                    "direction": "in",
                    "layer": "Doors"
                })
            for gx, gy, gap in gap_windows:
                closest_wall = None
                min_dist = float("inf")
                snap_t = 0.5
                for w in raw_data["walls"]:
                    x1, y1 = w["start"]["x"], w["start"]["y"]
                    x2, y2 = w["end"]["x"], w["end"]["y"]
                    dx, dy = x2 - x1, y2 - y1
                    line_len_sq = dx*dx + dy*dy
                    if line_len_sq < 1e-6:
                        continue
                    t = max(0.0, min(1.0, ((gx - x1) * dx + (gy - y1) * dy) / line_len_sq))
                    proj_x = x1 + t * dx
                    proj_y = y1 + t * dy
                    dist = ((gx - proj_x)**2 + (gy - proj_y)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        closest_wall = w["id"]
                        snap_t = t
                windows.append({
                    "id": f"win_gap_{uuid.uuid4().hex[:6]}",
                    "wallId": closest_wall,
                    "position": round(snap_t, 3),
                    "width": round(gap, 1),
                    "height": 1200,
                    "elevation": 900,
                    "layer": "Windows"
                })
        return {
            "metadata": raw_data.get("metadata", {"unit": "mm", "scale": 1.0}),
            "walls": raw_data["walls"],
            "doors": doors,
            "windows": windows,
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

    # 5. Heuristic: detect openings (doors/windows) by finding small gaps between colinear wall segments
    # This helps when input floorplans omit explicit door/window items.
    def detect_openings_from_wall_gaps(walls_list):
        openings_doors = []
        openings_windows = []
        # Allow smaller door gaps to be detected from raw wall geometry.
        min_door = 300.0  # mm
        max_door = 1400.0
        min_window = 1400.0
        max_window = 5000.0

        # Helper: vector utilities
        def vec(a, b):
            return (b[0]-a[0], b[1]-a[1])

        def length(v):
            return (v[0]*v[0] + v[1]*v[1])**0.5

        def dot(u, v):
            return u[0]*v[0] + u[1]*v[1]

        # For each pair of walls, if they are colinear and nearly on the same line, detect gap
        for i, wi in enumerate(walls_list):
            x1, y1 = wi["start"]["x"], wi["start"]["y"]
            x2, y2 = wi["end"]["x"], wi["end"]["y"]
            ui = vec((x1, y1), (x2, y2))
            len_ui = length(ui)
            if len_ui < 1e-3:
                continue
            ui_norm = (ui[0]/len_ui, ui[1]/len_ui)

            for j, wj in enumerate(walls_list):
                if i >= j:
                    continue
                x3, y3 = wj["start"]["x"], wj["start"]["y"]
                x4, y4 = wj["end"]["x"], wj["end"]["y"]
                uj = vec((x3, y3), (x4, y4))
                len_uj = length(uj)
                if len_uj < 1e-3:
                    continue
                uj_norm = (uj[0]/len_uj, uj[1]/len_uj)

                # Check colinearity (direction cosine near 1 or -1)
                cosang = abs(dot(ui_norm, uj_norm))
                if cosang < 0.995:  # not colinear enough
                    continue

                # Project endpoints onto the shared axis (use wi axis)
                # Use origin at (x1,y1)
                def proj_t(px, py):
                    return dot((px - x1, py - y1), ui_norm)

                t_i0 = 0.0
                t_i1 = len_ui
                t_j0 = proj_t(x3, y3)
                t_j1 = proj_t(x4, y4)
                # Normalize ordering
                a0, a1 = min(t_i0, t_i1), max(t_i0, t_i1)
                b0, b1 = min(t_j0, t_j1), max(t_j0, t_j1)

                # Check distance between intervals
                if b1 < a0:
                    gap = a0 - b1
                    gap_center_t = (a0 + b1) / 2.0
                elif a1 < b0:
                    gap = b0 - a1
                    gap_center_t = (a1 + b0) / 2.0
                else:
                    # intervals overlap or touch -> no opening
                    continue

                # Perpendicular offset between the two lines (approx)
                # compute distance from one segment midpoint to the other line
                # pick midpoint of gap on wi axis
                gx = x1 + ui_norm[0] * gap_center_t
                gy = y1 + ui_norm[1] * gap_center_t
                # perpendicular distance to wj line
                # line wj in param form p = (x3,y3) + s * uj_norm
                # find s that minimizes distance
                s = dot((gx - x3, gy - y3), uj_norm)
                projx = x3 + uj_norm[0] * s
                projy = y3 + uj_norm[1] * s
                perp_dist = ((gx - projx)**2 + (gy - projy)**2)**0.5

                if perp_dist > 200.0:
                    # too far apart (not same wall line)
                    continue

                # Classify as door or window based on gap length
                if min_door <= gap <= max_door:
                    openings_doors.append((gx, gy, gap))
                elif min_window <= gap <= max_window:
                    openings_windows.append((gx, gy, gap))

        return openings_doors, openings_windows

    gap_doors, gap_windows = detect_openings_from_wall_gaps(walls)
    for idx, (gx, gy, gap) in enumerate(gap_doors):
        # snap to nearest wall id and compute position ratio
        closest_wall = None
        min_dist = float('inf')
        snap_t = 0.5
        for w in walls:
            x1, y1 = w['start']['x'], w['start']['y']
            x2, y2 = w['end']['x'], w['end']['y']
            dx, dy = x2 - x1, y2 - y1
            line_len_sq = dx*dx + dy*dy
            if line_len_sq < 1e-6:
                continue
            t = max(0.0, min(1.0, ((gx - x1) * dx + (gy - y1) * dy) / line_len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = ((gx - proj_x)**2 + (gy - proj_y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_wall = w['id']
                snap_t = t

        doors.append({
            'id': f'd_gap_{uuid.uuid4().hex[:6]}',
            'wallId': closest_wall,
            'position': round(snap_t, 3),
            'width': round(gap, 1),
            'height': 2100,
            'hand': 'left',
            'direction': 'in',
            'layer': 'Doors'
        })

    for idx, (gx, gy, gap) in enumerate(gap_windows):
        closest_wall = None
        min_dist = float('inf')
        snap_t = 0.5
        for w in walls:
            x1, y1 = w['start']['x'], w['start']['y']
            x2, y2 = w['end']['x'], w['end']['y']
            dx, dy = x2 - x1, y2 - y1
            line_len_sq = dx*dx + dy*dy
            if line_len_sq < 1e-6:
                continue
            t = max(0.0, min(1.0, ((gx - x1) * dx + (gy - y1) * dy) / line_len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = ((gx - proj_x)**2 + (gy - proj_y)**2)**0.5
            if dist < min_dist:
                min_dist = dist
                closest_wall = w['id']
                snap_t = t

        windows.append({
            'id': f'win_gap_{uuid.uuid4().hex[:6]}',
            'wallId': closest_wall,
            'position': round(snap_t, 3),
            'width': round(gap, 1),
            'height': 1200,
            'elevation': 900,
            'layer': 'Windows'
        })

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

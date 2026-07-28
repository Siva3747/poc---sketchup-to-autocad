import numpy as np
from typing import List, Dict, Any, Tuple
from shapely.geometry import LineString, Polygon, MultiPolygon
from shapely.ops import unary_union, polygonize
from backend.utils.logger import logger

def project_faces_to_2d_segments(faces: List[Dict[str, Any]]) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Filters vertical faces (whose normal vector has Z close to 0)
    and projects their bottom edges to 2D line segments on the XY plane.
    """
    segments = []
    for face in faces:
        normal = face.get("normal", {"x": 0, "y": 0, "z": 1})
        # If normal Z component is close to 0, the face is vertical (a wall surface)
        if abs(normal.get("z", 1.0)) < 0.1:
            vertices = face.get("vertices", [])
            if len(vertices) < 3:
                continue
                
            # Find the bottom vertices (minimum Z) or project all edges to 2D segments
            # For each edge in the face, project to XY
            for i in range(len(vertices)):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % len(vertices)]
                
                # Filter out vertical lines (x1 == x2 and y1 == y2)
                if abs(p1["x"] - p2["x"]) < 1e-2 and abs(p1["y"] - p2["y"]) < 1e-2:
                    continue
                    
                segments.append(((p1["x"], p1["y"]), (p2["x"], p2["y"])))
                
    logger.info(f"Projected {len(faces)} faces into {len(segments)} 2D segments.")
    return segments

def merge_colinear_segments(segments: List[Tuple[Tuple[float, float], Tuple[float, float]]], tolerance: float = 50.0) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Merges segments that are colinear and overlapping/close to each other within tolerance (in mm).
    """
    if not segments:
        return []
        
    merged = []
    used = [False] * len(segments)
    
    for i, seg1 in enumerate(segments):
        if used[i]:
            continue
            
        p1, p2 = np.array(seg1[0]), np.array(seg1[1])
        v1 = p2 - p1
        len1 = np.linalg.norm(v1)
        if len1 < 1e-3:
            continue
        u1 = v1 / len1
        
        # Start with seg1 bounds
        min_proj = 0.0
        max_proj = len1
        line_p = p1
        line_u = u1
        
        colinears = [i]
        used[i] = True
        
        for j, seg2 in enumerate(segments):
            if used[j]:
                continue
                
            q1, q2 = np.array(seg2[0]), np.array(seg2[1])
            
            # Check projection and distance from line
            # Distance from line_p along line_u
            proj1 = np.dot(q1 - line_p, line_u)
            proj2 = np.dot(q2 - line_p, line_u)
            
            # Perpendicular distance
            perp1 = np.linalg.norm((q1 - line_p) - proj1 * line_u)
            perp2 = np.linalg.norm((q2 - line_p) - proj2 * line_u)
            
            if perp1 < tolerance and perp2 < tolerance:
                # Check if it overlaps or is close to our current segment range
                proj_min = min(proj1, proj2)
                proj_max = max(proj1, proj2)
                
                # Check for overlap or small gap
                if proj_min <= max_proj + tolerance and proj_max >= min_proj - tolerance:
                    min_proj = min(min_proj, proj_min)
                    max_proj = max(max_proj, proj_max)
                    colinears.append(j)
                    used[j] = True
                    
        # Reconstruct the merged segment
        start_pt = line_p + min_proj * line_u
        end_pt = line_p + max_proj * line_u
        merged.append(((float(start_pt[0]), float(start_pt[1])), (float(end_pt[0]), float(end_pt[1]))))
        
    logger.info(f"Merged {len(segments)} segments down to {len(merged)} segments.")
    return merged

def detect_rooms_from_walls(walls: List[Dict[str, Any]], floorplan_width: float = 12000.0, floorplan_height: float = 10000.0) -> List[Dict[str, Any]]:
    """
    Given a list of walls, detects enclosed rooms using Shapely's polygonize operations.
    1. Draw wall centerlines.
    2. Buffer centerlines to form polygons, or use them to segment the floor area.
    3. Generate room polygon boundaries.
    """
    if not walls:
        return []
        
    # Represent walls as LineStrings
    lines = []
    for w in walls:
        start = w["start"]
        end = w["end"]
        lines.append(LineString([(start["x"], start["y"]), (end["x"], end["y"])]))
        
    # We create a bounding boundary polygon representing the outer frame of the house
    # We expand the walls bounding box slightly to define the envelope
    min_x, min_y, max_x, max_y = 0.0, 0.0, 10.0, 10.0
    all_points = []
    for w in walls:
        all_points.extend([(w["start"]["x"], w["start"]["y"]), (w["end"]["x"], w["end"]["y"])])
        
    if all_points:
        arr = np.array(all_points)
        min_x = float(arr[:, 0].min()) - 100
        min_y = float(arr[:, 1].min()) - 100
        max_x = float(arr[:, 0].max()) + 100
        max_y = float(arr[:, 1].max()) + 100
        
    envelope = Polygon([(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)])
    
    # We buffer each line to represent the physical wall boundaries
    wall_polys = []
    for w, line in zip(walls, lines):
        # Buffer by half thickness
        thickness = w.get("thickness", 200)
        wall_polys.append(line.buffer(thickness / 2.0, cap_style=3)) # cap_style=3 is square
        
    # Union of all wall polygons
    walls_union = unary_union(wall_polys)
    
    # Subtract walls from the envelope to get interior spaces
    interior_spaces = envelope.difference(walls_union)
    
    rooms_detected = []
    room_counter = 1
    
    # Iterate through individual polygon elements in interior_spaces
    if isinstance(interior_spaces, Polygon):
        polys = [interior_spaces]
    elif isinstance(interior_spaces, MultiPolygon):
        polys = list(interior_spaces.geoms)
    else:
        polys = []
        
    for poly in polys:
        # Exclude the outer boundary space (the one containing the boundary points of our envelope)
        # If a polygon touches the edge of the envelope, it's outside the house!
        bounds = poly.bounds
        if bounds[0] <= min_x + 10 or bounds[1] <= min_y + 10 or bounds[2] >= max_x - 10 or bounds[3] >= max_y - 10:
            continue
            
        # Simplify the room polygon coordinates
        poly_coords = list(poly.exterior.coords)[:-1] # Remove repeated closing point
        points = [{"x": float(x), "y": float(y)} for x, y in poly_coords]
        
        # Calculate area in square meters (mm^2 to m^2, divide by 1,000,000)
        area = float(poly.area) / 1000000.0
        
        if area > 1.0: # filter out tiny speck polygons
            rooms_detected.append({
                "id": f"room_{room_counter}",
                "name": f"Room {room_counter}",
                "points": points,
                "area": round(area, 2),
                "layer": "Rooms"
            })
            room_counter += 1
            
    logger.info(f"Automatically detected {len(rooms_detected)} rooms.")
    return rooms_detected

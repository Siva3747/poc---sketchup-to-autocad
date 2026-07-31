import json
import os
import random
import datetime
import math
from typing import Dict, Any, List
from backend.utils.logger import logger

try:
    from openskp import SkpFile
    OPENSKP_AVAILABLE = True
except ImportError:
    OPENSKP_AVAILABLE = False
    logger.warning("openskp library not installed. Parsing of physical SketchUp binary files will fall back to mock generation.")

def check_is_skp_header(file_path: str) -> bool:
    """
    Checks if the file starts with the SketchUp model header.
    SketchUp binary headers usually contain 'SketchUp' or start with custom bytes.
    """
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, "rb") as f:
            header = f.read(100)
            # Normal SKP files start with 'SketchUp Model' or similar strings in the first 100 bytes
            return b"SketchUp" in header or b"ActiveModel" in header or header.startswith(b"\xff\xfe")
    except Exception as e:
        logger.error(f"Error checking file header: {e}")
        return False

def parse_skp_file(file_path: str) -> Dict[str, Any]:
    """
    Main entry point for parsing SketchUp files.
    - If it's a JSON file (exported by our Ruby script), we load it directly.
    - If it's a binary SKP, we try openskp.
    - Binary models are converted into real plan-view geometry for detection.
    """
    logger.info(f"Attempting to parse file: {file_path}")
    
    # Check if the file is already a JSON (e.g. exported from SketchUp Ruby Plugin or workspace floorplan)
    if file_path.lower().endswith(".json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "raw_geometry" in data or "walls" in data:
                    logger.info("Successfully loaded pre-exported SketchUp JSON model.")
                    return data
                elif "layers" in data:
                    logger.info("Detected workspace-format floorplan JSON. Converting to internal schema...")
                    from backend.parser.convert_floorplan_to_skpjson import convert_floorplan_dict
                    converted = convert_floorplan_dict(data)
                    return converted
        except Exception as e:
            logger.error(f"Failed to read JSON file: {e}")
            raise ValueError(f"Invalid JSON file format: {e}")

    # Check for binary SketchUp file signature
    is_skp = check_is_skp_header(file_path)
    if not is_skp and file_path.lower().endswith(".skp"):
        logger.warning("File extension is .skp but header check did not find 'SketchUp' signature.")
    
    # 1. Attempt binary parsing if openskp is available
    if OPENSKP_AVAILABLE and is_skp:
        try:
            logger.info("Parsing SketchUp binary file using openskp library...")
            model = SkpFile.open(file_path).parse()

            # openskp exposes geometry through model definitions, not the
            # SkpFile wrapper. Keep long, horizontal edges: they represent
            # the plan-view outlines while excluding vertical wall edges and
            # tiny construction details that overwhelm the detector.
            candidate_edges = []
            for definition in model.definitions.values():
                for edge in definition.edges.values():
                    start = definition.vertices.get(edge.v1_id)
                    end = definition.vertices.get(edge.v2_id)
                    if not start or not end or abs(start.z - end.z) > 0.01:
                        continue
                    length_mm = math.hypot(end.x - start.x, end.y - start.y) * 25.4
                    if length_mm >= 100:
                        candidate_edges.append((length_mm, start, end, definition.name))

            candidate_edges.sort(key=lambda item: item[0], reverse=True)
            edges = []
            for i, (_, start, end, layer) in enumerate(candidate_edges[:800]):
                edges.append({
                    "id": f"edge_{i}",
                    "layer": layer or "Layer0",
                    "start": {"x": start.x * 25.4, "y": start.y * 25.4, "z": start.z * 25.4},
                    "end": {"x": end.x * 25.4, "y": end.y * 25.4, "z": end.z * 25.4},
                })

            if not edges:
                raise ValueError("No usable plan-view edges were found in this SketchUp model.")
                
            # Compile exported data
            export_data = {
                "metadata": {
                    "name": os.path.basename(file_path),
                    "unit": "mm",
                    "scale": 1.0,
                    "created_at": "N/A",
                    "updated_at": "N/A"
                },
                "walls": [],
                "doors": [],
                "windows": [],
                "rooms": [],
                "raw_geometry": {
                    "faces": [],
                    "edges": edges,
                    "instances": [],
                }
            }
            logger.info(f"openskp parse complete. Extracted {len(edges)} plan-view edges.")
            return export_data
            
        except Exception as e:
            logger.error(f"openskp failed to parse the file: {e}")
            raise ValueError(
                "This SketchUp model version cannot be read directly. "
                "In SketchUp, run the supplied SketchUp JSON exporter and upload the exported JSON file."
            ) from e
            
    raise ValueError(
        "This SketchUp file cannot be parsed directly. Export it with the supplied "
        "SketchUp JSON exporter and upload the resulting JSON file."
    )

def generate_mock_floorplan(filename: str) -> Dict[str, Any]:
    """
    Generates a highly-detailed, beautiful, and valid mock architectural 2D floor plan JSON.
    This enables full visualization, editing, and CAD exports out-of-the-box.
    Deterministic based on the hash of the filename to provide unique plans for different files.
    """
    import random
    import hashlib
    
    # Generate seed from filename
    h = hashlib.md5(filename.encode("utf-8")).hexdigest()
    seed = int(h, 16) % (2**32)
    rng = random.Random(seed)
    
    # Determine classification: residential vs commercial/office
    lower_name = filename.lower()
    is_office = any(k in lower_name for k in ["office", "work", "commercial", "corp", "hq", "business", "meeting", "lab"])
    
    # Select layout style: 0 (Studio), 1 (3-Room), 2 (4-Room Layout)
    style = rng.choice([0, 1, 2])
    
    walls = []
    doors = []
    windows = []
    rooms = []
    raw_faces = []
    
    if style == 0:
        # Style 0: Studio / Simple Office Space
        # Width: 7m to 9m, Height: 5m to 7m
        W = rng.randint(7000, 9000)
        H = rng.randint(5000, 7000)
        
        # Division line: vertical divider at X = W * 0.65
        div_x = int(W * 0.65)
        
        # Define walls
        wall_segments = [
            {"id": "w_outer_top", "start": {"x": 0, "y": 0}, "end": {"x": W, "y": 0}, "thickness": 250},
            {"id": "w_outer_right", "start": {"x": W, "y": 0}, "end": {"x": W, "y": H}, "thickness": 250},
            {"id": "w_outer_bottom", "start": {"x": W, "y": H}, "end": {"x": 0, "y": H}, "thickness": 250},
            {"id": "w_outer_left", "start": {"x": 0, "y": H}, "end": {"x": 0, "y": 0}, "thickness": 250},
            {"id": "w_div_vertical", "start": {"x": div_x, "y": 0}, "end": {"x": div_x, "y": H}, "thickness": 150}
        ]
        
        for ws in wall_segments:
            walls.append({
                "id": ws["id"],
                "start": ws["start"],
                "end": ws["end"],
                "thickness": ws["thickness"],
                "height": 2800,
                "layer": "Walls"
            })
            
        # Place doors
        doors.extend([
            {
                "id": "d_main",
                "wallId": "w_outer_bottom",
                "position": 0.25,
                "width": 900,
                "height": 2100,
                "hand": "left",
                "direction": "in",
                "layer": "Doors"
            },
            {
                "id": "d_bathroom",
                "wallId": "w_div_vertical",
                "position": 0.5,
                "width": 800,
                "height": 2100,
                "hand": "right",
                "direction": "in",
                "layer": "Doors"
            }
        ])
        
        # Place windows
        windows.extend([
            {
                "id": "win_main",
                "wallId": "w_outer_top",
                "position": 0.3,
                "width": 1500,
                "height": 1200,
                "elevation": 900,
                "layer": "Windows"
            },
            {
                "id": "win_bath",
                "wallId": "w_outer_right",
                "position": 0.5,
                "width": 600,
                "height": 600,
                "elevation": 1500,
                "layer": "Windows"
            }
        ])
        
        # Room names
        r1_name = "Work Space" if is_office else "Living Space"
        r2_name = "Restroom" if is_office else "Bathroom"
        
        rooms.extend([
            {
                "id": "room_main",
                "name": r1_name,
                "points": [
                    {"x": 0, "y": 0},
                    {"x": div_x, "y": 0},
                    {"x": div_x, "y": H},
                    {"x": 0, "y": H}
                ],
                "area": round((div_x * H) / 1000000.0, 1),
                "layer": "Rooms"
            },
            {
                "id": "room_bath",
                "name": r2_name,
                "points": [
                    {"x": div_x, "y": 0},
                    {"x": W, "y": 0},
                    {"x": W, "y": H},
                    {"x": div_x, "y": H}
                ],
                "area": round(((W - div_x) * H) / 1000000.0, 1),
                "layer": "Rooms"
            }
        ])
        
    elif style == 1:
        # Style 1: 3-Room Apartment / Commercial suite
        # Width: 9m to 12m, Height: 7m to 9m
        W = rng.randint(9000, 12000)
        H = rng.randint(7000, 9000)
        
        div_x = int(W * 0.6)
        div_y = int(H * 0.5)
        
        wall_segments = [
            {"id": "w_outer_top", "start": {"x": 0, "y": 0}, "end": {"x": W, "y": 0}, "thickness": 250},
            {"id": "w_outer_right", "start": {"x": W, "y": 0}, "end": {"x": W, "y": H}, "thickness": 250},
            {"id": "w_outer_bottom", "start": {"x": W, "y": H}, "end": {"x": 0, "y": H}, "thickness": 250},
            {"id": "w_outer_left", "start": {"x": 0, "y": H}, "end": {"x": 0, "y": 0}, "thickness": 250},
            {"id": "w_div_vertical", "start": {"x": div_x, "y": 0}, "end": {"x": div_x, "y": H}, "thickness": 150},
            {"id": "w_div_horizontal", "start": {"x": div_x, "y": div_y}, "end": {"x": W, "y": div_y}, "thickness": 150}
        ]
        
        for ws in wall_segments:
            walls.append({
                "id": ws["id"],
                "start": ws["start"],
                "end": ws["end"],
                "thickness": ws["thickness"],
                "height": 2800,
                "layer": "Walls"
            })
            
        doors.extend([
            {
                "id": "d_main",
                "wallId": "w_outer_bottom",
                "position": 0.25,
                "width": 900,
                "height": 2100,
                "hand": "left",
                "direction": "in",
                "layer": "Doors"
            },
            {
                "id": "d_room_top",
                "wallId": "w_div_vertical",
                "position": 0.25,
                "width": 850,
                "height": 2100,
                "hand": "left",
                "direction": "in",
                "layer": "Doors"
            },
            {
                "id": "d_room_bottom",
                "wallId": "w_div_vertical",
                "position": 0.75,
                "width": 800,
                "height": 2100,
                "hand": "right",
                "direction": "in",
                "layer": "Doors"
            }
        ])
        
        windows.extend([
            {
                "id": "win_living",
                "wallId": "w_outer_left",
                "position": 0.5,
                "width": 1500,
                "height": 1200,
                "elevation": 900,
                "layer": "Windows"
            },
            {
                "id": "win_top",
                "wallId": "w_outer_top",
                "position": 0.8,
                "width": 1200,
                "height": 1200,
                "elevation": 900,
                "layer": "Windows"
            },
            {
                "id": "win_bottom",
                "wallId": "w_outer_right",
                "position": 0.75,
                "width": 600,
                "height": 600,
                "elevation": 1500,
                "layer": "Windows"
            }
        ])
        
        # Room names
        r1_name = "Reception / Lobby" if is_office else "Living Room"
        r2_name = "Office Suite" if is_office else "Bedroom"
        r3_name = "Conference Room" if is_office else "Kitchen"
        
        rooms.extend([
            {
                "id": "room_1",
                "name": r1_name,
                "points": [
                    {"x": 0, "y": 0},
                    {"x": div_x, "y": 0},
                    {"x": div_x, "y": H},
                    {"x": 0, "y": H}
                ],
                "area": round((div_x * H) / 1000000.0, 1),
                "layer": "Rooms"
            },
            {
                "id": "room_2",
                "name": r2_name,
                "points": [
                    {"x": div_x, "y": 0},
                    {"x": W, "y": 0},
                    {"x": W, "y": div_y},
                    {"x": div_x, "y": div_y}
                ],
                "area": round(((W - div_x) * div_y) / 1000000.0, 1),
                "layer": "Rooms"
            },
            {
                "id": "room_3",
                "name": r3_name,
                "points": [
                    {"x": div_x, "y": div_y},
                    {"x": W, "y": div_y},
                    {"x": W, "y": H},
                    {"x": div_x, "y": H}
                ],
                "area": round(((W - div_x) * (H - div_y)) / 1000000.0, 1),
                "layer": "Rooms"
            }
        ])
        
    else:
        # Style 2: 4-Room Layout (similar to original, but randomized dimensions)
        # Width: 10m to 14m, Height: 8m to 11m
        W = rng.randint(10000, 14000)
        H = rng.randint(8000, 11000)
        
        div_x = int(W * rng.uniform(0.55, 0.65))
        div_y_left = int(H * rng.uniform(0.5, 0.6))
        div_y_right = int(H * rng.uniform(0.45, 0.55))
        
        wall_segments = [
            {"id": "w_outer_top", "start": {"x": 0, "y": 0}, "end": {"x": W, "y": 0}, "thickness": 250},
            {"id": "w_outer_right", "start": {"x": W, "y": 0}, "end": {"x": W, "y": H}, "thickness": 250},
            {"id": "w_outer_bottom", "start": {"x": W, "y": H}, "end": {"x": 0, "y": H}, "thickness": 250},
            {"id": "w_outer_left", "start": {"x": 0, "y": H}, "end": {"x": 0, "y": 0}, "thickness": 250},
            {"id": "w_div_vertical", "start": {"x": div_x, "y": 0}, "end": {"x": div_x, "y": H}, "thickness": 150},
            {"id": "w_div_horiz_left", "start": {"x": 0, "y": div_y_left}, "end": {"x": div_x, "y": div_y_left}, "thickness": 150},
            {"id": "w_div_horiz_right", "start": {"x": div_x, "y": div_y_right}, "end": {"x": W, "y": div_y_right}, "thickness": 150}
        ]
        
        for ws in wall_segments:
            walls.append({
                "id": ws["id"],
                "start": ws["start"],
                "end": ws["end"],
                "thickness": ws["thickness"],
                "height": 2800,
                "layer": "Walls"
            })
            
        doors.extend([
            {
                "id": "d_main",
                "wallId": "w_outer_bottom",
                "position": 0.25,
                "width": 900,
                "height": 2100,
                "hand": "left",
                "direction": "in",
                "layer": "Doors"
            },
            {
                "id": "d_bedroom",
                "wallId": "w_div_horiz_left",
                "position": 0.3,
                "width": 850,
                "height": 2100,
                "hand": "left",
                "direction": "in",
                "layer": "Doors"
            },
            {
                "id": "d_bathroom",
                "wallId": "w_div_horiz_right",
                "position": 0.4,
                "width": 750,
                "height": 2100,
                "hand": "right",
                "direction": "in",
                "layer": "Doors"
            },
            {
                "id": "d_kitchen",
                "wallId": "w_div_vertical",
                "position": 0.3,
                "width": 1000,
                "height": 2100,
                "hand": "left",
                "direction": "in",
                "layer": "Doors"
            }
        ])
        
        windows.extend([
            {
                "id": "win_living",
                "wallId": "w_outer_top",
                "position": 0.3,
                "width": 1500,
                "height": 1200,
                "elevation": 900,
                "layer": "Windows"
            },
            {
                "id": "win_bedroom",
                "wallId": "w_outer_left",
                "position": 0.8,
                "width": 1200,
                "height": 1200,
                "elevation": 900,
                "layer": "Windows"
            },
            {
                "id": "win_kitchen",
                "wallId": "w_outer_right",
                "position": 0.25,
                "width": 1200,
                "height": 1200,
                "elevation": 900,
                "layer": "Windows"
            },
            {
                "id": "win_bathroom",
                "wallId": "w_outer_right",
                "position": 0.8,
                "width": 600,
                "height": 600,
                "elevation": 1500,
                "layer": "Windows"
            }
        ])
        
        # Room names
        r1_name = "Main Office" if is_office else "Living Room"
        r2_name = "Conference Room" if is_office else "Bedroom"
        r3_name = "Pantry / Breakroom" if is_office else "Kitchen"
        r4_name = "Restroom" if is_office else "Bathroom"
        
        rooms.extend([
            {
                "id": "room_living",
                "name": r1_name,
                "points": [
                    {"x": 0, "y": 0},
                    {"x": div_x, "y": 0},
                    {"x": div_x, "y": div_y_left},
                    {"x": 0, "y": div_y_left}
                ],
                "area": round((div_x * div_y_left) / 1000000.0, 1),
                "layer": "Rooms"
            },
            {
                "id": "room_bedroom",
                "name": r2_name,
                "points": [
                    {"x": 0, "y": div_y_left},
                    {"x": div_x, "y": div_y_left},
                    {"x": div_x, "y": H},
                    {"x": 0, "y": H}
                ],
                "area": round((div_x * (H - div_y_left)) / 1000000.0, 1),
                "layer": "Rooms"
            },
            {
                "id": "room_kitchen",
                "name": r3_name,
                "points": [
                    {"x": div_x, "y": 0},
                    {"x": W, "y": 0},
                    {"x": W, "y": div_y_right},
                    {"x": div_x, "y": div_y_right}
                ],
                "area": round(((W - div_x) * div_y_right) / 1000000.0, 1),
                "layer": "Rooms"
            },
            {
                "id": "room_bathroom",
                "name": r4_name,
                "points": [
                    {"x": div_x, "y": div_y_right},
                    {"x": W, "y": div_y_right},
                    {"x": W, "y": H},
                    {"x": div_x, "y": H}
                ],
                "area": round(((W - div_x) * (H - div_y_right)) / 1000000.0, 1),
                "layer": "Rooms"
            }
        ])
        
    # Generate raw faces to simulate openskp parser output
    raw_faces.append({
        "id": "f_wall_1",
        "layer": "Walls",
        "normal": {"x": 0, "y": 1, "z": 0},
        "vertices": [
            {"x": 0, "y": 0, "z": 0},
            {"x": W, "y": 0, "z": 0},
            {"x": W, "y": 0, "z": 2800},
            {"x": 0, "y": 0, "z": 2800}
        ]
    })
    
    import datetime
    return {
        "metadata": {
            "name": filename,
            "unit": "mm",
            "scale": 1.0,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
        },
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "rooms": rooms,
        "raw_geometry": {
            "faces": raw_faces,
            "edges": [],
            "instances": []
        }
    }

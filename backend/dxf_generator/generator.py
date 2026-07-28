import os
import math
import ezdxf
from ezdxf.enums import TextEntityAlignment
from typing import Dict, Any, List, Tuple
from backend.utils.logger import logger

def generate_dxf_file(floorplan_data: Dict[str, Any], output_path: str) -> str:
    """
    Generates a professional 2D CAD DXF file from the structured floorplan JSON.
    Uses ezdxf to construct layers, geometry, and annotations.
    """
    logger.info(f"Generating DXF file at: {output_path}")
    
    # Create a new DXF drawing (AutoCAD 2010 format)
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    
    # Set up standard CAD layers with colors
    # Colors: 1=Red, 2=Yellow, 3=Green, 4=Cyan, 5=Blue, 6=Magenta, 7=White/Black
    layers = {
        "WALLS": {"color": 7, "lineweight": 35},      # White/Black, thick line
        "DOORS": {"color": 1, "lineweight": 18},      # Red, thin line
        "WINDOWS": {"color": 4, "lineweight": 18},    # Cyan, thin line
        "ROOMS_TEXT": {"color": 2, "lineweight": 15}, # Yellow, text
        "DIMENSIONS": {"color": 3, "lineweight": 9},  # Green, very thin line
        "CENTERLINES": {"color": 5, "lineweight": 13} # Blue, dashed centerline
    }
    
    for layer_name, attribs in layers.items():
        doc.layers.new(
            name=layer_name, 
            dxfattribs={"color": attribs["color"], "lineweight": attribs["lineweight"]}
        )
        
    walls = floorplan_data.get("walls", [])
    doors = floorplan_data.get("doors", [])
    windows = floorplan_data.get("windows", [])
    rooms = floorplan_data.get("rooms", [])
    
    # Keep track of wall geometries for door/window snapping coordinate calculations
    wall_map = {w["id"]: w for w in walls}
    
    # 1. DRAW WALLS
    for w in walls:
        x1, y1 = w["start"]["x"], w["start"]["y"]
        x2, y2 = w["end"]["x"], w["end"]["y"]
        thickness = w.get("thickness", 200)
        
        # Draw Centerline
        msp.add_line((x1, y1), (x2, y2), dxfattribs={"layer": "CENTERLINES"})
        
        # Draw Double Lines (Wall Boundary)
        dx = x2 - x1
        dy = y2 - y1
        length = math.hypot(dx, dy)
        if length < 1e-3:
            continue
            
        # Unit direction vectors
        ux = dx / length
        uy = dy / length
        
        # Perpendicular vectors (normal to wall direction)
        nx = -uy
        ny = ux
        
        # Offset coordinates (half thickness on each side)
        half_t = thickness / 2.0
        
        p1 = (x1 + nx * half_t, y1 + ny * half_t)
        p2 = (x2 + nx * half_t, y2 + ny * half_t)
        p3 = (x2 - nx * half_t, y2 - ny * half_t)
        p4 = (x1 - nx * half_t, y1 - ny * half_t)
        
        # Add closed polyline for wall boundary
        msp.add_lwpolyline([p1, p2, p3, p4, p1], dxfattribs={"layer": "WALLS"})
        
        # Add dimensions text (optional visual polish)
        wall_len_m = length / 1000.0
        mid_x = (x1 + x2) / 2.0 + nx * (half_t + 150)
        mid_y = (y1 + y2) / 2.0 + ny * (half_t + 150)
        angle_rad = math.atan2(dy, dx)
        # Normalize angle to range [-90, 90] degrees so text is never upside down
        angle_deg = math.degrees(angle_rad)
        if angle_deg > 90:
            angle_deg -= 180
        elif angle_deg < -90:
            angle_deg += 180
            
        msp.add_text(
            text=f"{wall_len_m:.2f} m", 
            dxfattribs={
                "layer": "DIMENSIONS",
                "height": 120,
                "rotation": angle_deg
            }
        ).set_placement((mid_x, mid_y), align=TextEntityAlignment.MIDDLE_CENTER)

    # 2. DRAW DOORS
    for d in doors:
        wall_id = d.get("wallId")
        if wall_id not in wall_map:
            continue
            
        w = wall_map[wall_id]
        wx1, wy1 = w["start"]["x"], w["start"]["y"]
        wx2, wy2 = w["end"]["x"], w["end"]["y"]
        pos_ratio = d["position"]
        width = d["width"]
        
        wdx = wx2 - wx1
        wdy = wy2 - wy1
        w_len = math.hypot(wdx, wdy)
        if w_len < 1e-3:
            continue
            
        wux = wdx / w_len
        wuy = wdy / w_len
        
        # Door center along the wall path
        dcx = wx1 + pos_ratio * wdx
        dcy = wy1 + pos_ratio * wdy
        
        # Hinge and Latch positions along the wall
        # We place hinge at the start side of the opening and latch at the end side
        hx = dcx - (width / 2.0) * wux
        hy = dcy - (width / 2.0) * wuy
        
        lx = dcx + (width / 2.0) * wux
        ly = dcy + (width / 2.0) * wuy
        
        # Perpendicular direction for swing
        pnx = -wuy
        pny = wux
        
        # Swing hand and direction modifiers
        # direction: "in" or "out" (negates perpendicular vector)
        dir_mult = -1.0 if d.get("direction", "in") == "in" else 1.0
        
        # Door panel endpoint (swung open 90 degrees)
        dpx = hx + width * pnx * dir_mult
        dpy = hy + width * pny * dir_mult
        
        # Add door panel line (hinge to panel end)
        msp.add_line((hx, hy), (dpx, dpy), dxfattribs={"layer": "DOORS"})
        
        # Add door swing arc
        # ezdxf arc takes angles in degrees counterclockwise from X axis
        base_angle_rad = math.atan2(wuy, wux)
        perpendicular_angle_rad = math.atan2(pny * dir_mult, pnx * dir_mult)
        
        # We compute angles in degrees
        hinge_to_latch_angle = math.degrees(base_angle_rad)
        hinge_to_panel_angle = math.degrees(perpendicular_angle_rad)
        
        # Normalize to 0-360
        a1 = hinge_to_latch_angle % 360
        a2 = hinge_to_panel_angle % 360
        
        start_angle = min(a1, a2)
        end_angle = max(a1, a2)
        
        # Handle wraparound correctly
        if (end_angle - start_angle) > 180:
            start_angle, end_angle = end_angle, start_angle + 360
            
        msp.add_arc(
            center=(hx, hy),
            radius=width,
            start_angle=start_angle,
            end_angle=end_angle,
            dxfattribs={"layer": "DOORS"}
        )

    # 3. DRAW WINDOWS
    for win in windows:
        wall_id = win.get("wallId")
        if wall_id not in wall_map:
            continue
            
        w = wall_map[wall_id]
        wx1, wy1 = w["start"]["x"], w["start"]["y"]
        wx2, wy2 = w["end"]["x"], w["end"]["y"]
        pos_ratio = win["position"]
        width = win["width"]
        thickness = w.get("thickness", 200)
        
        wdx = wx2 - wx1
        wdy = wy2 - wy1
        w_len = math.hypot(wdx, wdy)
        if w_len < 1e-3:
            continue
            
        wux = wdx / w_len
        wuy = wdy / w_len
        
        # Window center along wall path
        wcx = wx1 + pos_ratio * wdx
        wcy = wy1 + pos_ratio * wdy
        
        # Endpoints along wall centerline
        x1_win = wcx - (width / 2.0) * wux
        y1_win = wcy - (width / 2.0) * wuy
        x2_win = wcx + (width / 2.0) * wux
        y2_win = wcy + (width / 2.0) * wuy
        
        # Perpendicular normal
        nx = -wuy
        ny = wux
        
        half_t = thickness / 2.0
        
        # Window corner points
        p1 = (x1_win + nx * half_t, y1_win + ny * half_t)
        p2 = (x2_win + nx * half_t, y2_win + ny * half_t)
        p3 = (x2_win - nx * half_t, y2_win - ny * half_t)
        p4 = (x1_win - nx * half_t, y1_win - ny * half_t)
        
        # Draw window frame outline
        msp.add_lwpolyline([p1, p2, p3, p4, p1], dxfattribs={"layer": "WINDOWS"})
        
        # Draw inner double glass lines
        gl1_start = (x1_win + nx * (half_t * 0.2), y1_win + ny * (half_t * 0.2))
        gl1_end = (x2_win + nx * (half_t * 0.2), y2_win + ny * (half_t * 0.2))
        gl2_start = (x1_win - nx * (half_t * 0.2), y1_win - ny * (half_t * 0.2))
        gl2_end = (x2_win - nx * (half_t * 0.2), y2_win - ny * (half_t * 0.2))
        
        msp.add_line(gl1_start, gl1_end, dxfattribs={"layer": "WINDOWS"})
        msp.add_line(gl2_start, gl2_end, dxfattribs={"layer": "WINDOWS"})

    # 4. DRAW ROOM NAMES & LABELS
    for r in rooms:
        name = r.get("name", "Room")
        area = r.get("area", 0.0)
        points = r.get("points", [])
        if not points:
            continue
            
        # Calculate centroid of points to place the text label
        cx = sum(p["x"] for p in points) / len(points)
        cy = sum(p["y"] for p in points) / len(points)
        
        # Label text showing room name and its area
        label = f"{name}\\P{area:.1f} m2" # \\P creates a new line in AutoCAD MTEXT
        
        # Add MText (multi-line text) for clean alignment
        mtext = msp.add_mtext(
            text=label,
            dxfattribs={
                "layer": "ROOMS_TEXT",
                "insert": (cx, cy),
                "char_height": 180,
                "attachment_point": 5, # Top center
                "line_spacing_style": 1
            }
        )
        # Shift slightly up so it's centered properly
        mtext.dxf.insert = (cx, cy + 90)

    # Make sure folder exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save the DXF file
    doc.saveas(output_path)
    return output_path

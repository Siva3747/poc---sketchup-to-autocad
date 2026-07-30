"""
SketchUp SKP Exporter
Generates a SketchUp-compatible Ruby script that reconstructs the model
when run inside SketchUp's Ruby Console.
The script approach avoids needing the SketchUp SDK on the server.
"""
import json
import os
from typing import Dict, Any
from backend.utils.logger import logger


def generate_skp_ruby_script(canonical_json: Dict[str, Any], output_path: str) -> str:
    """
    Generates a .rb Ruby script that, when executed inside SketchUp,
    reconstructs the full floor plan model from the Canonical JSON.
    Returns the path to the saved script.
    """
    logger.info(f"Generating SKP Ruby reconstruction script: {output_path}")
    walls = canonical_json.get("walls", [])
    doors = canonical_json.get("doors", [])
    windows = canonical_json.get("windows", [])
    rooms = canonical_json.get("rooms", [])
    metadata = canonical_json.get("metadata", {})
    unit = metadata.get("unit", "mm")

    # SketchUp uses inches internally; convert if needed
    if unit == "mm":
        factor = 1.0 / 25.4
    elif unit == "cm":
        factor = 1.0 / 2.54
    elif unit == "m":
        factor = 39.3701
    elif unit == "ft":
        factor = 12.0
    else:
        factor = 1.0  # assume inches

    lines = [
        "# CAD AI Converter – SketchUp Floor Plan Reconstruction Script",
        f"# Source model: {metadata.get('name', 'Unnamed')}",
        "# Run this script from SketchUp > Window > Ruby Console",
        "",
        "model = Sketchup.active_model",
        "model.start_operation('CAD AI Converter Import', true)",
        "ents = model.active_entities",
        "",
        "# Helper: draw a wall as a pushpull face",
        "def draw_wall(ents, x1, y1, x2, y2, thickness, height)",
        "  dx = x2 - x1",
        "  dy = y2 - y1",
        "  len = Math.sqrt(dx*dx + dy*dy)",
        "  return if len < 0.001",
        "  nx = -dy/len * thickness/2",
        "  ny =  dx/len * thickness/2",
        "  pts = [",
        "    Geom::Point3d.new(x1+nx, y1+ny, 0),",
        "    Geom::Point3d.new(x2+nx, y2+ny, 0),",
        "    Geom::Point3d.new(x2-nx, y2-ny, 0),",
        "    Geom::Point3d.new(x1-nx, y1-ny, 0),",
        "  ]",
        "  face = ents.add_face(pts)",
        "  face.pushpull(height) if face",
        "end",
        "",
        "# ── Walls ───────────────────────────────────────────────",
        "wall_layer = model.layers.add('Walls')",
    ]

    for w in walls:
        x1 = round(w["start"]["x"] * factor, 6)
        y1 = round(w["start"]["y"] * factor, 6)
        x2 = round(w["end"]["x"] * factor, 6)
        y2 = round(w["end"]["y"] * factor, 6)
        t = round(w.get("thickness", 200) * factor, 6)
        h = round(w.get("height", 2800) * factor, 6)
        lines.append(f"draw_wall(ents, {x1}, {y1}, {x2}, {y2}, {t}, {h})")

    lines += [
        "",
        "# ── Rooms (guide planes) ────────────────────────────────",
        "room_layer = model.layers.add('Rooms')",
    ]
    for r in rooms:
        pts = r.get("points", [])
        if len(pts) >= 3:
            pt_str = ", ".join(
                f"Geom::Point3d.new({round(p['x']*factor,6)}, {round(p['y']*factor,6)}, 0)"
                for p in pts
            )
            lines.append(f"face = ents.add_face([{pt_str}])")
            lines.append(f"face.layer = room_layer if face")

    lines += [
        "",
        "model.commit_operation",
        "puts 'CAD AI Converter: Model imported successfully!'",
    ]

    script = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)

    logger.info(f"SKP Ruby script written: {output_path}")
    return output_path

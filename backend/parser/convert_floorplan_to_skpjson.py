import json
from pathlib import Path

INPUT = Path("d:/poc3/floorplan.json")
OUTPUT = Path("d:/poc3/floorplan_converted.json")

UNIT_MAP = {
    "mm": 1.0,
    "cm": 10.0,
    # Some source data labels millimeter-based coordinates as cent,
    # so treat cent as mm when the numeric values already appear to be millimeter-scale.
    "cent": 1.0,
    "m": 1000.0,
    "in": 25.4,
    "ft": 304.8
}


def to_mm(val, unit_scale):
    return val * unit_scale


def convert_floorplan_dict(data: dict, unit_override: str = None) -> dict:
    """Convert workspace floorplan JSON (layers/areas/lines) into SketchUp-exporter-compatible schema.

    Returns the converted dict (not written to disk unless caller writes it).
    """

    unit = unit_override or data.get("unit", "mm")
    scale = UNIT_MAP.get(unit, 1.0)

    # Build vertex map (assuming single selected layer or use first layer)
    layers = data.get("layers", {})
    if not layers:
        raise SystemExit("No layers found in input JSON")

    # Choose first layer entry
    layer_id, layer = next(iter(layers.items()))

    vertices = layer.get("vertices", {})

    # Helper to resolve vertex id to coordinates
    def resolve_vid(vid):
        v = vertices.get(vid)
        if not v:
            return None
        x = to_mm(v.get("x", 0), scale)
        y = to_mm(v.get("y", 0), scale)
        return {"x": x, "y": y}

    # Convert walls from lines
    walls = []
    for lid, line in layer.get("lines", {}).items():
        verts = line.get("vertices", [])
        if len(verts) >= 2:
            a = resolve_vid(verts[0])
            b = resolve_vid(verts[1])
        else:
            # fallback to geometry rawPolygon bounding
            poly = line.get("geometry", {}).get("rawPolygon") or []
            if len(poly) >= 2:
                a = {"x": to_mm(poly[0].get("x", 0), scale), "y": to_mm(poly[0].get("y", 0), scale)}
                b = {"x": to_mm(poly[1].get("x", 0), scale), "y": to_mm(poly[1].get("y", 0), scale)}
            else:
                continue

        thickness = line.get("properties", {}).get("thickness", {}).get("length")
        height = line.get("properties", {}).get("height", {}).get("length")
        if thickness is not None:
            thickness = to_mm(thickness, scale)
        if height is not None:
            height = to_mm(height, scale)

        walls.append({
            "id": lid,
            "start": a,
            "end": b,
            "thickness": thickness,
            "height": height,
            "layer": layer.get("name", "Layer0")
        })

    # Convert rooms from areas
    rooms = []
    for aid, area in layer.get("areas", {}).items():
        geom = area.get("geometry", {})
        poly = geom.get("innerPolygon") or geom.get("outerPolygon") or []
        points = []
        for p in poly:
            points.append({"x": to_mm(p.get("x", 0), scale), "y": to_mm(p.get("y", 0), scale)})
        rooms.append({
            "id": aid,
            "name": area.get("properties", {}).get("label") or area.get("properties", {}).get("name") or aid,
            "points": points,
            "area": area.get("properties", {}).get("area") or None,
            "layer": layer.get("name", "Area")
        })

    # Raw geometry: create faces from area innerPolygon (z=0)
    faces = []
    for rid, r in layer.get("areas", {}).items():
        geom = r.get("geometry", {})
        poly = geom.get("innerPolygon") or geom.get("outerPolygon") or []
        verts = []
        for i, p in enumerate(poly):
            verts.append({"x": to_mm(p.get("x", 0), scale), "y": to_mm(p.get("y", 0), scale), "z": 0})
        faces.append({"id": f"face_{rid}", "layer": layer.get("name", "Layer0"), "vertices": verts, "normal": {"x": 0, "y": 0, "z": 1}})

    converted = {
        "metadata": {
            "name": data.get("name", "floorplan"),
            "unit": "mm",
            "scale": 1.0,
            "created_at": None,
            "updated_at": None
        },
        "walls": walls,
        "doors": [],
        "windows": [],
        "rooms": rooms,
        "raw_geometry": {
            "faces": faces,
            "edges": [],
            "instances": []
        }
    }
    # Build quick wall lookup for snapping
    wall_map = {w["id"]: w for w in walls}

    def snap_to_wall(px, py):
        """Find closest wall and return (wall_id, position_ratio) or (None, 0.5)."""
        best_id = None
        best_dist = float("inf")
        best_t = 0.5
        for w in walls:
            x1, y1 = w["start"]["x"], w["start"]["y"]
            x2, y2 = w["end"]["x"], w["end"]["y"]
            dx, dy = x2 - x1, y2 - y1
            line_len_sq = dx*dx + dy*dy
            if line_len_sq < 1e-6:
                continue
            t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / line_len_sq))
            proj_x = x1 + t * dx
            proj_y = y1 + t * dy
            dist = ((px - proj_x)**2 + (py - proj_y)**2)**0.5
            if dist < best_dist:
                best_dist = dist
                best_id = w["id"]
                best_t = t
        return best_id, best_t

    def get_wall_position_from_offset(wall, offset):
        if offset is None:
            return 0.5
        x1, y1 = wall["start"]["x"], wall["start"]["y"]
        x2, y2 = wall["end"]["x"], wall["end"]["y"]
        wall_length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        if wall_length < 1e-6:
            return 0.5
        return max(0.0, min(1.0, float(offset) / wall_length))

    # Populate doors/windows from top-level if present
    input_doors = data.get("doors") or []
    input_windows = data.get("windows") or []

    # Helper to convert numeric dims
    def conv_val(v):
        if v is None:
            return None
        try:
            return to_mm(v, scale)
        except Exception:
            return v

    for d in input_doors:
        # Convert dims
        width = conv_val(d.get("width"))
        height = conv_val(d.get("height"))

        wall_id = d.get("wallId")
        position = d.get("position")

        # If wallId missing or unknown, try snapping from center/x/y
        if not wall_id or wall_id not in wall_map:
            cx = None
            if "center" in d and isinstance(d["center"], dict):
                cx = d["center"].get("x")
                cy = d["center"].get("y")
            elif "x" in d and "y" in d:
                cx = d.get("x")
                cy = d.get("y")
            else:
                cx = None
            if cx is not None:
                wall_id, snap_pos = snap_to_wall(cx, cy)
                position = position if position is not None else snap_pos

        converted["doors"].append({
            "id": d.get("id") or f"d_{len(converted['doors'])+1}",
            "wallId": wall_id,
            "position": position if position is not None else 0.5,
            "width": width or 900,
            "height": height or 2100,
            "hand": d.get("hand", "left"),
            "direction": d.get("direction", "in"),
            "layer": d.get("layer", "Doors")
        })

    for w in input_windows:
        width = conv_val(w.get("width"))
        height = conv_val(w.get("height"))
        elevation = conv_val(w.get("elevation"))

        wall_id = w.get("wallId")
        position = w.get("position")

        if not wall_id or wall_id not in wall_map:
            cx = None
            if "center" in w and isinstance(w["center"], dict):
                cx = w["center"].get("x")
                cy = w["center"].get("y")
            elif "x" in w and "y" in w:
                cx = w.get("x")
                cy = w.get("y")
            else:
                cx = None
            if cx is not None:
                wall_id, snap_pos = snap_to_wall(cx, cy)
                position = position if position is not None else snap_pos

        converted["windows"].append({
            "id": w.get("id") or f"win_{len(converted['windows'])+1}",
            "wallId": wall_id,
            "position": position if position is not None else 0.5,
            "width": width or 1200,
            "height": height or 1500,
            "elevation": elevation or 900,
            "layer": w.get("layer", "Windows")
        })

    # Also check for layer-level items with possible door/window classifications
    layer_items = layer.get("items") if isinstance(layer.get("items"), dict) else {}
    for iid, item in layer_items.items():
        typ = item.get("type", "").lower()
        if typ in ("door", "window"):
            cx = item.get("x") or item.get("center", {}).get("x")
            cy = item.get("y") or item.get("center", {}).get("y")
            wall_id, snap_pos = (None, 0.5)
            if cx is not None:
                wall_id, snap_pos = snap_to_wall(to_mm(cx, scale), to_mm(cy, scale))
            if typ == "door":
                converted["doors"].append({
                    "id": iid,
                    "wallId": wall_id,
                    "position": snap_pos,
                    "width": conv_val(item.get("width")) or 900,
                    "height": conv_val(item.get("height")) or 2100,
                    "hand": item.get("hand", "left"),
                    "direction": item.get("direction", "in"),
                    "layer": item.get("layer", "Doors")
                })
            else:
                converted["windows"].append({
                    "id": iid,
                    "wallId": wall_id,
                    "position": snap_pos,
                    "width": conv_val(item.get("width")) or 1200,
                    "height": conv_val(item.get("height")) or 1500,
                    "elevation": conv_val(item.get("elevation")) or 900,
                    "layer": item.get("layer", "Windows")
                })

    # Convert wall holes into doors/windows if they declare type
    for lid, line in layer.get("lines", {}).items():
        if line.get("type") != "wall":
            continue
        for hole_id in line.get("holes", []):
            hole = layer.get("holes", {}).get(hole_id)
            if not hole:
                continue
            typ = hole.get("type", "").lower()
            if typ not in ("door", "window"):
                continue
            wall = wall_map.get(lid)
            if not wall:
                continue
            offset = hole.get("offset")
            position = get_wall_position_from_offset(wall, offset)
            width = conv_val(hole.get("width")) or (813 if typ == "door" else 1120)
            height = conv_val(hole.get("height")) or (2133.6 if typ == "door" else 1219.2)
            elevation = conv_val(hole.get("altitude")) if typ == "window" else None
            if typ == "door":
                converted["doors"].append({
                    "id": hole_id,
                    "wallId": lid,
                    "position": position,
                    "width": width,
                    "height": height,
                    "hand": hole.get("hand", "left"),
                    "direction": hole.get("direction", "in"),
                    "layer": hole.get("layer", "Doors")
                })
            else:
                converted["windows"].append({
                    "id": hole_id,
                    "wallId": lid,
                    "position": position,
                    "width": width,
                    "height": height,
                    "elevation": elevation or 900,
                    "layer": hole.get("layer", "Windows")
                })

    return converted


def main():
    data = json.loads(INPUT.read_text(encoding="utf-8"))
    converted = convert_floorplan_dict(data)
    OUTPUT.write_text(json.dumps(converted, indent=2), encoding="utf-8")
    print(f"Wrote converted file to: {OUTPUT}")


if __name__ == "__main__":
    main()

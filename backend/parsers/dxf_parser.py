"""
DXF / DWG Input Parser
Reads AutoCAD DXF files using ezdxf and converts geometry into Canonical JSON.
"""
import uuid
import math
from typing import Dict, Any, List, Tuple
from backend.utils.logger import logger

try:
    import ezdxf
    from ezdxf.math import Vec2
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False
    logger.warning("ezdxf not available – DXF input parsing disabled.")


def parse_dxf_file(file_path: str) -> Dict[str, Any]:
    """
    Parse a DXF file and return a raw geometry dict compatible with the
    existing geometry detector pipeline.
    """
    if not EZDXF_AVAILABLE:
        raise RuntimeError("ezdxf is required for DXF parsing")

    logger.info(f"Parsing DXF file: {file_path}")
    try:
        doc = ezdxf.readfile(file_path)
    except Exception as e:
        raise ValueError(f"Failed to read DXF file: {e}")

    msp = doc.modelspace()
    segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
    instances: List[Dict[str, Any]] = []

    for entity in msp:
        etype = entity.dxftype()

        if etype == "LINE":
            s = entity.dxf.start
            e = entity.dxf.end
            segments.append(((s.x, s.y), (e.x, e.y)))

        elif etype == "LWPOLYLINE":
            pts = list(entity.get_points())
            for i in range(len(pts) - 1):
                segments.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))
            if entity.is_closed and len(pts) >= 2:
                segments.append(((pts[-1][0], pts[-1][1]), (pts[0][0], pts[0][1])))

        elif etype == "POLYLINE":
            verts = list(entity.vertices)
            for i in range(len(verts) - 1):
                a, b = verts[i].dxf.location, verts[i+1].dxf.location
                segments.append(((a.x, a.y), (b.x, b.y)))

        elif etype == "ARC":
            # Approximate arc with line segments
            cx, cy = entity.dxf.center.x, entity.dxf.center.y
            r = entity.dxf.radius
            start_a = math.radians(entity.dxf.start_angle)
            end_a = math.radians(entity.dxf.end_angle)
            if end_a < start_a:
                end_a += 2 * math.pi
            steps = max(6, int((end_a - start_a) / math.radians(15)))
            prev = None
            for i in range(steps + 1):
                t = start_a + (end_a - start_a) * i / steps
                pt = (cx + r * math.cos(t), cy + r * math.sin(t))
                if prev is not None:
                    segments.append((prev, pt))
                prev = pt

        elif etype == "INSERT":
            # Block references — try to classify by block name
            name = entity.dxf.name.lower()
            cx = entity.dxf.insert.x
            cy = entity.dxf.insert.y
            inst_type = None
            if any(k in name for k in ["door", "dr", "deur"]):
                inst_type = "door"
            elif any(k in name for k in ["window", "win", "fen"]):
                inst_type = "window"
            if inst_type:
                instances.append({
                    "id": f"{inst_type}_{uuid.uuid4().hex[:6]}",
                    "type": inst_type,
                    "center": {"x": cx, "y": cy},
                    "width": entity.dxf.xscale * 900 if hasattr(entity.dxf, "xscale") else 900,
                    "height": entity.dxf.yscale * 2100 if hasattr(entity.dxf, "yscale") else 2100,
                })

    # Filter trivially short segments
    MIN_LEN = 10.0
    segments = [s for s in segments if math.hypot(
        s[1][0] - s[0][0], s[1][1] - s[0][1]) >= MIN_LEN]

    edges = [
        {
            "start": {"x": s[0][0], "y": s[0][1], "z": 0},
            "end":   {"x": s[1][0], "y": s[1][1], "z": 0},
        }
        for s in segments
    ]

    logger.info(f"DXF parsed: {len(edges)} edges, {len(instances)} component instances")
    return {
        "raw_geometry": {
            "faces": [],
            "edges": edges,
            "instances": instances,
        },
        "metadata": {
            "name": doc.filename or "DXF Model",
            "unit": _dxf_unit(doc),
            "scale": 1.0,
        }
    }


def _dxf_unit(doc) -> str:
    try:
        units = doc.header.get("$INSUNITS", 0)
        unit_map = {0: "unitless", 1: "in", 2: "ft", 4: "mm", 5: "cm", 6: "m"}
        return unit_map.get(units, "mm")
    except Exception:
        return "mm"

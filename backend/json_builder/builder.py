import json
import math
from typing import Dict, Any
from backend.utils.logger import logger


def _number_or_default(value: Any, default: float) -> float:
    """Return a usable finite number when exported data contains nulls."""
    if value is None:
        return default
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return default
    return numeric_value if math.isfinite(numeric_value) else default

def validate_and_format_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates the structure of the generated floorplan and sets default values
    where fields might be missing.
    """
    logger.info("Validating and formatting structured floor plan JSON...")
    
    # Ensure root arrays exist
    for key in ["walls", "doors", "windows", "rooms"]:
        if key not in data:
            data[key] = []
            
    if "metadata" not in data:
        data["metadata"] = {
            "name": "Unnamed Model",
            "unit": "mm",
            "scale": 1.0
        }
    else:
        if "unit" not in data["metadata"]:
            data["metadata"]["unit"] = "mm"
        if "scale" not in data["metadata"]:
            data["metadata"]["scale"] = 1.0
            
    # Normalize ID formats and coordinates
    for i, w in enumerate(data["walls"]):
        if "id" not in w:
            w["id"] = f"w_{i}"
        w["thickness"] = _number_or_default(w.get("thickness"), 200)
        w["height"] = _number_or_default(w.get("height"), 2800)
        w["layer"] = w.get("layer", "Walls")
        
    for i, d in enumerate(data["doors"]):
        if "id" not in d:
            d["id"] = f"d_{i}"
        d["width"] = _number_or_default(d.get("width"), 900)
        d["height"] = _number_or_default(d.get("height"), 2100)
        d["hand"] = d.get("hand", "left")
        d["direction"] = d.get("direction", "in")
        d["layer"] = d.get("layer", "Doors")
        
    for i, wnd in enumerate(data["windows"]):
        if "id" not in wnd:
            wnd["id"] = f"win_{i}"
        wnd["width"] = _number_or_default(wnd.get("width"), 1200)
        wnd["height"] = _number_or_default(wnd.get("height"), 1200)
        wnd["elevation"] = _number_or_default(wnd.get("elevation"), 900)
        wnd["layer"] = wnd.get("layer", "Windows")
        
    for i, r in enumerate(data["rooms"]):
        if "id" not in r:
            r["id"] = f"room_{i}"
        r["area"] = _number_or_default(r.get("area"), 0)
        r["layer"] = r.get("layer", "Rooms")
        
    return data

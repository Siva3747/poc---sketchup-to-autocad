"""
AI Architectural Detection Engine
Modular design: plug-and-play models (heuristic, ONNX, PyTorch, etc.)
Each detected object includes: id, type, confidence, geometry, properties
"""
import uuid
import math
from typing import Dict, Any, List, Tuple, Optional
from backend.utils.logger import logger

# Confidence threshold below which objects are classified as "Unknown"
DEFAULT_CONFIDENCE_THRESHOLD = 0.80

# ─────────────────────────────────────────────────────────────────────────────
# Feature Extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_geometric_features(canonical_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts a rich feature set from the canonical JSON for AI processing.
    Returns features: vertices, faces, edges, dimensions, bounding boxes, connectivity.
    """
    walls = canonical_json.get("walls", [])
    doors = canonical_json.get("doors", [])
    windows = canonical_json.get("windows", [])
    rooms = canonical_json.get("rooms", [])

    features = {
        "wall_count": len(walls),
        "door_count": len(doors),
        "window_count": len(windows),
        "room_count": len(rooms),
        "walls": [],
        "doors": [],
        "windows": [],
        "rooms": [],
        "connectivity_graph": {},
    }

    wall_map: Dict[str, Dict] = {}
    for w in walls:
        x1, y1 = w["start"]["x"], w["start"]["y"]
        x2, y2 = w["end"]["x"], w["end"]["y"]
        length = math.hypot(x2 - x1, y2 - y1)
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
        thickness = w.get("thickness", 200)
        height = w.get("height", 2800)
        volume = length * thickness * height

        feat = {
            "id": w["id"],
            "length": round(length, 2),
            "angle_deg": round(angle, 2),
            "thickness": thickness,
            "height": height,
            "area": round(length * height, 2),
            "volume": round(volume, 2),
            "is_horizontal": angle < 15 or angle > 165,
            "is_vertical": 75 <= angle <= 105,
            "bbox": {
                "minX": min(x1, x2) - thickness / 2,
                "minY": min(y1, y2) - thickness / 2,
                "maxX": max(x1, x2) + thickness / 2,
                "maxY": max(y1, y2) + thickness / 2,
            },
        }
        features["walls"].append(feat)
        wall_map[w["id"]] = w

    # Door features
    for d in doors:
        wall = wall_map.get(d["wallId"])
        feat = {
            "id": d["id"],
            "width": d.get("width", 900),
            "height": d.get("height", 2100),
            "position_ratio": d.get("position", 0.5),
            "wall_id": d["wallId"],
            "aspect_ratio": d.get("width", 900) / max(d.get("height", 2100), 1),
        }
        features["doors"].append(feat)

    # Window features
    for win in windows:
        feat = {
            "id": win["id"],
            "width": win.get("width", 1200),
            "height": win.get("height", 1200),
            "elevation": win.get("elevation", 900),
            "position_ratio": win.get("position", 0.5),
            "wall_id": win["wallId"],
            "aspect_ratio": win.get("width", 1200) / max(win.get("height", 1200), 1),
        }
        features["windows"].append(feat)

    # Room features
    for r in rooms:
        pts = r.get("points", [])
        feat = {
            "id": r["id"],
            "name": r.get("name", "Room"),
            "area": r.get("area", 0),
            "point_count": len(pts),
            "perimeter": _polygon_perimeter(pts),
            "compactness": _compactness(r.get("area", 0), _polygon_perimeter(pts)),
        }
        features["rooms"].append(feat)

    # Build simple adjacency / connectivity graph
    adjacency: Dict[str, List[str]] = {}
    for d in doors:
        wid = d["wallId"]
        adjacency.setdefault(wid, [])

    features["connectivity_graph"] = adjacency
    return features


def _polygon_perimeter(pts: List[Dict]) -> float:
    if len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        total += math.hypot(b["x"] - a["x"], b["y"] - a["y"])
    return round(total, 2)


def _compactness(area: float, perimeter: float) -> float:
    """4πA/P² — 1.0 for a circle, lower for complex shapes."""
    if perimeter < 1e-3:
        return 0.0
    return round(4 * math.pi * area / (perimeter ** 2), 4)


# ─────────────────────────────────────────────────────────────────────────────
# Heuristic AI Model (plug-and-play baseline)
# ─────────────────────────────────────────────────────────────────────────────

class HeuristicAIModel:
    """
    Geometry-based architectural element classifier.
    Produces confidence-scored detections compatible with the AI output schema.
    Swap this class for a PyTorch/ONNX model without changing the pipeline.
    """
    name = "heuristic-v1"

    def detect(
        self,
        canonical_json: Dict[str, Any],
        features: Dict[str, Any],
        threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> List[Dict[str, Any]]:
        detections: List[Dict[str, Any]] = []

        detections += self._classify_walls(canonical_json.get("walls", []), features["walls"], threshold)
        detections += self._classify_doors(canonical_json.get("doors", []), features["doors"], threshold)
        detections += self._classify_windows(canonical_json.get("windows", []), features["windows"], threshold)
        detections += self._classify_rooms(canonical_json.get("rooms", []), features["rooms"], threshold)

        return detections

    # ── Wall classification ──────────────────────────────────────────────────
    def _classify_walls(self, walls, wall_feats, threshold):
        results = []
        for w, f in zip(walls, wall_feats):
            confidence, label = self._wall_confidence(f)
            if confidence < threshold:
                label = "unknown"
            results.append(self._make_detection(
                obj_id=w["id"],
                obj_type=label,
                confidence=confidence,
                geometry={"start": w["start"], "end": w["end"]},
                properties={
                    "length": f["length"],
                    "height": f["height"],
                    "thickness": f["thickness"],
                    "angle_deg": f["angle_deg"],
                },
            ))
        return results

    def _wall_confidence(self, f: Dict) -> Tuple[float, str]:
        score = 0.5
        # Length heuristic: typical walls 500mm–20000mm
        if 500 <= f["length"] <= 20000:
            score += 0.2
        elif f["length"] < 200:
            score -= 0.3  # too short – likely detail line
        # Thickness heuristic
        if 100 <= f["thickness"] <= 600:
            score += 0.15
        # Orthogonality bonus
        if f["is_horizontal"] or f["is_vertical"]:
            score += 0.15
        # Large height
        if 2000 <= f["height"] <= 5000:
            score += 0.1

        label = "wall"
        if f["length"] < 200:
            label = "detail_line"
        elif f["thickness"] > 800:
            label = "slab"
        elif f["height"] < 600:
            label = "beam"

        return min(round(score, 3), 0.99), label

    # ── Door classification ──────────────────────────────────────────────────
    def _classify_doors(self, doors, door_feats, threshold):
        results = []
        for d, f in zip(doors, door_feats):
            confidence, label = self._door_confidence(f)
            if confidence < threshold:
                label = "unknown"
            results.append(self._make_detection(
                obj_id=d["id"],
                obj_type=label,
                confidence=confidence,
                geometry={"wall_id": d["wallId"], "position": d["position"]},
                properties={
                    "width": f["width"],
                    "height": f["height"],
                    "aspect_ratio": f["aspect_ratio"],
                },
            ))
        return results

    def _door_confidence(self, f: Dict) -> Tuple[float, str]:
        score = 0.6
        # Typical door width 600–1400mm
        if 600 <= f["width"] <= 1400:
            score += 0.25
        elif f["width"] > 2000:
            score -= 0.2  # likely a garage or large opening
        # Typical door height 1800–2400mm
        if 1800 <= f["height"] <= 2400:
            score += 0.15
        return min(round(score, 3), 0.99), "door"

    # ── Window classification ────────────────────────────────────────────────
    def _classify_windows(self, windows, win_feats, threshold):
        results = []
        for win, f in zip(windows, win_feats):
            confidence, label = self._window_confidence(f)
            if confidence < threshold:
                label = "unknown"
            results.append(self._make_detection(
                obj_id=win["id"],
                obj_type=label,
                confidence=confidence,
                geometry={"wall_id": win["wallId"], "position": win["position"]},
                properties={
                    "width": f["width"],
                    "height": f["height"],
                    "elevation": f["elevation"],
                    "aspect_ratio": f["aspect_ratio"],
                },
            ))
        return results

    def _window_confidence(self, f: Dict) -> Tuple[float, str]:
        score = 0.55
        # Typical window width 600–3000mm
        if 600 <= f["width"] <= 3000:
            score += 0.2
        # Elevation from ground (windows are above sill height)
        if 600 <= f["elevation"] <= 1500:
            score += 0.2
        # Aspect ratio – windows tend to be wider than tall
        if f["aspect_ratio"] >= 0.8:
            score += 0.05
        return min(round(score, 3), 0.99), "window"

    # ── Room classification ──────────────────────────────────────────────────
    def _classify_rooms(self, rooms, room_feats, threshold):
        results = []
        for r, f in zip(rooms, room_feats):
            confidence, label = self._room_confidence(r, f)
            if confidence < threshold:
                label = "unknown"
            results.append(self._make_detection(
                obj_id=r["id"],
                obj_type=label,
                confidence=confidence,
                geometry={"points": r.get("points", [])},
                properties={
                    "area": f["area"],
                    "perimeter": f["perimeter"],
                    "compactness": f["compactness"],
                    "suggested_name": label.replace("_", " ").title(),
                },
            ))
        return results

    def _room_confidence(self, room: Dict, f: Dict) -> Tuple[float, str]:
        area = f["area"]
        score = 0.5
        name = room.get("name", "").lower()
        label = "room"

        # Area-based room type classification
        if area < 2:
            label, score = "closet", 0.72
        elif area < 5:
            label, score = "bathroom", 0.78
        elif area < 10:
            label, score = "bedroom", 0.75
        elif area < 20:
            label, score = "living_room", 0.76
        elif area < 40:
            label, score = "open_plan", 0.70
        else:
            label, score = "large_space", 0.65

        # Name hint boost
        name_map = {
            "bedroom": "bedroom", "bath": "bathroom", "kitchen": "kitchen",
            "living": "living_room", "dining": "dining_room", "hall": "hallway",
            "corridor": "hallway", "garage": "garage", "office": "office",
            "study": "office", "closet": "closet", "storage": "storage",
        }
        for hint, mapped in name_map.items():
            if hint in name:
                label = mapped
                score = min(score + 0.12, 0.99)
                break

        # Compactness: rectangular rooms score higher
        if f["compactness"] > 0.7:
            score += 0.05

        return min(round(score, 3), 0.99), label

    # ── Detection object factory ─────────────────────────────────────────────
    @staticmethod
    def _make_detection(
        obj_id: str,
        obj_type: str,
        confidence: float,
        geometry: Dict,
        properties: Dict,
    ) -> Dict[str, Any]:
        return {
            "id": obj_id,
            "type": obj_type,
            "confidence": confidence,
            "needs_review": confidence < DEFAULT_CONFIDENCE_THRESHOLD,
            "geometry": geometry,
            "properties": properties,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

_default_model = HeuristicAIModel()


def run_ai_detection(
    canonical_json: Dict[str, Any],
    model=None,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> Dict[str, Any]:
    """
    Main entry point.  Runs feature extraction → AI model → enhanced canonical JSON.
    Returns the original canonical JSON enriched with `ai_detections` and
    `ai_metadata` keys, plus counts of items that need review.
    """
    if model is None:
        model = _default_model

    logger.info(f"Running AI detection with model: {model.name}")
    features = extract_geometric_features(canonical_json)
    detections = model.detect(canonical_json, features, threshold)

    needs_review = [d for d in detections if d.get("needs_review")]
    logger.info(
        f"AI detection complete: {len(detections)} objects, "
        f"{len(needs_review)} need review"
    )

    enhanced = dict(canonical_json)
    enhanced["ai_detections"] = detections
    enhanced["ai_metadata"] = {
        "model": model.name,
        "threshold": threshold,
        "total_detections": len(detections),
        "needs_review_count": len(needs_review),
        "feature_summary": {
            "wall_count": features["wall_count"],
            "door_count": features["door_count"],
            "window_count": features["window_count"],
            "room_count": features["room_count"],
        },
    }
    return enhanced


def apply_user_corrections(
    enhanced_json: Dict[str, Any],
    corrections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Apply user accept/reject/reclassify corrections to AI detections.
    Corrections format: [{id, action: 'accept'|'reject'|'reclassify', new_type?}]
    """
    detections = {d["id"]: d for d in enhanced_json.get("ai_detections", [])}
    for corr in corrections:
        did = corr.get("id")
        action = corr.get("action")
        if did not in detections:
            continue
        if action == "accept":
            detections[did]["needs_review"] = False
            detections[did]["user_accepted"] = True
        elif action == "reject":
            detections[did]["rejected"] = True
            detections[did]["needs_review"] = False
        elif action == "reclassify":
            detections[did]["type"] = corr.get("new_type", detections[did]["type"])
            detections[did]["user_reclassified"] = True
            detections[did]["needs_review"] = False
            detections[did]["confidence"] = 1.0  # user is authoritative

    result = dict(enhanced_json)
    result["ai_detections"] = list(detections.values())
    return result

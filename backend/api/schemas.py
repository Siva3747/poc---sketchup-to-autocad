from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# ─── Core geometry ────────────────────────────────────────────────────────────

class PointSchema(BaseModel):
    x: float
    y: float

class WallSchema(BaseModel):
    id: str
    start: PointSchema
    end: PointSchema
    thickness: float = 200.0
    height: float = 2800.0
    layer: str = "Walls"

class DoorSchema(BaseModel):
    id: str
    wallId: str
    position: float = Field(..., ge=0.0, le=1.0)
    width: float = 900.0
    height: float = 2100.0
    hand: str = "left"
    direction: str = "in"
    layer: str = "Doors"

class WindowSchema(BaseModel):
    id: str
    wallId: str
    position: float = Field(..., ge=0.0, le=1.0)
    width: float = 1200.0
    height: float = 1200.0
    elevation: float = 900.0
    layer: str = "Windows"

class RoomSchema(BaseModel):
    id: str
    name: str
    points: List[PointSchema]
    area: float
    layer: str = "Rooms"

class MetadataSchema(BaseModel):
    name: str = "Unnamed Model"
    unit: str = "mm"
    scale: float = 1.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# ─── Canonical JSON (floor plan) ──────────────────────────────────────────────

class FloorPlanSchema(BaseModel):
    metadata: MetadataSchema
    walls: List[WallSchema]
    doors: List[DoorSchema]
    windows: List[WindowSchema]
    rooms: List[RoomSchema]

# ─── AI Detection ────────────────────────────────────────────────────────────

class AIDetectionSchema(BaseModel):
    id: str
    type: str
    confidence: float
    needs_review: bool = False
    geometry: Dict[str, Any]
    properties: Dict[str, Any]
    user_accepted: Optional[bool] = None
    rejected: Optional[bool] = None
    user_reclassified: Optional[bool] = None

class AIMetadataSchema(BaseModel):
    model: str
    threshold: float
    total_detections: int
    needs_review_count: int
    feature_summary: Dict[str, Any]

class EnhancedFloorPlanSchema(FloorPlanSchema):
    ai_detections: List[AIDetectionSchema] = []
    ai_metadata: Optional[AIMetadataSchema] = None

# ─── AI Correction ───────────────────────────────────────────────────────────

class CorrectionSchema(BaseModel):
    id: str
    action: str  # accept | reject | reclassify
    new_type: Optional[str] = None

class CorrectionsRequest(BaseModel):
    project_id: str
    corrections: List[CorrectionSchema]

# ─── Project responses ────────────────────────────────────────────────────────

class ProjectResponse(BaseModel):
    id: str
    filename: str
    source_format: str = "skp"
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    has_dxf: bool
    has_dwg: bool
    has_skp_script: bool = False
    has_ai: bool = False

    class Config:
        from_attributes = True

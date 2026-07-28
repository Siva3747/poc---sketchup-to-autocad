from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

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
    hand: str = "left" # left, right
    direction: str = "in" # in, out
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
    name: str
    unit: str = "mm"
    scale: float = 1.0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class FloorPlanSchema(BaseModel):
    metadata: MetadataSchema
    walls: List[WallSchema]
    doors: List[DoorSchema]
    windows: List[WindowSchema]
    rooms: List[RoomSchema]

class ProjectResponse(BaseModel):
    id: str
    filename: str
    status: str
    error_message: Optional[str] = None
    created_at: str
    updated_at: str
    has_dxf: bool
    has_dwg: bool

    class Config:
        from_attributes = True

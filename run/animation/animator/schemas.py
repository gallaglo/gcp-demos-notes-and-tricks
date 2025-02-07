from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class Setup(BaseModel):
    frame_start: int = Field(1, description="Start frame of the animation")
    frame_end: int = Field(250, description="End frame of the animation")
    world_name: str = Field("Animation World", description="Name of the Blender world")

class Camera(BaseModel):
    location: Vector3
    rotation: Vector3

class Light(BaseModel):
    type: Literal["SUN", "POINT", "SPOT", "AREA"]
    location: Vector3
    energy: float = Field(5.0, description="Light intensity")
    rotation: Optional[Vector3] = None

class Material(BaseModel):
    name: str = Field("Material", description="Name of the material")
    color: List[float] = Field(..., description="RGBA color values", min_items=4, max_items=4)
    strength: float = Field(5.0, description="Emission strength")

class Animation(BaseModel):
    type: Literal["circular"]
    radius: float = Field(..., description="Radius of the circular motion")
    axis: Literal["XY", "XZ", "YZ"] = Field("XY", description="Plane of circular motion")

class Object(BaseModel):
    type: Literal["uv_sphere", "cube", "cylinder"]
    location: Vector3
    parameters: dict = Field(..., description="Object-specific parameters (e.g., radius, size)")
    material: Optional[Material] = None
    animation: Optional[Animation] = None

class BlenderScript(BaseModel):
    setup: Setup
    camera: Camera
    lights: List[Light]
    objects: List[Object]
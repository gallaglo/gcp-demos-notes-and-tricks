# Pydantic models for script structure
from typing import List, Tuple, Literal, Optional
from pydantic import BaseModel, Field

class SetupConfig(BaseModel):
    frame_start: int = Field(1, description="Start frame for animation")
    frame_end: int = Field(250, description="End frame for animation")
    world_name: str = Field("Animation World", description="Name of the Blender world")

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class CameraConfig(BaseModel):
    location: Vector3 = Field(..., description="Camera location in 3D space")
    rotation: Vector3 = Field(..., description="Camera rotation in radians")

class AnimationConfig(BaseModel):
    type: Literal["circular"] = Field(..., description="Type of animation")
    radius: float = Field(..., description="Radius of circular motion")
    axis: Literal["XY", "XZ", "YZ"] = Field("XY", description="Plane of circular motion")

class ObjectConfig(BaseModel):
    type: Literal["uv_sphere", "cube", "cylinder"] = Field(..., description="Type of 3D object")
    location: Vector3 = Field(..., description="Object location")
    parameters: dict = Field(..., description="Object-specific parameters (radius, size, etc)")
    animation: Optional[AnimationConfig] = Field(None, description="Animation configuration")
    material: Optional[dict] = Field(None, description="Material configuration")

class BlenderScript(BaseModel):
    setup: SetupConfig = Field(..., description="Basic scene setup configuration")
    camera: CameraConfig = Field(..., description="Camera configuration")
    lights: List[dict] = Field(..., description="Light configurations")
    objects: List[ObjectConfig] = Field(..., description="Scene objects configuration")

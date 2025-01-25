from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Vector3(BaseModel):
    x: float
    y: float
    z: float

class SetupConfig(BaseModel):
    frame_start: int = Field(1)
    frame_end: int = Field(250)
    world_name: str = Field("Animation World")

class CameraConfig(BaseModel):
    location: Vector3
    rotation: Vector3

class AnimationConfig(BaseModel):
    type: Literal["circular"]
    radius: float
    axis: Literal["XY", "XZ", "YZ"] = "XY"

class ObjectConfig(BaseModel):
    type: Literal["uv_sphere", "cube", "cylinder"]
    location: Vector3
    parameters: dict
    animation: Optional[AnimationConfig] = None
    material: Optional[dict] = None

class BlenderScript(BaseModel):
    setup: SetupConfig
    camera: CameraConfig
    lights: List[dict]
    objects: List[ObjectConfig]
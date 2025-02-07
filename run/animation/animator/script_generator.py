from typing import List, Dict, Any
import logging
import json
from schemas import BlenderScript, Setup, Camera, Light, Object, Vector3, Material, Animation
from langchain.schema import SystemMessage, HumanMessage
from langchain_google_vertexai.functions_utils import PydanticFunctionsOutputParser
from prompts import blender_prompt

logger = logging.getLogger(__name__)

class BlenderScriptGenerator:
    def __init__(self, llm):
        """Initialize the script generator with an LLM instance."""
        self.llm = llm
        self.parser = PydanticFunctionsOutputParser(
            pydantic_schema={
                "create_blender_scene": BlenderScript
            }
        )

    def generate(self, prompt: str) -> str:
        """Generate a complete Blender script from a text prompt."""
        try:
            # Use the prompt template from prompts.py
            messages = blender_prompt.format_messages(user_prompt=prompt)
            
            # Get response from LLM
            logger.info(f"Sending prompt to LLM: {prompt}")
            response = self.llm.invoke(messages)
            
            try:
                blender_script = self.parser.parse_result([response])
                logger.info("Successfully parsed LLM response into BlenderScript")
                
                # Generate the script
                return self._generate_script(blender_script)
            
            except Exception as e:
                logger.error(f"Failed to parse LLM response with function parser: {str(e)}")
                # Fallback to traditional JSON parsing
                content = response.content if hasattr(response, 'content') else str(response)
                json_data = self._parse_llm_response(content)
                
                # Transform the JSON to match our schema
                transformed_data = self._transform_json_to_schema(json_data)
                
                # Create BlenderScript instance using transformed data
                script_config = BlenderScript(**transformed_data)
                return self._generate_script(script_config)
            
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate script: {str(e)}")

    def _parse_llm_response(self, content: str) -> dict:
        """Parse the LLM response into a dictionary."""
        try:
            # Clean the content to find the JSON structure
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Find JSON structure
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start < 0 or end <= start:
                raise ValueError("No valid JSON structure found in response")
                
            json_content = content[start:end]
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            raise ValueError(f"Failed to parse response: {str(e)}")

    def _transform_json_to_schema(self, json_data: dict) -> dict:
        """Transform LLM JSON output to match our Pydantic schema."""
        try:
            transformed = {}
            
            # Transform setup
            transformed["setup"] = {
                "frame_start": 1,
                "frame_end": 250,
                "world_name": json_data.get("scene_setup", {}).get("name", "Animation World")
            }
            
            # Transform camera
            cam_data = json_data.get("camera", {})
            transformed["camera"] = {
                "location": self._convert_to_vector3(cam_data.get("location", [10, -10, 10])),
                "rotation": self._convert_to_vector3(cam_data.get("rotation", [0.785, 0, 0.785]))
            }
            
            # Transform lights
            transformed["lights"] = []
            for light in json_data.get("lights", []):
                transformed_light = {
                    "type": self._map_light_type(light.get("type", "SUN")),
                    "location": self._convert_to_vector3(light.get("location", [5, -5, 10])),
                    "energy": float(light.get("energy", 5))
                }
                if "rotation" in light:
                    transformed_light["rotation"] = self._convert_to_vector3(light["rotation"])
                transformed["lights"].append(transformed_light)
            
            # Transform objects
            transformed["objects"] = []
            for obj in json_data.get("objects", []):
                transformed_obj = {
                    "type": self._map_object_type(obj.get("type", "uv_sphere")),
                    "location": self._convert_to_vector3(obj.get("location", [0, 0, 0])),
                    "parameters": {"radius": float(obj.get("radius", 1.0))} if "radius" in obj else {"size": float(obj.get("size", 2.0))},
                }
                
                # Transform material
                if "material" in obj:
                    mat = obj["material"]
                    transformed_obj["material"] = {
                        "name": mat.get("name", "Material"),
                        "color": [1.0, 0.0, 0.0, 1.0] if "color" not in mat else self._ensure_color_format(mat["color"]),
                        "strength": float(mat.get("strength", 5))
                    }
                
                # Transform animation
                if "animation" in obj:
                    anim = obj["animation"]
                    transformed_obj["animation"] = {
                        "type": "circular",
                        "radius": float(anim.get("radius", 5.0)),
                        "axis": anim.get("axis", "XY").upper()
                    }
                
                transformed["objects"].append(transformed_obj)
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming JSON: {str(e)}")
            raise ValueError(f"Failed to transform JSON: {str(e)}")

    def _convert_to_vector3(self, value) -> dict:
        """Convert a list/tuple of coordinates to Vector3 format."""
        if isinstance(value, (list, tuple)):
            return {"x": float(value[0]), "y": float(value[1]), "z": float(value[2])}
        return value

    def _ensure_color_format(self, color) -> list:
        """Ensure color is in RGBA format."""
        if isinstance(color, (list, tuple)):
            # Add alpha channel if missing
            if len(color) == 3:
                return [float(c) for c in color] + [1.0]
            return [float(c) for c in color[:4]]
        elif isinstance(color, dict):
            return [
                float(color.get("r", 1.0)),
                float(color.get("g", 1.0)),
                float(color.get("b", 1.0)),
                float(color.get("a", 1.0))
            ]
        return [1.0, 1.0, 1.0, 1.0]

    def _map_light_type(self, light_type: str) -> str:
        """Map various light type descriptions to our supported types."""
        light_type = light_type.upper()
        if light_type in ["SUN", "POINT", "SPOT", "AREA"]:
            return light_type
        return "SUN"  # default

    def _map_object_type(self, obj_type: str) -> str:
        """Map various object type descriptions to our supported types."""
        type_mapping = {
            "SPHERE": "uv_sphere",
            "BALL": "uv_sphere",
            "UV_SPHERE": "uv_sphere",
            "CUBE": "cube",
            "BOX": "cube",
            "CYLINDER": "cylinder",
            "TUBE": "cylinder"
        }
        return type_mapping.get(obj_type.upper(), "uv_sphere")

    def _generate_script(self, config: BlenderScript) -> str:
        """Convert the BlenderScript model into a complete Python script."""
        script_parts = []
        
        # Add standard imports
        script_parts.append(self._get_standard_imports())
        
        # Add scene setup
        script_parts.append(self._generate_setup(config.setup))
        
        # Add camera setup
        script_parts.append(self._generate_camera(config.camera))
        
        # Add lighting setup
        script_parts.append(self._generate_lights(config.lights))
        
        # Add objects
        for obj in config.objects:
            script_parts.append(self._generate_object(obj))
        
        # Add export code
        script_parts.append(self._get_export_code())
        
        return "\n\n".join(script_parts)

    def _get_standard_imports(self) -> str:
        return """import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]"""

    def _generate_setup(self, setup: Setup) -> str:
        return f"""# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set frame range
bpy.context.scene.frame_start = {setup.frame_start}
bpy.context.scene.frame_end = {setup.frame_end}

# Create world
world = bpy.data.worlds.new(name="{setup.world_name}")
bpy.context.scene.world = world
world.use_nodes = True"""

    def _generate_camera(self, camera: Camera) -> str:
        return f"""# Create camera
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera_object)

# Set camera location and rotation
camera_object.location = ({camera.location.x}, {camera.location.y}, {camera.location.z})
camera_object.rotation_euler = ({camera.rotation.x}, {camera.rotation.y}, {camera.rotation.z})

# Make this the active camera
bpy.context.scene.camera = camera_object"""

    def _generate_lights(self, lights: List[Light]) -> str:
        light_parts = []
        for i, light in enumerate(lights):
            light_name = f"Light_{i}"
            light_parts.append(f"""# Create {light_name}
{light_name}_data = bpy.data.lights.new(name="{light_name}", type='{light.type}')
{light_name}_object = bpy.data.objects.new(name="{light_name}", object_data={light_name}_data)
bpy.context.scene.collection.objects.link({light_name}_object)
{light_name}_object.location = ({light.location.x}, {light.location.y}, {light.location.z})
{light_name}_data.energy = {light.energy}""")
            
            if light.rotation:
                light_parts.append(
                    f"{light_name}_object.rotation_euler = ({light.rotation.x}, {light.rotation.y}, {light.rotation.z})"
                )
        
        return "\n\n".join(light_parts)

    def _generate_object(self, obj: Object) -> str:
        """Generate code for creating and configuring an object."""
        # Create object based on type
        creation_code = {
            "uv_sphere": f"""bpy.ops.mesh.primitive_uv_sphere_add(
    radius={obj.parameters.get('radius', 1.0)},
    location=({obj.location.x}, {obj.location.y}, {obj.location.z})
)""",
            "cube": f"""bpy.ops.mesh.primitive_cube_add(
    size={obj.parameters.get('size', 2.0)},
    location=({obj.location.x}, {obj.location.y}, {obj.location.z})
)""",
            "cylinder": f"""bpy.ops.mesh.primitive_cylinder_add(
    radius={obj.parameters.get('radius', 1.0)},
    depth={obj.parameters.get('depth', 2.0)},
    location=({obj.location.x}, {obj.location.y}, {obj.location.z})
)"""
        }[obj.type]

        script_parts = [creation_code, "obj = bpy.context.active_object"]

        # Add material if specified
        if obj.material:
            script_parts.append(self._generate_material(obj.material))

        # Add animation if specified
        if obj.animation:
            script_parts.append(self._generate_animation(obj.animation))

        return "\n".join(script_parts)

    def _generate_material(self, material: Material) -> str:
        """Generate code for creating and configuring a material."""
        return f"""# Create material
material = bpy.data.materials.new(name="{material.name}")
material.use_nodes = True
nodes = material.node_tree.nodes
# Clear default nodes
nodes.clear()
# Create emission node
node_emission = nodes.new(type='ShaderNodeEmission')
node_emission.inputs[0].default_value = {material.color}
node_emission.inputs[1].default_value = {material.strength}
# Create output node
node_output = nodes.new(type='ShaderNodeOutputMaterial')
# Link nodes
links = material.node_tree.links
links.new(node_emission.outputs[0], node_output.inputs[0])
# Assign material to object
if obj.data.materials:
    obj.data.materials[0] = material
else:
    obj.data.materials.append(material)"""

    def _generate_animation(self, animation: Animation) -> str:
        """Generate code for creating an animation."""
        axis_mapping = {
            "XY": ("x", "y", "z", "cos", "sin", "obj.location.z"),
            "XZ": ("x", "z", "y", "cos", "sin", "obj.location.y"),
            "YZ": ("y", "z", "x", "cos", "sin", "obj.location.x")
        }
        
        x_axis, y_axis, fixed_axis, x_func, y_func, fixed_val = axis_mapping[animation.axis]
        
        return f"""# Create circular motion animation
radius = {animation.radius}
for frame in range(1, 251):
    angle = (frame / 250) * 2 * pi  # Convert frame to angle
    {x_axis} = radius * {x_func}(angle)
    {y_axis} = radius * {y_func}(angle)
    {fixed_axis} = {fixed_val}
    
    obj.location = ({x_axis}, {y_axis}, {fixed_axis})
    obj.keyframe_insert(data_path="location", frame=frame)"""

    def _get_export_code(self) -> str:
        """Get the standard export code."""
        return """# Export the scene
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)"""
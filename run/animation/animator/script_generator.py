from typing import List, Dict, Any
from langchain_core.output_parsers import PydanticOutputParser
import logging
import json
from schemas import BlenderScript, Setup, Camera, Light, Object, Vector3, Material, Animation
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

class BlenderScriptGenerator:
    def __init__(self, llm):
        """Initialize the script generator with an LLM instance."""
        self.llm = llm

    def generate(self, prompt: str) -> str:
        """Generate a complete Blender script from a text prompt."""
        try:
            messages = [
                SystemMessage(content="""You are a specialized AI that generates 3D animations using Blender.
Your task is to output a JSON object with this EXACT structure. Copy this structure EXACTLY:

{
  "setup": {
    "frame_start": 1,
    "frame_end": 250,
    "world_name": "Animation World"
  },
  "camera": {
    "location": {"x": 10, "y": -10, "z": 10},
    "rotation": {"x": 0.785, "y": 0, "z": 0.785}
  },
  "lights": [
    {
      "type": "SUN",
      "location": {"x": 5, "y": -5, "z": 10},
      "energy": 5
    }
  ],
  "objects": [
    {
      "type": "uv_sphere",
      "location": {"x": 0, "y": 0, "z": 0},
      "parameters": {"radius": 1.0},
      "material": {
        "name": "Material",
        "color": [1, 1, 1, 1],
        "strength": 5
      },
      "animation": {
        "type": "circular",
        "radius": 5,
        "axis": "XY"
      }
    }
  ]
}

Just copy this structure and modify the values. Do not modify the structure itself."""),
                HumanMessage(content=f"""Create a scene configuration for: {prompt}

Remember:
1. Copy the JSON structure exactly as shown above
2. Only modify the values, not the structure
3. Use the exact field names shown""")
            ]
            
            # Get response from LLM
            logger.info(f"Sending prompt to LLM: {prompt}")
            response = self.llm.invoke(messages)
            
            # Get content from response
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info("Raw content from LLM:")
            logger.info(content)
            
            # Parse JSON response
            json_data = self._parse_llm_response(content)
            logger.info("Parsed JSON data:")
            logger.info(json.dumps(json_data, indent=2))
            
            # Create BlenderScript instance directly
            script_config = BlenderScript(
                setup=Setup(**json_data["setup"]),
                camera=Camera(**json_data["camera"]),
                lights=[Light(**light) for light in json_data["lights"]],
                objects=[Object(**obj) for obj in json_data["objects"]]
            )
            
            logger.info("Successfully created BlenderScript instance")
            
            # Generate the script
            return self._generate_script(script_config)
            
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate script: {str(e)}")

    def _parse_llm_response(self, content: str) -> dict:
        """Parse the LLM response into a dictionary."""
        try:
            # Clean the content
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Remove JavaScript-style comments (both single and multi-line)
            import re
            # Remove single-line comments
            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
            # Remove multi-line comments
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            
            # Find JSON structure
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start < 0 or end <= start:
                raise ValueError("No valid JSON structure found in response")
                
            json_content = content[start:end]
            logger.info("Extracted JSON content:")
            logger.info(json_content)
            
            # Further clean up any trailing commas
            json_content = re.sub(r',(\s*[\]}])', r'\1', json_content)
            
            # Parse initial JSON
            try:
                json_data = json.loads(json_content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error at position {e.pos}: {str(e)}")
                logger.error(f"Context: {json_content[max(0, e.pos-50):min(len(json_content), e.pos+50)]}")
                # Try cleaning the content more aggressively
                cleaned = re.sub(r'[^\x20-\x7E]', '', json_content)  # Remove non-printable chars
                cleaned = re.sub(r',\s*([\]}])', r'\1', cleaned)     # Remove trailing commas
                json_data = json.loads(cleaned)
            
            logger.info("Successfully parsed JSON data")
            
            # Transform if needed
            if "scene" in json_data:
                json_data = self._transform_to_required_format(json_data)
                logger.info("Transformed scene-based JSON to required format")
            
            # Validate required fields
            required_fields = {"setup", "camera", "lights", "objects"}
            missing_fields = required_fields - set(json_data.keys())
            if missing_fields:
                raise ValueError(f"Missing required fields in JSON response: {missing_fields}")
                    
            return json_data
                
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Content: {content}")
            raise ValueError(f"Failed to parse response: {str(e)}")

    def _transform_to_required_format(self, data: dict) -> dict:
        """Transform any non-compliant JSON into our required format."""
        logger.info("Starting scene transformation")
        try:
            result = {
                "setup": {
                    "frame_start": 1,
                    "frame_end": 250,
                    "world_name": data.get("scene", {}).get("name", "Animation World")
                },
                "camera": {},
                "lights": [],
                "objects": []
            }
            
            scene = data.get("scene", {})
            
            # Transform camera
            if "camera" in scene:
                cam = scene["camera"]
                result["camera"] = {
                    "location": {
                        "x": float(cam.get("position", {}).get("x", 0)),
                        "y": float(cam.get("position", {}).get("y", -10)),
                        "z": float(cam.get("position", {}).get("z", 10))
                    },
                    "rotation": {
                        "x": float(cam.get("rotation", {}).get("x", 0.785)),
                        "y": float(cam.get("rotation", {}).get("y", 0)),
                        "z": float(cam.get("rotation", {}).get("z", 0.785))
                    }
                }
            
            # Transform lights
            if "lights" in scene:
                for light in scene["lights"]:
                    new_light = {
                        "type": self._map_light_type(light.get("type", "SUN")),
                        "location": {
                            "x": float(light.get("position", {}).get("x", 5)),
                            "y": float(light.get("position", {}).get("y", -5)),
                            "z": float(light.get("position", {}).get("z", 10))
                        },
                        "energy": float(light.get("intensity", 5))
                    }
                    result["lights"].append(new_light)
            
            # Transform objects
            if "objects" in scene:
                for obj in scene["objects"]:
                    new_obj = {
                        "type": self._map_object_type(obj.get("type", "")),
                        "location": {
                            "x": float(obj.get("position", {}).get("x", 0)),
                            "y": float(obj.get("position", {}).get("y", 0)),
                            "z": float(obj.get("position", {}).get("z", 0))
                        },
                        "parameters": self._extract_parameters(obj),
                        "material": self._extract_material(obj)
                    }
                    
                    # Add animation if exists
                    if "animation" in obj:
                        new_obj["animation"] = self._extract_animation(obj["animation"])
                    
                    result["objects"].append(new_obj)
            
            logger.info("Successfully transformed scene data")
            return result
            
        except Exception as e:
            logger.error(f"Error transforming scene data: {str(e)}")
            raise ValueError(f"Failed to transform scene data: {str(e)}")

    def _map_light_type(self, light_type: str) -> str:
        """Map various light type descriptions to our supported types."""
        light_type = light_type.upper()
        if light_type in ["SUN", "POINT", "SPOT", "AREA"]:
            return light_type
        if "DIRECT" in light_type:
            return "SUN"
        if "POINT" in light_type:
            return "POINT"
        return "SUN"

    def _map_object_type(self, obj_type: str) -> str:
        """Map various object type descriptions to our supported types."""
        obj_type = obj_type.lower()
        if obj_type in ["uv_sphere", "cube", "cylinder"]:
            return obj_type
        if obj_type in ["sphere", "ball"]:
            return "uv_sphere"
        if obj_type in ["box", "block"]:
            return "cube"
        if obj_type in ["tube", "pipe"]:
            return "cylinder"
        return "uv_sphere"

    def _extract_parameters(self, obj: dict) -> dict:
        """Extract object parameters based on type."""
        params = {}
        if "radius" in obj:
            params["radius"] = float(obj["radius"])
        elif "size" in obj:
            params["size"] = float(obj["size"])
        elif "scale" in obj:
            scale = obj["scale"]
            if isinstance(scale, (int, float)):
                params["size"] = float(scale)
            elif isinstance(scale, (list, tuple)):
                params["size"] = float(scale[0])
            elif isinstance(scale, dict):
                params["size"] = float(scale.get("x", 1.0))
        return params or {"radius": 1.0}

    def _extract_material(self, obj: dict) -> dict:
        """Extract material properties from object."""
        mat = obj.get("material", {})
        color = mat.get("color", {})
        
        # Handle different color formats
        if isinstance(color, dict):
            return {
                "name": mat.get("name", "Material"),
                "color": [
                    float(color.get("r", 1)),
                    float(color.get("g", 1)),
                    float(color.get("b", 1)),
                    1.0
                ],
                "strength": float(mat.get("strength", 5))
            }
        elif isinstance(color, (list, tuple)):
            return {
                "name": mat.get("name", "Material"),
                "color": [float(c) for c in color[:3]] + [1.0],
                "strength": float(mat.get("strength", 5))
            }
        
        return {
            "name": mat.get("name", "Material"),
            "color": [1.0, 1.0, 1.0, 1.0],
            "strength": float(mat.get("strength", 5))
        }

    def _extract_animation(self, anim: dict) -> dict:
        """Extract animation properties."""
        anim_type = anim.get("type", "circular").lower()
        if anim_type in ["circular", "orbit", "rotate"]:
            return {
                "type": "circular",
                "radius": float(anim.get("radius", 5.0)),
                "axis": anim.get("axis", "XY").upper()
            }
        return None

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
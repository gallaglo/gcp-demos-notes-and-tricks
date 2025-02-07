from typing import List, Dict, Any
import logging
import json
from schemas import BlenderScript, Setup, Camera, Light, Object, Vector3, Material, Animation
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_vertexai.functions_utils import PydanticFunctionsOutputParser
from langchain_core.output_parser import OutputParserException
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
            
            # Parse the response into a BlenderScript instance
            try:
                blender_script = self.parser.parse_result([response])
                logger.info("Successfully parsed LLM response into BlenderScript")
                
                # Generate the Python script
                return self._generate_script(blender_script)
            
            except OutputParserException as e:
                logger.error(f"Failed to parse LLM response: {str(e)}")
                # Fallback to traditional JSON parsing if function calling fails
                content = response.content if hasattr(response, 'content') else str(response)
                json_data = self._parse_llm_response(content)
                
                script_config = BlenderScript(
                    setup=Setup(**json_data["setup"]),
                    camera=Camera(**json_data["camera"]),
                    lights=[Light(**light) for light in json_data["lights"]],
                    objects=[Object(**obj) for obj in json_data["objects"]]
                )
                
                return self._generate_script(script_config)
            
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to generate script: {str(e)}")

    def _parse_llm_response(self, content: str) -> dict:
        """Legacy JSON parsing method as fallback."""
        try:
            # Clean the content
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Remove JavaScript-style comments
            import re
            content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
            content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
            
            # Find JSON structure
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start < 0 or end <= start:
                raise ValueError("No valid JSON structure found in response")
                
            json_content = content[start:end]
            json_content = re.sub(r',(\s*[\]}])', r'\1', json_content)
            
            return json.loads(json_content)
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}")
            logger.error(f"Content: {content}")
            raise ValueError(f"Failed to parse response: {str(e)}")

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
from typing import List
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
import logging
from schemas import BlenderScript, ObjectConfig, Vector3
from prompts import blender_prompt

logger = logging.getLogger(__name__)

class BlenderScriptGenerator:
    def __init__(self, llm):
        """Initialize the script generator with an LLM instance."""
        self.llm = llm
        self.parser = PydanticOutputParser(pydantic_object=BlenderScript)

    def generate(self, prompt: str) -> str:
        """Generate a complete Blender script from a text prompt."""
        try:
            formatted_prompt = blender_prompt.format_messages(
                user_prompt=prompt
            )
            
            # Call LLM with the formatted prompt
            response = self.llm.invoke(formatted_prompt)
            
            # Parse the response using the schema
            parsed_response = self.parser.parse(response.content)
            
            # Convert structured response to Blender script
            return self._generate_script(parsed_response)
            
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise ValueError(f"Failed to generate script: {str(e)}")

    def _generate_script(self, config: BlenderScript) -> str:
        """Convert the structured configuration into a complete Blender script."""
        script_parts = []
        
        # Add standard imports and setup
        script_parts.append(self._get_standard_imports())
        script_parts.append(self._generate_setup(config.setup))
        script_parts.append(self._generate_camera(config.camera))
        script_parts.append(self._generate_lights(config.lights))
        
        # Add objects and their animations
        for obj in config.objects:
            script_parts.append(self._generate_object(obj))
        
        # Add export code
        script_parts.append(self._get_export_code())
        
        return "\n\n".join(script_parts)

    def _get_standard_imports(self) -> str:
        """Get the standard import statements and argument handling."""
        return """import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]"""

    def _generate_setup(self, setup) -> str:
        """Generate the basic scene setup code."""
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

    def _generate_camera(self, camera) -> str:
        """Generate camera setup code."""
        return f"""# Create camera
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera_object)

# Set camera location and rotation
camera_object.location = ({camera.location.x}, {camera.location.y}, {camera.location.z})
camera_object.rotation_euler = ({camera.rotation.x}, {camera.rotation.y}, {camera.rotation.z})

# Make this the active camera
bpy.context.scene.camera = camera_object"""

    def _generate_lights(self, lights: List[dict]) -> str:
        """Generate lighting setup code."""
        light_parts = []
        for i, light in enumerate(lights):
            light_name = f"Light_{i}"
            light_parts.append(f"""# Create {light_name}
{light_name}_data = bpy.data.lights.new(name="{light_name}", type='{light["type"]}')
{light_name}_object = bpy.data.objects.new(name="{light_name}", object_data={light_name}_data)
bpy.context.scene.collection.objects.link({light_name}_object)
{light_name}_object.location = ({light["location"]["x"]}, {light["location"]["y"]}, {light["location"]["z"]})
{light_name}_data.energy = {light.get("energy", 5)}""")
            
            if "rotation" in light:
                light_parts.append(f"""{light_name}_object.rotation_euler = ({light["rotation"]["x"]}, {light["rotation"]["y"]}, {light["rotation"]["z"]})""")
        
        return "\n\n".join(light_parts)

    def _generate_object(self, obj: ObjectConfig) -> str:
        """Generate code for creating and animating an object."""
        # Create object based on type
        creation_code = self._get_object_creation_code(obj)
        material_code = self._generate_material(obj.material) if obj.material else ""
        animation_code = self._generate_animation(obj.animation) if obj.animation else ""
        
        return "\n\n".join(filter(None, [creation_code, material_code, animation_code]))

    def _get_object_creation_code(self, obj: ObjectConfig) -> str:
        """Generate the appropriate object creation code based on type."""
        creation_codes = {
            "uv_sphere": f"""bpy.ops.mesh.primitive_uv_sphere_add(
    radius={obj.parameters.get("radius", 1.0)},
    location=({obj.location.x}, {obj.location.y}, {obj.location.z})
)
sphere = bpy.context.active_object""",
            
            "cube": f"""bpy.ops.mesh.primitive_cube_add(
    size={obj.parameters.get("size", 2.0)},
    location=({obj.location.x}, {obj.location.y}, {obj.location.z})
)
cube = bpy.context.active_object""",
            
            "cylinder": f"""bpy.ops.mesh.primitive_cylinder_add(
    radius={obj.parameters.get("radius", 1.0)},
    depth={obj.parameters.get("depth", 2.0)},
    location=({obj.location.x}, {obj.location.y}, {obj.location.z})
)
cylinder = bpy.context.active_object"""
        }
        
        return creation_codes.get(obj.type, "")

    def _generate_material(self, material: dict) -> str:
        """Generate material setup code."""
        return f"""material = bpy.data.materials.new(name="{material.get('name', 'Material')}")
material.use_nodes = True
nodes = material.node_tree.nodes
# Clear default nodes
nodes.clear()
# Create emission node
node_emission = nodes.new(type='ShaderNodeEmission')
node_emission.inputs[0].default_value = {material.get('color', '(1, 1, 1, 1)')}
node_emission.inputs[1].default_value = {material.get('strength', 5.0)}
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

    def _generate_animation(self, animation) -> str:
        """Generate animation code based on the animation type."""
        if animation.type == "circular":
            return f"""# Circular motion animation
radius = {animation.radius}
for frame in range(1, 251):
    angle = (frame / 250) * 2 * pi  # Convert frame to angle
    
    # Calculate position based on animation plane
    if "{animation.axis}" == "XY":
        x = radius * cos(angle)
        y = radius * sin(angle)
        z = obj.location.z
    elif "{animation.axis}" == "XZ":
        x = radius * cos(angle)
        y = obj.location.y
        z = radius * sin(angle)
    else:  # YZ
        x = obj.location.x
        y = radius * cos(angle)
        z = radius * sin(angle)
    
    obj.location = (x, y, z)
    obj.keyframe_insert(data_path="location", frame=frame)"""
        return ""

    def _get_export_code(self) -> str:
        """Get the standard export code."""
        return """bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)"""
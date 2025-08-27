"""Blender Script Generation Tool for ADK Animation Agent"""
import logging
import re
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class BlenderScriptGenerator:
    """Handles Blender Python script generation and validation."""
    
    def generate(self, prompt: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate a Blender Python script from a text prompt.
        
        Args:
            prompt (str): Text description of the animation to create
            history (List[Dict], optional): Conversation history for context
            
        Returns:
            str: Python script for Blender
        """
        try:
            logger.info("Generating Blender script from prompt")
            
            # This is a simplified version - in a real implementation,
            # this would call the LLM with the proper prompt template
            # For now, we'll generate a basic script structure
            
            script = self._generate_basic_script(prompt)
            
            if not script:
                logger.error("Generated script is empty")
                raise ValueError("Empty script generated")
            
            # Apply common fixes to the script
            script = self._fix_common_script_issues(script)
            
            # Validate script has required components
            self._validate_script_requirements(script)
            
            # Add the command-line argument handling to ensure proper output path
            script = self._modify_script_for_output_path(script)
            
            return script
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise ValueError(f"Failed to generate script: {str(e)}")
    
    def _generate_basic_script(self, prompt: str) -> str:
        """Generate a basic Blender script template - this would normally use the LLM."""
        
        # Basic template for a spinning cube (simplified example)
        script = """import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]

# Basic Setup
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set frame range (start=1, end=250 for 10-second animation at 25fps)
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 250

# Create and setup world
world = bpy.data.worlds.new(name="Animation World")
bpy.context.scene.world = world
world.use_nodes = True

# Create camera
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera_object)

# Set camera location and rotation
camera_object.location = (10, -10, 10)
camera_object.rotation_euler = (radians(45), 0, radians(45))

# Make this the active camera
bpy.context.scene.camera = camera_object

# Create key light
key_light_data = bpy.data.lights.new(name="Key Light", type='SUN')
key_light_object = bpy.data.objects.new(name="Key Light", object_data=key_light_data)
bpy.context.scene.collection.objects.link(key_light_object)
key_light_object.location = (5, -5, 10)
key_light_object.rotation_euler = (radians(30), radians(15), radians(20))
key_light_data.energy = 5

# Create fill light
fill_light_data = bpy.data.lights.new(name="Fill Light", type='SUN')
fill_light_object = bpy.data.objects.new(name="Fill Light", object_data=fill_light_data)
bpy.context.scene.collection.objects.link(fill_light_object)
fill_light_object.location = (-8, -4, 8)
fill_light_data.energy = 2

# Create cube
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
cube = bpy.context.active_object

# Create material
material = bpy.data.materials.new(name="Cube Material")
material.use_nodes = True
nodes = material.node_tree.nodes
# Clear default nodes
nodes.clear()
# Create emission node
node_emission = nodes.new(type='ShaderNodeEmission')
node_emission.inputs[0].default_value = (0.8, 0.3, 0.1, 1)  # Orange color
node_emission.inputs[1].default_value = 3.0  # Strength
# Create output node
node_output = nodes.new(type='ShaderNodeOutputMaterial')
# Link nodes
links = material.node_tree.links
links.new(node_emission.outputs[0], node_output.inputs[0])
# Assign material to object
if cube.data.materials:
    cube.data.materials[0] = material
else:
    cube.data.materials.append(material)

# Animate rotation
for frame in range(1, 251):
    angle = (frame / 250) * 2 * pi  # Full rotation over animation
    cube.rotation_euler = (angle, angle * 0.5, angle * 0.3)
    cube.keyframe_insert(data_path="rotation_euler", frame=frame)

# Export animation
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)
"""
        return script

    def _fix_common_script_issues(self, script: str) -> str:
        """Fix common issues in generated Blender scripts."""
        # Fix camera creation if it has the wrong number of arguments
        script = script.replace(
            'camera_object = bpy.data.objects.new("Camera", "Camera", camera_data)',
            'camera_object = bpy.data.objects.new("Camera", camera_data)'
        )
        
        # Fix similar issues with other object types
        script = script.replace(
            'light_object = bpy.data.objects.new("Light", "Light", light_data)',
            'light_object = bpy.data.objects.new("Light", light_data)'
        )
        
        # Fix any issues with sun object creation
        script = script.replace(
            'sun_object = bpy.data.objects.new("Sun", "Sun", sun_data)',
            'sun_object = bpy.data.objects.new("Sun", sun_data)'
        )
        
        # Fix any issues with key_light object creation
        script = script.replace(
            'key_light_object = bpy.data.objects.new("Key Light", "Key Light", key_light_data)',
            'key_light_object = bpy.data.objects.new("Key Light", key_light_data)'
        )
        
        # Fix any issues with fill_light object creation
        script = script.replace(
            'fill_light_object = bpy.data.objects.new("Fill Light", "Fill Light", fill_light_data)',
            'fill_light_object = bpy.data.objects.new("Fill Light", fill_light_data)'
        )
        
        # Fix common rotation issues
        script = script.replace(
            'obj.rotation = (', 
            'obj.rotation_euler = ('
        )
        
        # Fix common scene issues
        script = script.replace(
            'bpy.context.scene.objects.link(',
            'bpy.context.scene.collection.objects.link('
        )
        
        # Replace any instances where three arguments are passed to bpy.data.objects.new
        pattern = r'bpy\.data\.objects\.new\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]+)[\'"],\s*([^)]+)\)'
        replacement = r'bpy.data.objects.new("\1", \3)'
        script = re.sub(pattern, replacement, script)
        
        return script

    def _modify_script_for_output_path(self, script: str) -> str:
        """Ensure the script has proper command-line argument handling for output path."""
        # Remove any existing output path assignments
        lines = script.split('\n')
        filtered_lines = [
            line for line in lines 
            if not ('output_path =' in line and 'os.path' in line)
        ]
        
        # Find the position after the imports
        import_end_idx = 0
        for i, line in enumerate(filtered_lines):
            if line.strip().startswith('import '):
                import_end_idx = i + 1
        
        # Insert our path handling code
        path_handling = [
            "",
            "# Get output path from command line arguments",
            "if \"--\" not in sys.argv:",
            "    raise Exception(\"Please provide the output path after '--'\")",
            "output_path = sys.argv[sys.argv.index(\"--\") + 1]",
            ""
        ]
        
        # Ensure sys is imported
        if 'import sys' not in script:
            path_handling.insert(0, "import sys")
        
        # Combine everything
        modified_script = (
            '\n'.join(filtered_lines[:import_end_idx]) + 
            '\n' + 
            '\n'.join(path_handling) + 
            '\n' + 
            '\n'.join(filtered_lines[import_end_idx:])
        )
        
        return modified_script

    def _validate_script_requirements(self, script: str) -> None:
        """Validates the generated script contains required components and no forbidden terms."""
        # Check for forbidden terms
        forbidden_terms = ['subprocess', 'os.system', 'eval(', 'exec(']
        for term in forbidden_terms:
            if term in script:
                raise ValueError(f'Generated script contains forbidden term: {term}')
        
        # Required components to check
        required_components = [
            'import bpy',
            'bpy.ops.export_scene.gltf(',
            'filepath=output_path',
            'export_format=\'GLB\'',
        ]
        
        for component in required_components:
            if component not in script:
                raise ValueError(f'Generated script missing required component: {component}')
                
        # Check for incorrect camera creation syntax (common issue)
        if 'bpy.data.objects.new(' in script and 'camera_data' in script:
            # Pattern match to see if there are more than two arguments in the call
            pattern = r'bpy\.data\.objects\.new\([\'"][^\'"]+[\'"],\s*[\'"][^\'"]+[\'"],\s*[^)]+\)'
            matches = re.findall(pattern, script)
            if matches:
                raise ValueError('Incorrect object creation syntax: too many arguments in bpy.data.objects.new()')

async def generate_blender_script( prompt: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Generate a Blender Python script based on user prompt.
    
    Args:
        prompt: Text description of the animation to create
        history: Conversation history for context
        
    Returns:
        Dictionary containing generated script and status
    """
    try:
        generator = BlenderScriptGenerator()
        script = generator.generate(prompt, history)
        
        # Store script in tool context state
        
        return {
            "status": "success",
            "script_preview": script[:200] + "..." if len(script) > 200 else script,
            "script_length": len(script),
            "message": "Blender script generated successfully"
        }
        
    except Exception as e:
        error_msg = f"Failed to generate Blender script: {str(e)}"
        logger.error(error_msg)
        
        # Store error in tool context state
        
        return {
            "status": "error",
            "error": error_msg,
            "script_preview": "",
            "message": "Failed to generate Blender script"
        }

async def get_generated_script() -> Dict[str, Any]:
    """
    Get the currently generated Blender script from state.
    
    Args:
        
    Returns:
        Dictionary containing script information
    """
    
    return {
        "script": "",
        "status": "not_started",
        "error": "",
        "has_script": False,
        "script_length": 0
    }
"""
This module contains prompt templates for the Blender animation generator.
"""

import os
from langchain.prompts import PromptTemplate

def load_blender_operators():
    """Load Blender operators from the operators file."""
    ops_path = os.path.join(os.path.dirname(__file__), 'blender-4.3-ops.txt')
    try:
        with open(ops_path, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        raise Exception(f"Blender operators file not found at: {ops_path}")

# Load operators at module level
BLENDER_OPERATORS = load_blender_operators()

BLENDER_TEMPLATE = '''You are a specialized Python code generator for Blender 4.3. Your task is to generate complete, working Python scripts for creating animations. Follow these rules:

1. Generate ONLY valid Python code
2. Use standard 4-space indentation
3. Do not include any instructional text or section headers
4. Use only ASCII characters (no special whitespace or line endings)
5. Include all required components in order:
   - Imports and setup
   - Camera and lighting
   - Helper functions
   - Custom animation code
   - Export code

### Instructions for script structure ###

Section 1: Start with these exact imports and setup:
import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]

# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set frame range (start=1, end=250 for 10-second animation at 25fps)
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 250

# Setup world
world = bpy.data.worlds.new(name="Animation World")
bpy.context.scene.world = world
world.use_nodes = True

Section 2: Then add this exact camera and lighting setup:
# Create camera
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera_object)
camera_object.location = (10, -10, 10)
camera_object.rotation_euler = (radians(45), 0, radians(45))
bpy.context.scene.camera = camera_object

# Create lights
key_light_data = bpy.data.lights.new(name="Key Light", type='SUN')
key_light_object = bpy.data.objects.new(name="Key Light", object_data=key_light_data)
bpy.context.scene.collection.objects.link(key_light_object)
key_light_object.location = (5, -5, 10)
key_light_object.rotation_euler = (radians(30), radians(15), radians(20))
key_light_data.energy = 5

fill_light_data = bpy.data.lights.new(name="Fill Light", type='SUN')
fill_light_object = bpy.data.objects.new(name="Fill Light", object_data=fill_light_data)
bpy.context.scene.collection.objects.link(fill_light_object)
fill_light_object.location = (-8, -4, 8)
fill_light_data.energy = 2

Section 3: Include these exact helper functions:
def create_colored_material(name, color):
    """Creates and returns a new material with the specified color."""
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    node_emission = nodes.new(type='ShaderNodeEmission')
    node_emission.inputs[0].default_value = (*color, 1)
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    material.node_tree.links.new(node_emission.outputs[0], node_output.inputs[0])
    return material

def create_object_with_material(name, mesh_type, size, location, color):
    """Creates an object with the specified mesh type and material."""
    if mesh_type == 'SPHERE':
        bpy.ops.mesh.primitive_uv_sphere_add(radius=size, location=location)
    elif mesh_type == 'CUBE':
        bpy.ops.mesh.primitive_cube_add(size=size, location=location)
    elif mesh_type == 'CYLINDER':
        bpy.ops.mesh.primitive_cylinder_add(radius=size, depth=size*2, location=location)
    
    obj = bpy.context.active_object
    obj.name = name
    material = create_colored_material(f"{{name}}_material", color)
    obj.data.materials.append(material)
    return obj

def animate_object(obj, start_frame=1, end_frame=None, motion='ROTATION', axis='Z', **kwargs):
    """Animates an object with specified motion type."""
    if end_frame is None:
        end_frame = bpy.context.scene.frame_end
    if end_frame > bpy.context.scene.frame_end:
        end_frame = bpy.context.scene.frame_end
    
    frames = end_frame - start_frame + 1
    
    if motion == 'ROTATION':
        speed = kwargs.get('speed', 1.0)
        for frame in range(start_frame, end_frame + 1):
            time = (frame - start_frame) / frames
            angle = time * speed * 2 * pi
            if axis == 'Z':
                obj.rotation_euler = (0, 0, angle)
            elif axis == 'X':
                obj.rotation_euler = (angle, 0, 0)
            elif axis == 'Y':
                obj.rotation_euler = (0, angle, 0)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    
    elif motion == 'ORBIT':
        radius = kwargs.get('radius', 5.0)
        center = kwargs.get('center', (0, 0, 0))
        speed = kwargs.get('speed', 1.0)
        
        original_location = obj.location.copy()
        
        for frame in range(start_frame, end_frame + 1):
            time = (frame - start_frame) / frames
            angle = time * speed * 2 * pi
            x = center[0] + radius * cos(angle)
            y = center[1] + radius * sin(angle)
            z = center[2]
            obj.location = (x, y, z)
            obj.keyframe_insert(data_path="location", frame=frame)
    
    elif motion == 'BOUNCE':
        height = kwargs.get('height', 2.0)
        frequency = kwargs.get('frequency', 2.0)
        
        original_location = obj.location.copy()
        
        for frame in range(start_frame, end_frame + 1):
            time = (frame - start_frame) / frames
            if axis == 'Z':
                z = original_location.z + abs(sin(time * frequency * pi)) * height
                obj.location.z = z
                obj.keyframe_insert(data_path="location", frame=frame)
            elif axis == 'Y':
                y = original_location.y + abs(sin(time * frequency * pi)) * height
                obj.location.y = y
                obj.keyframe_insert(data_path="location", frame=frame)
            elif axis == 'X':
                x = original_location.x + abs(sin(time * frequency * pi)) * height
                obj.location.x = x
                obj.keyframe_insert(data_path="location", frame=frame)

Section 4: Add your custom animation code here to create and animate objects based on the user's request.

Section 5: End with this exact export code:
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)

Available Blender Operators:
{operators}

Generate ONLY the Python code for this animation request (do not include any section headers or instructions):
{user_prompt}
'''

BLENDER_PROMPT = PromptTemplate(
    template=BLENDER_TEMPLATE,
    input_variables=["user_prompt", "operators"]
)
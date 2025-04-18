import os
import logging
import json
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ScriptGenerator")

# Template parts for Blender scripts
SCRIPT_HEADER = """
import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]
"""

SCRIPT_SETUP = """
# Clear existing objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Set frame range (start=1, end=250 for 10-second animation at 25fps)
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 250

# Create and setup world
world = bpy.data.worlds.new(name="Animation World")
bpy.context.scene.world = world
world.use_nodes = True
"""

CAMERA_SETUP = """
# Create camera
camera_data = bpy.data.cameras.new(name="Camera")
camera_object = bpy.data.objects.new("Camera", camera_data)
bpy.context.scene.collection.objects.link(camera_object)

# Set camera location and rotation
camera_object.location = (10, -10, 10)
camera_object.rotation_euler = (radians(45), 0, radians(45))

# Make this the active camera
bpy.context.scene.camera = camera_object
"""

LIGHTING_SETUP = """
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
"""

EXPORT_CODE = """
# Export animation
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)
"""

class AnimationType:
    """Constants for different animation types"""
    BOUNCE = "bounce"
    ROTATE = "rotate"
    ORBIT = "orbit"
    WAVE = "wave"
    SCALE = "scale"
    CUSTOM = "custom"

class AnimationScriptGenerator:
    """Generates Blender Python scripts for animations based on text prompts"""
    
    def __init__(self):
        """Initialize the script generator"""
        # Load any necessary resources or models here
        pass
    
    def generate_script(self, prompt: str, animation_type: Optional[str] = None) -> str:
        """
        Generate a complete Blender script based on a prompt.
        
        Args:
            prompt: A text description of the desired animation
            animation_type: Optional type specification to override detection
            
        Returns:
            str: Complete Blender Python script
        """
        # Basic prompt analysis to determine animation type
        detected_type = self._detect_animation_type(prompt) if not animation_type else animation_type
        
        # Generate the main animation content
        animation_content = self._generate_animation_content(prompt, detected_type)
        
        # Assemble the full script
        full_script = (
            SCRIPT_HEADER +
            SCRIPT_SETUP +
            CAMERA_SETUP +
            LIGHTING_SETUP +
            animation_content +
            EXPORT_CODE
        )
        
        return full_script
    
    def _detect_animation_type(self, prompt: str) -> str:
        """
        Analyze the prompt to detect what kind of animation is desired.
        
        Args:
            prompt: The user's text prompt
            
        Returns:
            str: The detected animation type
        """
        prompt_lower = prompt.lower()
        
        # Simple keyword matching for now - could be upgraded to ML classification
        if any(word in prompt_lower for word in ["bounce", "jumping", "hopping"]):
            return AnimationType.BOUNCE
        elif any(word in prompt_lower for word in ["rotate", "spin", "turning"]):
            return AnimationType.ROTATE
        elif any(word in prompt_lower for word in ["orbit", "revolve", "planet", "sun", "solar"]):
            return AnimationType.ORBIT
        elif any(word in prompt_lower for word in ["wave", "ripple", "oscillate"]):
            return AnimationType.WAVE
        elif any(word in prompt_lower for word in ["scale", "grow", "shrink", "enlarge"]):
            return AnimationType.SCALE
        else:
            return AnimationType.CUSTOM
    
    def _generate_animation_content(self, prompt: str, animation_type: str) -> str:
        """
        Generate the core animation content based on the prompt and detected type.
        
        Args:
            prompt: The user's text prompt
            animation_type: The type of animation to generate
            
        Returns:
            str: Python code for the specific animation
        """
        # Select the appropriate animation generator based on the type
        if animation_type == AnimationType.BOUNCE:
            return self._generate_bouncing_animation(prompt)
        elif animation_type == AnimationType.ROTATE:
            return self._generate_rotation_animation(prompt)
        elif animation_type == AnimationType.ORBIT:
            return self._generate_orbit_animation(prompt)
        elif animation_type == AnimationType.WAVE:
            return self._generate_wave_animation(prompt)
        elif animation_type == AnimationType.SCALE:
            return self._generate_scale_animation(prompt)
        else:
            return self._generate_custom_animation(prompt)
    
    def _extract_object_info(self, prompt: str):
        """Extract object information from the prompt"""
        # A simple extraction for now - could be enhanced with NLP
        prompt_lower = prompt.lower()
        
        # Default values
        shape = "sphere"
        color = "red"
        size = 1.0
        
        # Extract shape
        if "cube" in prompt_lower or "box" in prompt_lower:
            shape = "cube"
        elif "cylinder" in prompt_lower:
            shape = "cylinder"
        elif "cone" in prompt_lower:
            shape = "cone"
        elif "torus" in prompt_lower or "donut" in prompt_lower:
            shape = "torus"
        
        # Extract color - very basic approach
        color_map = {
            "red": (1.0, 0.0, 0.0, 1.0),
            "green": (0.0, 1.0, 0.0, 1.0),
            "blue": (0.0, 0.0, 1.0, 1.0),
            "yellow": (1.0, 1.0, 0.0, 1.0),
            "purple": (0.8, 0.0, 0.8, 1.0),
            "orange": (1.0, 0.5, 0.0, 1.0),
            "black": (0.0, 0.0, 0.0, 1.0),
            "white": (1.0, 1.0, 1.0, 1.0),
        }
        
        color_value = color_map["red"]  # Default
        for color_name, color_rgb in color_map.items():
            if color_name in prompt_lower:
                color = color_name
                color_value = color_rgb
                break
        
        # Extract size modifiers
        if "large" in prompt_lower or "big" in prompt_lower:
            size = 2.0
        elif "small" in prompt_lower or "tiny" in prompt_lower:
            size = 0.5
        
        return {
            "shape": shape,
            "color": color,
            "color_value": color_value,
            "size": size
        }
    
    def _create_object_code(self, object_info):
        """Generate code to create an object with the given properties"""
        shape = object_info["shape"]
        size = object_info["size"]
        color_value = object_info["color_value"]
        
        # Create object code
        if shape == "cube":
            object_creation = f"""
# Create a cube
bpy.ops.mesh.primitive_cube_add(size={size}, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "AnimatedCube"
"""
        elif shape == "sphere":
            object_creation = f"""
# Create a sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius={size}, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "AnimatedSphere"
"""
        elif shape == "cylinder":
            object_creation = f"""
# Create a cylinder
bpy.ops.mesh.primitive_cylinder_add(radius={size}, depth={size*2}, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "AnimatedCylinder"
"""
        elif shape == "cone":
            object_creation = f"""
# Create a cone
bpy.ops.mesh.primitive_cone_add(radius1={size}, radius2=0, depth={size*2}, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "AnimatedCone"
"""
        elif shape == "torus":
            object_creation = f"""
# Create a torus
bpy.ops.mesh.primitive_torus_add(major_radius={size}, minor_radius={size*0.25}, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "AnimatedTorus"
"""
        else:
            # Default to sphere
            object_creation = f"""
# Create a sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius={size}, location=(0, 0, 0))
obj = bpy.context.active_object
obj.name = "AnimatedSphere"
"""
        
        # Add material
        material_creation = f"""
# Create material
material = bpy.data.materials.new(name="Material")
material.use_nodes = True
nodes = material.node_tree.nodes
# Clear default nodes
nodes.clear()

# Create diffuse node
node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
node_diffuse.inputs[0].default_value = {color_value}  # Color (RGBA)

# Create output node
node_output = nodes.new(type='ShaderNodeOutputMaterial')

# Link nodes
links = material.node_tree.links
links.new(node_diffuse.outputs[0], node_output.inputs[0])

# Assign material to object
if obj.data.materials:
    obj.data.materials[0] = material
else:
    obj.data.materials.append(material)
"""
        
        return object_creation + material_creation
    
    def _generate_bouncing_animation(self, prompt: str) -> str:
        """Generate a bouncing ball animation"""
        object_info = self._extract_object_info(prompt)
        object_code = self._create_object_code(object_info)
        
        bounce_height = 5.0  # Default height
        if "high" in prompt.lower():
            bounce_height = 8.0
        elif "low" in prompt.lower():
            bounce_height = 3.0
        
        animation_code = f"""
# Animate the bouncing
frame_start = 1
frame_end = 250
total_frames = frame_end - frame_start

# Set initial location
obj.location = (0, 0, {bounce_height})
obj.keyframe_insert(data_path="location", frame=frame_start)

# Create bounce keyframes
bounce_count = 5
decay_factor = 0.7  # Each bounce gets lower

for bounce in range(bounce_count):
    # Calculate frames for this bounce cycle
    bounce_frames = int(total_frames / bounce_count)
    start_frame = frame_start + bounce * bounce_frames
    mid_frame = start_frame + bounce_frames // 2
    end_frame = start_frame + bounce_frames
    
    # Adjust height based on decay
    current_height = bounce_height * (decay_factor ** bounce)
    
    # Bottom of bounce (ground level)
    obj.location = (0, 0, object_info["size"])  # Object sits on the ground
    obj.keyframe_insert(data_path="location", frame=mid_frame)
    
    # Top of next bounce (if not the last bounce)
    if bounce < bounce_count - 1:
        obj.location = (0, 0, current_height)
        obj.keyframe_insert(data_path="location", frame=end_frame)

# Add ground plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create ground material
ground_mat = bpy.data.materials.new(name="GroundMaterial")
ground_mat.use_nodes = True
nodes = ground_mat.node_tree.nodes
nodes.clear()

node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
node_diffuse.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)  # Gray color

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = ground_mat.node_tree.links
links.new(node_diffuse.outputs[0], node_output.inputs[0])

if ground.data.materials:
    ground.data.materials[0] = ground_mat
else:
    ground.data.materials.append(ground_mat)
"""
        
        return object_code + animation_code
    
    def _generate_rotation_animation(self, prompt: str) -> str:
        """Generate a rotation animation"""
        object_info = self._extract_object_info(prompt)
        object_code = self._create_object_code(object_info)
        
        # Determine rotation speed and axis from prompt
        speed = 1.0  # Default speed
        if "fast" in prompt.lower():
            speed = 2.0
        elif "slow" in prompt.lower():
            speed = 0.5
        
        # Determine rotation axis
        axis = "Z"  # Default axis
        if "x axis" in prompt.lower():
            axis = "X"
        elif "y axis" in prompt.lower():
            axis = "Y"
        
        animation_code = f"""
# Animate the rotation
frame_start = 1
frame_end = 250

# Set initial rotation
obj.rotation_euler = (0, 0, 0)
obj.keyframe_insert(data_path="rotation_euler", frame=frame_start)

# Create rotation keyframes
full_rotations = {speed} * 2  # Number of complete rotations
for frame in range(frame_start, frame_end + 1, 10):  # Keyframe every 10 frames
    rotation_progress = (frame - frame_start) / (frame_end - frame_start)
    angle = rotation_progress * full_rotations * 2 * pi
    
    if "{axis}" == "X":
        obj.rotation_euler = (angle, 0, 0)
    elif "{axis}" == "Y":
        obj.rotation_euler = (0, angle, 0)
    else:  # Z
        obj.rotation_euler = (0, 0, angle)
    
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)

# Add a simple environment
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create ground material
ground_mat = bpy.data.materials.new(name="GroundMaterial")
ground_mat.use_nodes = True
nodes = ground_mat.node_tree.nodes
nodes.clear()

node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
node_diffuse.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)  # Gray color

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = ground_mat.node_tree.links
links.new(node_diffuse.outputs[0], node_output.inputs[0])

if ground.data.materials:
    ground.data.materials[0] = ground_mat
else:
    ground.data.materials.append(ground_mat)
"""
        
        return object_code + animation_code
    
    def _generate_orbit_animation(self, prompt: str) -> str:
        """Generate an orbiting animation (like planets around a sun)"""
        # For orbit animations, we need at least two objects
        prompt_lower = prompt.lower()
        
        # Determine if we're creating a solar system
        is_solar_system = any(term in prompt_lower for term in ["solar system", "planets", "sun"])
        
        if is_solar_system:
            # Create sun and planets
            animation_code = """
# Create the sun
bpy.ops.mesh.primitive_uv_sphere_add(radius=2.0, location=(0, 0, 0))
sun = bpy.context.active_object
sun.name = "Sun"

# Create sun material (emissive)
sun_mat = bpy.data.materials.new(name="SunMaterial")
sun_mat.use_nodes = True
nodes = sun_mat.node_tree.nodes
nodes.clear()

node_emission = nodes.new(type='ShaderNodeEmission')
node_emission.inputs[0].default_value = (1.0, 0.7, 0.2, 1.0)  # Sun color
node_emission.inputs[1].default_value = 5.0  # Strength

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = sun_mat.node_tree.links
links.new(node_emission.outputs[0], node_output.inputs[0])

if sun.data.materials:
    sun.data.materials[0] = sun_mat
else:
    sun.data.materials.append(sun_mat)

# Create planets
planet_colors = [
    (0.7, 0.3, 0.1, 1.0),  # Mercury (brownish)
    (0.9, 0.8, 0.5, 1.0),  # Venus (yellowish)
    (0.2, 0.3, 0.8, 1.0),  # Earth (blue)
    (0.8, 0.2, 0.1, 1.0),  # Mars (reddish)
    (0.7, 0.6, 0.5, 1.0),  # Jupiter (light brown)
    (0.8, 0.7, 0.5, 1.0),  # Saturn (light yellow)
    (0.5, 0.7, 0.9, 1.0),  # Uranus (light blue)
    (0.2, 0.4, 0.8, 1.0),  # Neptune (dark blue)
]

planet_sizes = [0.3, 0.5, 0.5, 0.4, 1.0, 0.9, 0.7, 0.7]
planet_distances = [3.5, 4.5, 6.0, 7.5, 10.0, 13.0, 16.0, 19.0]
orbit_speeds = [4.0, 3.0, 2.5, 2.0, 1.2, 0.9, 0.6, 0.4]

planets = []
for i in range(8):  # Create 8 planets
    bpy.ops.mesh.primitive_uv_sphere_add(radius=planet_sizes[i], location=(planet_distances[i], 0, 0))
    planet = bpy.context.active_object
    planet.name = f"Planet{i+1}"
    planets.append(planet)
    
    # Create planet material
    planet_mat = bpy.data.materials.new(name=f"PlanetMaterial{i+1}")
    planet_mat.use_nodes = True
    nodes = planet_mat.node_tree.nodes
    nodes.clear()
    
    node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
    node_diffuse.inputs[0].default_value = planet_colors[i]
    
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = planet_mat.node_tree.links
    links.new(node_diffuse.outputs[0], node_output.inputs[0])
    
    if planet.data.materials:
        planet.data.materials[0] = planet_mat
    else:
        planet.data.materials.append(planet_mat)

# Create orbit paths (circles)
for i, distance in enumerate(planet_distances):
    bpy.ops.curve.primitive_bezier_circle_add(radius=distance, location=(0, 0, 0))
    orbit = bpy.context.active_object
    orbit.name = f"Orbit{i+1}"
    
    # Make orbit path nearly invisible
    orbit_mat = bpy.data.materials.new(name=f"OrbitMaterial{i+1}")
    orbit_mat.use_nodes = True
    nodes = orbit_mat.node_tree.nodes
    nodes.clear()
    
    node_transparent = nodes.new(type='ShaderNodeBsdfTransparent')
    node_output = nodes.new(type='ShaderNodeOutputMaterial')
    links = orbit_mat.node_tree.links
    links.new(node_transparent.outputs[0], node_output.inputs[0])
    
    if orbit.data.materials:
        orbit.data.materials[0] = orbit_mat
    else:
        orbit.data.materials.append(orbit_mat)

# Animate planet orbits
frame_start = 1
frame_end = 250

for i, planet in enumerate(planets):
    # Orbital speed varies by planet
    orbit_speed = orbit_speeds[i]
    
    for frame in range(frame_start, frame_end + 1, 5):  # Keyframe every 5 frames
        # Calculate position along orbit
        angle = (frame - frame_start) * orbit_speed * 2 * pi / (frame_end - frame_start)
        x = planet_distances[i] * cos(angle)
        y = planet_distances[i] * sin(angle)
        z = 0  # All planets on the same plane for simplicity
        
        planet.location = (x, y, z)
        planet.keyframe_insert(data_path="location", frame=frame)
        
        # Also add some rotation to the planets
        planet.rotation_euler = (0, 0, angle * 2)  # Planet rotates as it orbits
        planet.keyframe_insert(data_path="rotation_euler", frame=frame)

# Adjust camera to view the whole system
camera_object.location = (0, -30, 20)
camera_object.rotation_euler = (radians(30), 0, 0)
"""
        else:
            # Default to simple orbit animation
            object_info = self._extract_object_info(prompt)
            
            animation_code = f"""
# Create central object
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
central = bpy.context.active_object
central.name = "CentralObject"

# Create central object material
central_mat = bpy.data.materials.new(name="CentralMaterial")
central_mat.use_nodes = True
nodes = central_mat.node_tree.nodes
nodes.clear()

node_emission = nodes.new(type='ShaderNodeEmission')
node_emission.inputs[0].default_value = (1.0, 0.7, 0.2, 1.0)  # Yellow glow
node_emission.inputs[1].default_value = 3.0  # Strength

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = central_mat.node_tree.links
links.new(node_emission.outputs[0], node_output.inputs[0])

if central.data.materials:
    central.data.materials[0] = central_mat
else:
    central.data.materials.append(central_mat)

# Create orbiting object
{self._create_object_code(object_info)}

# Move to initial position
obj.location = (5, 0, 0)

# Animate the orbit
frame_start = 1
frame_end = 250

# Create orbit path (circle)
bpy.ops.curve.primitive_bezier_circle_add(radius=5, location=(0, 0, 0))
orbit = bpy.context.active_object
orbit.name = "OrbitPath"

# Make orbit path nearly invisible
orbit_mat = bpy.data.materials.new(name="OrbitMaterial")
orbit_mat.use_nodes = True
nodes = orbit_mat.node_tree.nodes
nodes.clear()

node_transparent = nodes.new(type='ShaderNodeBsdfTransparent')
node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = orbit_mat.node_tree.links
links.new(node_transparent.outputs[0], node_output.inputs[0])

if orbit.data.materials:
    orbit.data.materials[0] = orbit_mat
else:
    orbit.data.materials.append(orbit_mat)

# Set keyframes for orbit
for frame in range(frame_start, frame_end + 1, 5):  # Keyframe every 5 frames
    angle = (frame - frame_start) * 2 * pi / (frame_end - frame_start)
    x = 5 * cos(angle)
    y = 5 * sin(angle)
    z = 0
    
    obj.location = (x, y, z)
    obj.keyframe_insert(data_path="location", frame=frame)
    
    # Also add some rotation to the orbiting object
    obj.rotation_euler = (0, 0, angle * 2)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)

# Adjust camera to view the whole system
camera_object.location = (0, -15, 10)
camera_object.rotation_euler = (radians(30), 0, 0)
"""
        
        return animation_code
    
    def _generate_wave_animation(self, prompt: str) -> str:
        """Generate a wave-like animation"""
        object_info = self._extract_object_info(prompt)
        
        # For wave animations, we'll create multiple objects
        animation_code = f"""
# Create a grid of objects for the wave
grid_size = 10
spacing = 1.0
wave_height = 2.0
wave_speed = 1.0

# Create a collection for the wave objects
wave_collection = bpy.data.collections.new("WaveObjects")
bpy.context.scene.collection.children.link(wave_collection)

# Create the grid of objects
objects = []
for x in range(grid_size):
    for y in range(grid_size):
        if "{object_info['shape']}" == "cube":
            bpy.ops.mesh.primitive_cube_add(size=0.8, location=(x * spacing, y * spacing, 0))
        else:
            bpy.ops.mesh.primitive_uv_sphere_add(radius=0.4, location=(x * spacing, y * spacing, 0))
        
        obj = bpy.context.active_object
        obj.name = f"WaveObject_{x}_{y}"
        objects.append(obj)
        
        # Move to wave collection
        bpy.context.scene.collection.objects.unlink(obj)
        wave_collection.objects.link(obj)
        
        # Create material
        material = bpy.data.materials.new(name=f"Material_{x}_{y}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        
        # Create diffuse node with color based on position
        node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
        # Create a gradient of colors
        r = 0.2 + (x / grid_size) * 0.6
        g = 0.2 + (y / grid_size) * 0.6
        b = {object_info['color_value'][2]}
        node_diffuse.inputs[0].default_value = (r, g, b, 1.0)
        
        # Create output node
        node_output = nodes.new(type='ShaderNodeOutputMaterial')
        
        # Link nodes
        links = material.node_tree.links
        links.new(node_diffuse.outputs[0], node_output.inputs[0])
        
        # Assign material to object
        if obj.data.materials:
            obj.data.materials[0] = material
        else:
            obj.data.materials.append(material)

# Animate the wave
frame_start = 1
frame_end = 250

for frame in range(frame_start, frame_end + 1, 2):  # Keyframe every 2 frames
    time = (frame - frame_start) / 20  # Time factor
    
    for i, obj in enumerate(objects):
        # Get grid position
        x = i % grid_size
        y = i // grid_size
        
        # Calculate wave height using sine functions
        wave_z = wave_height * sin(x/2 + time * wave_speed) * sin(y/2 + time * wave_speed)
        
        # Set object location
        obj.location = (x * spacing, y * spacing, wave_z)
        obj.keyframe_insert(data_path="location", frame=frame)

# Position camera to see the wave
camera_object.location = (grid_size * spacing / 2, -grid_size * spacing / 1.2, grid_size * spacing / 1.5)
camera_object.rotation_euler = (radians(40), 0, 0)
"""
        
        return animation_code
    
    def _generate_scale_animation(self, prompt: str) -> str:
        """Generate a scaling animation"""
        object_info = self._extract_object_info(prompt)
        object_code = self._create_object_code(object_info)
        
        # Determine scaling parameters
        scale_min = 0.2
        scale_max = 2.0
        pulse_count = 3
        
        if "pulse" in prompt.lower():
            # Pulsing animation
            animation_code = f"""
# Animate scaling (pulsing)
frame_start = 1
frame_end = 250
total_frames = frame_end - frame_start

# Set initial scale
obj.scale = (1, 1, 1)
obj.keyframe_insert(data_path="scale", frame=frame_start)

# Create pulsing animation
for pulse in range(pulse_count):
    # Calculate frames for this pulse cycle
    pulse_frames = int(total_frames / pulse_count)
    start_frame = frame_start + pulse * pulse_frames
    mid_frame = start_frame + pulse_frames // 2
    end_frame = start_frame + pulse_frames
    
    # Maximum scale
    obj.scale = (scale_max, scale_max, scale_max)
    obj.keyframe_insert(data_path="scale", frame=mid_frame)
    
    # Return to normal scale
    if pulse < pulse_count - 1:
        obj.scale = (1, 1, 1)
        obj.keyframe_insert(data_path="scale", frame=end_frame)

# Add ground plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create ground material
ground_mat = bpy.data.materials.new(name="GroundMaterial")
ground_mat.use_nodes = True
nodes = ground_mat.node_tree.nodes
nodes.clear()

node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
node_diffuse.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)  # Gray color

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = ground_mat.node_tree.links
links.new(node_diffuse.outputs[0], node_output.inputs[0])

if ground.data.materials:
    ground.data.materials[0] = ground_mat
else:
    ground.data.materials.append(ground_mat)
"""
        else:
            # Growing/shrinking animation
            animation_code = f"""
# Animate scaling (growing and shrinking)
frame_start = 1
frame_end = 250

# Set initial scale
obj.scale = (scale_min, scale_min, scale_min)
obj.keyframe_insert(data_path="scale", frame=frame_start)

# Grow to maximum size
max_frame = frame_start + (frame_end - frame_start) // 2
obj.scale = (scale_max, scale_max, scale_max)
obj.keyframe_insert(data_path="scale", frame=max_frame)

# Shrink back to minimum
obj.scale = (scale_min, scale_min, scale_min)
obj.keyframe_insert(data_path="scale", frame=frame_end)

# Add ground plane
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create ground material
ground_mat = bpy.data.materials.new(name="GroundMaterial")
ground_mat.use_nodes = True
nodes = ground_mat.node_tree.nodes
nodes.clear()

node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
node_diffuse.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)  # Gray color

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = ground_mat.node_tree.links
links.new(node_diffuse.outputs[0], node_output.inputs[0])

if ground.data.materials:
    ground.data.materials[0] = ground_mat
else:
    ground.data.materials.append(ground_mat)
"""
        
        return object_code + animation_code
    
    def _generate_custom_animation(self, prompt: str) -> str:
        """Generate a custom animation based on the prompt"""
        # For custom animations, try to combine elements from other types
        object_info = self._extract_object_info(prompt)
        object_code = self._create_object_code(object_info)
        
        # Create a simple animation that combines rotation and movement
        animation_code = f"""
# Create a custom animation combining movement and rotation
frame_start = 1
frame_end = 250

# Set initial position and rotation
obj.location = (0, 0, 0)
obj.rotation_euler = (0, 0, 0)
obj.keyframe_insert(data_path="location", frame=frame_start)
obj.keyframe_insert(data_path="rotation_euler", frame=frame_start)

# Create a figure-8 motion path
for frame in range(frame_start, frame_end + 1, 5):  # Keyframe every 5 frames
    # Calculate movement using parametric equations
    t = (frame - frame_start) / (frame_end - frame_start) * 2 * pi
    x = 5 * sin(t)
    y = 3 * sin(t * 2)
    z = 1 + sin(t * 3)  # Slight up/down movement
    
    obj.location = (x, y, z)
    obj.keyframe_insert(data_path="location", frame=frame)
    
    # Add rotation as object moves
    obj.rotation_euler = (t, t/2, t/3)
    obj.keyframe_insert(data_path="rotation_euler", frame=frame)

# Add ground plane
bpy.ops.mesh.primitive_plane_add(size=15, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"

# Create ground material
ground_mat = bpy.data.materials.new(name="GroundMaterial")
ground_mat.use_nodes = True
nodes = ground_mat.node_tree.nodes
nodes.clear()

node_diffuse = nodes.new(type='ShaderNodeBsdfDiffuse')
node_diffuse.inputs[0].default_value = (0.2, 0.2, 0.2, 1.0)  # Gray color

node_output = nodes.new(type='ShaderNodeOutputMaterial')
links = ground_mat.node_tree.links
links.new(node_diffuse.outputs[0], node_output.inputs[0])

if ground.data.materials:
    ground.data.materials[0] = ground_mat
else:
    ground.data.materials.append(ground_mat)

# Position camera to see the full animation path
camera_object.location = (0, -10, 5)
camera_object.rotation_euler = (radians(25), 0, 0)
"""
        
        return object_code + animation_code


# Create an instance of the generator
generator = AnimationScriptGenerator()

def generate_animation_script(prompt: str, animation_type: Optional[str] = None) -> str:
    """Public function to generate a Blender script from a prompt"""
    return generator.generate_script(prompt, animation_type)


if __name__ == "__main__":
    # Example usage
    test_prompt = "Create a red ball bouncing on the floor"
    script = generate_animation_script(test_prompt)
    print(script)
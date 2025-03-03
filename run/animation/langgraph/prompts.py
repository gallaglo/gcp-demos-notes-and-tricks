"""
This module contains prompt templates for the Blender animation generator.
"""

from langchain.prompts import PromptTemplate

BLENDER_TEMPLATE = """Create a Python script for Blender that will generate a 3D animation based on this description:
{user_prompt}

The script must start with this exact code for handling the output path and imports:
```python
import bpy
import sys
import math
from math import sin, cos, pi, radians

# Get output path from command line arguments
if "--" not in sys.argv:
    raise Exception("Please provide the output path after '--'")
output_path = sys.argv[sys.argv.index("--") + 1]
```

Then include these essential components in this exact order:

1. Basic Setup:
   - Clear existing objects:
     ```python
     bpy.ops.object.select_all(action='SELECT')
     bpy.ops.object.delete()
     ```
   - Set frame range (start=1, end=250 for 10-second animation at 25fps):
     ```python
     bpy.context.scene.frame_start = 1
     bpy.context.scene.frame_end = 250
     ```
   - Create and setup world (EXACTLY like this):
     ```python
     world = bpy.data.worlds.new(name="Animation World")
     bpy.context.scene.world = world
     world.use_nodes = True
     ```

2. Camera Setup (EXACTLY like this):
   ```python
   # Create camera
   camera_data = bpy.data.cameras.new(name="Camera")
   camera_object = bpy.data.objects.new("Camera", camera_data)
   bpy.context.scene.collection.objects.link(camera_object)
   
   # Set camera location and rotation
   camera_object.location = (10, -10, 10)
   camera_object.rotation_euler = (radians(45), 0, radians(45))
   
   # Make this the active camera
   bpy.context.scene.camera = camera_object
   ```

3. Lighting Setup (EXACTLY like this):
   ```python
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
   ```

4. Scene Requirements:
   For creating objects, ALWAYS use these exact patterns:
   
   For a UV Sphere:
   ```python
   bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))
   sphere = bpy.context.active_object
   ```
   
   For a Cube:
   ```python
   bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
   cube = bpy.context.active_object
   ```
   
   For a Cylinder:
   ```python
   bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0, location=(0, 0, 0))
   cylinder = bpy.context.active_object
   ```
   
   For circular motion animation:
   ```python
   # Example of circular motion
   radius = 5
   for frame in range(1, 251):
       angle = (frame / 250) * 2 * pi  # Convert frame to angle
       x = radius * cos(angle)
       y = radius * sin(angle)
       z = 0
       
       obj.location = (x, y, z)
       obj.keyframe_insert(data_path="location", frame=frame)
   ```

   For Materials:
   ```python
   material = bpy.data.materials.new(name="Material Name")
   material.use_nodes = True
   nodes = material.node_tree.nodes
   # Clear default nodes
   nodes.clear()
   # Create emission node
   node_emission = nodes.new(type='ShaderNodeEmission')
   node_emission.inputs[0].default_value = (1, 1, 1, 1)  # Color (RGBA)
   node_emission.inputs[1].default_value = 5.0  # Strength
   # Create output node
   node_output = nodes.new(type='ShaderNodeOutputMaterial')
   # Link nodes
   links = material.node_tree.links
   links.new(node_emission.outputs[0], node_output.inputs[0])
   # Assign material to object
   if obj.data.materials:
       obj.data.materials[0] = material
   else:
       obj.data.materials.append(material)
   ```

5. Animation Export:
   Use EXACTLY this export code at the end of the script:
   ```python
   bpy.ops.export_scene.gltf(
       filepath=output_path,
       export_format='GLB',
       export_animations=True,
       export_cameras=True,
       export_lights=True
   )
   ```

The script must run without GUI (headless mode) and include proper error handling.
Always use the exact code patterns shown above for creating objects, materials, and animations.
Always use math functions with the proper import and use radians() for angles.
Do not try to use any attributes or methods that aren't shown in the examples above."""

BLENDER_PROMPT = PromptTemplate(
    template=BLENDER_TEMPLATE,
    input_variables=["user_prompt"]
)

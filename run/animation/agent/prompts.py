"""
This module contains prompt templates for the Blender animation generator.
"""

from langchain.prompts import PromptTemplate
import json

# System prompt for chat functionality
CHAT_SYSTEM_PROMPT = """You are an AI assistant that specializes in creating 3D animations. You can:
1. Generate 3D animations based on text descriptions
2. Explain how different 3D animations work
3. Suggest improvements to animation ideas
4. Engage in general conversation

When a user asks you to create an animation, you'll generate a script for Blender (a 3D animation software) 
that can render their request. Be helpful, concise, and friendly in your responses.

Your main goal is to help users create interesting 3D animations and understand how they work.
"""

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
Do not try to use any attributes or methods that aren't shown in the examples above.
"""
BLENDER_PROMPT = PromptTemplate(
    template=BLENDER_TEMPLATE,
    input_variables=["user_prompt"]
)

EDIT_ANALYSIS_PROMPT = """You are an AI assistant that specializes in understanding user requests to modify 3D scenes. 
You're given a scene description in JSON format and a user's request for changes.

Your task is to analyze the request and determine what modifications should be made to the existing scene.
This includes:
1. Identifying which objects need to be modified
2. Determining what properties should be changed (position, rotation, scale, color, etc.)
3. Identifying if new objects should be added
4. Identifying if existing objects should be removed

The scene JSON contains an array of objects, each with:
- id: A unique identifier
- name: The display name
- type: The object type (sphere, cube, cylinder, plane, light, camera)
- position: [x, y, z] coordinates
- rotation: [x, y, z] rotation values
- scale: [x, y, z] scale values
- material: Properties like color, roughness, etc.
- properties: Additional type-specific properties

OUTPUT INSTRUCTIONS:
You must output a valid JSON object with these top-level keys:
1. "object_changes": An object mapping IDs to changes for existing objects
2. "add_objects": An array of new objects to add to the scene
3. "remove_object_ids": An array of object IDs to remove

For example:
```json
{
  "object_changes": {
    "obj_id_1": {
      "position": [1, 2, 3],
      "material": {
        "color": [1, 0, 0]
      }
    }
  },
  "add_objects": [
    {
      "id": "new_sphere_1",
      "name": "New Red Sphere",
      "type": "sphere",
      "position": [0, 0, 2],
      "rotation": [0, 0, 0],
      "scale": [1, 1, 1],
      "material": {
        "color": [1, 0, 0]
      },
      "properties": {
        "radius": 1.0
      }
    }
  ],
  "remove_object_ids": ["obj_id_2"]
}
```

IMPORTANT:
- Provide ONLY this JSON object in your response, nothing else
- Ensure all JSON is valid and properly formatted
- If you can't determine changes with confidence, provide an empty array or object for that category
- Use the exact object IDs from the scene when referring to existing objects
- For colors, use RGB values between 0 and 1
"""

# Model Context Protocol (MCP) for animation editing
MCP_EDIT_PROMPT = """<context>
  <scene>
    {scene_json}
  </scene>
  <conversation>
    {conversation_history}
  </conversation>
  <current_prompt>
    {user_prompt}
  </current_prompt>
</context>

You are an AI specialized in 3D animation editing. Your task is to analyze the user's request to modify the current 3D scene.

INSTRUCTIONS:
Based on the user's request and the current scene state, identify the exact modifications needed.

1. Determine which objects should be modified, added, or removed.
2. Specify exact parameter changes (position, rotation, color, scale, etc.).
3. Return your analysis as a structured JSON object.

OUTPUT FORMAT:
```json
{
  "object_changes": {
    "object_id_1": {
      "position": [x, y, z],
      "rotation": [x, y, z],
      "scale": [x, y, z],
      "material": {
        "color": [r, g, b]
      }
    }
  },
  "add_objects": [
    {
      "type": "sphere",
      "name": "New Object",
      "position": [x, y, z],
      "rotation": [x, y, z],
      "scale": [x, y, z],
      "material": {
        "color": [r, g, b]
      },
      "properties": {
        "radius": 1.0
      }
    }
  ],
  "remove_object_ids": ["object_id_2"],
  "operation_description": "Brief description of the changes being made"
}
```

ONLY return the JSON object, nothing else. Ensure all values are valid numbers and the JSON is properly formatted.
"""

# New prompts for scene modification analysis

# System prompt for scene modification analysis
SCENE_MODIFICATION_SYSTEM_PROMPT = """You are an assistant that specializes in understanding requests to modify 3D scenes.
Your task is to analyze the user's request and convert it into specific modifications for objects in the scene.
You will receive:
1. A description of the current scene
2. A list of objects in the scene with their properties
3. A user request for modifications

You must identify which objects to modify, add, or remove, and what specific changes to make to their properties.
"""

# Human message template for scene modification analysis
SCENE_MODIFICATION_HUMAN_TEMPLATE = """
Current scene description: {scene_description}

The scene contains these objects:
{object_descriptions}

The user wants to modify the scene with this request: "{prompt}"

Based on this request, I need you to:
1. Identify which existing objects should be modified and how
2. Identify if any new objects should be added
3. Identify if any existing objects should be removed

Provide your analysis as a valid JSON object in exactly this format:
```json
{{
  "object_changes": {{
    "object_id_1": {{
      "position": [x, y, z],
      "rotation": [x, y, z],
      "scale": [x, y, z],
      "material": {{
        "color": [r, g, b]
      }}
    }}
  }},
  "add_objects": [
    {{
      "type": "sphere", // or "cube", "cylinder", "plane"
      "name": "New Object Name",
      "position": [x, y, z],
      "rotation": [0, 0, 0],
      "scale": [1, 1, 1],
      "material": {{
        "color": [r, g, b]
      }},
      "properties": {{ // type-specific properties
        "radius": 1.0 // for spheres
        // or "size": 2.0 for cubes/planes
        // or "radius": 1.0, "depth": 2.0 for cylinders
      }}
    }}
  ],
  "remove_object_ids": ["object_id_2"]
}}
```

Only include the exact JSON response with no additional text.
"""

SCENE_MODIFICATION_PROMPT = PromptTemplate(
    template=SCENE_MODIFICATION_HUMAN_TEMPLATE,
    input_variables=["scene_description", "object_descriptions", "prompt"]
)

# Function to format the MCP edit prompt
def format_mcp_edit_prompt(scene_state, conversation_history, user_prompt):
    """Format the MCP edit prompt with scene state and conversation history"""
    # Convert scene state to JSON string
    scene_json = json.dumps(scene_state, indent=2)
    
    # Format conversation history as text
    formatted_history = ""
    for msg in conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        formatted_history += f"<{role}>{content}</{role}>\n"
    
    # Format the prompt
    return MCP_EDIT_PROMPT.format(
        scene_json=scene_json,
        conversation_history=formatted_history,
        user_prompt=user_prompt
    )
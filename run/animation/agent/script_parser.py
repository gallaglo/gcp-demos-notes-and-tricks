import re
import json
import uuid
from typing import Dict, List, Any, Tuple, Optional

class ScriptParser:
    """
    Parser for extracting scene state from Blender Python scripts.
    This allows us to maintain object context between animation generations.
    """
    
    def __init__(self, script: str):
        self.script = script
        self.objects = []
        self.settings = {
            "frameStart": 1,
            "frameEnd": 250,
            "fps": 25,
            "backgroundColor": [0.05, 0.05, 0.05]
        }
        
    def parse(self) -> Dict[str, Any]:
        """Parse script and extract scene state"""
        # Extract frame settings
        self._extract_frame_settings()
        
        # Extract objects
        self._extract_objects()
        
        # Extract animations
        self._extract_animations()
        
        # Extract world settings
        self._extract_world_settings()
        
        # Build the scene state
        scene_state = {
            "id": str(uuid.uuid4()),
            "objects": self.objects,
            "settings": self.settings,
            "description": self._extract_description(),
            "createdAt": "",  # Will be set when saving
        }
        
        return scene_state
    
    def _extract_frame_settings(self):
        """Extract frame range and FPS settings"""
        frame_start_match = re.search(r'bpy\.context\.scene\.frame_start\s*=\s*(\d+)', self.script)
        if frame_start_match:
            self.settings["frameStart"] = int(frame_start_match.group(1))
            
        frame_end_match = re.search(r'bpy\.context\.scene\.frame_end\s*=\s*(\d+)', self.script)
        if frame_end_match:
            self.settings["frameEnd"] = int(frame_end_match.group(1))
            
        fps_match = re.search(r'bpy\.context\.scene\.render\.fps\s*=\s*(\d+)', self.script)
        if fps_match:
            self.settings["fps"] = int(fps_match.group(1))
    
    def _extract_objects(self):
        """Extract object definitions from the script"""
        # Match primitive object creations
        primitive_patterns = {
            'sphere': r'bpy\.ops\.mesh\.primitive_uv_sphere_add\((?:[^)]*radius=([0-9.]+))?[^)]*(?:location=\(([^)]+)\))?\)',
            'cube': r'bpy\.ops\.mesh\.primitive_cube_add\((?:[^)]*size=([0-9.]+))?[^)]*(?:location=\(([^)]+)\))?\)',
            'cylinder': r'bpy\.ops\.mesh\.primitive_cylinder_add\((?:[^)]*radius=([0-9.]+))?[^)]*(?:depth=([0-9.]+))?[^)]*(?:location=\(([^)]+)\))?\)',
            'plane': r'bpy\.ops\.mesh\.primitive_plane_add\((?:[^)]*size=([0-9.]+))?[^)]*(?:location=\(([^)]+)\))?\)',
        }
        
        # Find all variable assignments that might be objects
        obj_assignments = re.finditer(r'(\w+)\s*=\s*bpy\.context\.active_object', self.script)
        
        for match in obj_assignments:
            obj_name = match.group(1)
            obj_pos = match.start()
            
            # Look backwards to find what primitive created this object
            script_before = self.script[:obj_pos]
            
            # Check for each primitive type
            obj_type = None
            obj_props = {}
            
            for prim_type, pattern in primitive_patterns.items():
                prim_match = list(re.finditer(pattern, script_before))
                if prim_match:
                    # Take the closest match before the assignment
                    prim_match = prim_match[-1]
                    obj_type = prim_type
                    
                    # Extract properties based on type
                    if prim_type == 'sphere':
                        radius = prim_match.group(1) or "1.0"
                        location = prim_match.group(2) or "0, 0, 0"
                        obj_props = {
                            "radius": float(radius),
                            "location": self._parse_vector(location)
                        }
                    elif prim_type == 'cube':
                        size = prim_match.group(1) or "2.0"
                        location = prim_match.group(2) or "0, 0, 0"
                        obj_props = {
                            "size": float(size),
                            "location": self._parse_vector(location)
                        }
                    elif prim_type == 'cylinder':
                        radius = prim_match.group(1) or "1.0"
                        depth = prim_match.group(2) or "2.0"
                        location = prim_match.group(3) or "0, 0, 0"
                        obj_props = {
                            "radius": float(radius),
                            "depth": float(depth),
                            "location": self._parse_vector(location)
                        }
                    elif prim_type == 'plane':
                        size = prim_match.group(1) or "2.0"
                        location = prim_match.group(2) or "0, 0, 0"
                        obj_props = {
                            "size": float(size),
                            "location": self._parse_vector(location)
                        }
                    break
            
            # If we found a valid object, extract additional properties
            if obj_type:
                # Look for rotation after the assignment
                script_after = self.script[obj_pos:]
                rotation = self._extract_rotation(script_after, obj_name)
                scale = self._extract_scale(script_after, obj_name)
                material = self._extract_material(script_after, obj_name)
                
                # Create object entry
                obj_entry = {
                    "id": str(uuid.uuid4()),
                    "name": obj_name,
                    "type": obj_type,
                    "position": obj_props.get("location", [0, 0, 0]),
                    "rotation": rotation,
                    "scale": scale,
                    "material": material,
                    "properties": obj_props
                }
                
                self.objects.append(obj_entry)
        
        # Also extract cameras and lights
        self._extract_cameras()
        self._extract_lights()
    
    def _extract_cameras(self):
        """Extract camera objects from the script"""
        camera_pattern = r'camera_data\s*=\s*bpy\.data\.cameras\.new\(name="([^"]+)"\)[^]*?camera_object\s*=\s*bpy\.data\.objects\.new\("([^"]+)",\s*camera_data\)[^]*?camera_object\.location\s*=\s*\(([^)]+)\)[^]*?camera_object\.rotation_euler\s*=\s*\(([^)]+)\)'
        
        # Use re.DOTALL to match across multiple lines
        camera_matches = re.finditer(camera_pattern, self.script, re.DOTALL)
        
        for match in camera_matches:
            camera_name = match.group(2)
            location = self._parse_vector(match.group(3))
            rotation = self._parse_vector(match.group(4))
            
            camera_obj = {
                "id": str(uuid.uuid4()),
                "name": camera_name,
                "type": "camera",
                "position": location,
                "rotation": rotation,
                "scale": [1, 1, 1],
                "properties": {
                    "isActive": "bpy.context.scene.camera = camera_object" in match.group(0)
                }
            }
            
            self.objects.append(camera_obj)
    
    def _extract_lights(self):
        """Extract light objects from the script"""
        light_pattern = r'(\w+)_light_data\s*=\s*bpy\.data\.lights\.new\(name="([^"]+)",\s*type=\'([^\']+)\'\)[^]*?(\w+)_light_object\s*=\s*bpy\.data\.objects\.new\((?:name="[^"]+",\s*object_data=\w+_light_data|"[^"]+",\s*\w+_light_data)\)[^]*?(\w+)_light_object\.location\s*=\s*\(([^)]+)\)'
        
        # Use re.DOTALL to match across multiple lines
        light_matches = re.finditer(light_pattern, self.script, re.DOTALL)
        
        for match in light_matches:
            light_type = match.group(3).lower()
            light_name = match.group(2)
            location = self._parse_vector(match.group(6))
            
            # Look for energy setting
            energy_match = re.search(rf'{match.group(1)}_light_data\.energy\s*=\s*([0-9.]+)', self.script)
            energy = float(energy_match.group(1)) if energy_match else 1.0
            
            # Look for rotation if present
            rotation_match = re.search(rf'{match.group(1)}_light_object\.rotation_euler\s*=\s*\(([^)]+)\)', self.script)
            rotation = self._parse_vector(rotation_match.group(1)) if rotation_match else [0, 0, 0]
            
            light_obj = {
                "id": str(uuid.uuid4()),
                "name": light_name,
                "type": "light",
                "position": location,
                "rotation": rotation,
                "scale": [1, 1, 1],
                "properties": {
                    "lightType": light_type,
                    "energy": energy
                }
            }
            
            self.objects.append(light_obj)
    
    def _extract_animations(self):
        """Extract animation data for objects"""
        # Find animation loops
        animation_pattern = r'for\s+frame\s+in\s+range\([^)]+\):[^}]*?(\w+)\.location\s*=\s*\(([^)]+)\)[^}]*?(\w+)\.keyframe_insert\(data_path="([^"]+)"'
        
        animation_matches = re.finditer(animation_pattern, self.script, re.DOTALL)
        
        for match in animation_matches:
            obj_name = match.group(1)
            property_path = match.group(4)
            
            # Find the corresponding object
            for obj in self.objects:
                if obj["name"] == obj_name:
                    # Initialize animation array if it doesn't exist
                    if "animation" not in obj:
                        obj["animation"] = []
                    
                    # Extract keyframe pattern
                    keyframe_pattern = rf'frame\s*=\s*(\d+)[^}}]*?\.location\s*=\s*\(([^)]+)\)'
                    keyframe_matches = re.finditer(keyframe_pattern, match.group(0), re.DOTALL)
                    
                    keyframes = []
                    for kf_match in keyframe_matches:
                        frame = int(kf_match.group(1))
                        value = self._parse_vector(kf_match.group(2))
                        keyframes.append({
                            "frame": frame,
                            "value": value
                        })
                    
                    # Add animation data
                    if keyframes:
                        obj["animation"].append({
                            "property": property_path,
                            "keyframes": keyframes
                        })
                    
                    break
    
    def _extract_world_settings(self):
        """Extract world background and environment settings"""
        # Check for world background color
        bg_color_match = re.search(r'world\.node_tree\.nodes\["Background"\]\.inputs\[0\]\.default_value\s*=\s*\(([^)]+)\)', self.script)
        if bg_color_match:
            color_values = self._parse_vector(bg_color_match.group(1))
            # Only take RGB from RGBA
            if len(color_values) >= 3:
                self.settings["backgroundColor"] = color_values[:3]
        
        # Check for world strength (environment lighting)
        env_strength_match = re.search(r'world\.node_tree\.nodes\["Background"\]\.inputs\[1\]\.default_value\s*=\s*([0-9.]+)', self.script)
        if env_strength_match:
            self.settings["environmentLighting"] = float(env_strength_match.group(1))
    
    def _extract_material(self, script_part: str, obj_name: str) -> Dict[str, Any]:
        """Extract material properties for an object"""
        material = {}
        
        # Look for color assignment
        color_match = re.search(rf'(?:material|mat)\.node_tree\.nodes\[.*?\]\.inputs\[0\]\.default_value\s*=\s*\(([^)]+)\)[^}}]*?{obj_name}\.data\.materials', script_part)
        if color_match:
            color = self._parse_vector(color_match.group(1))
            if len(color) >= 3:
                material["color"] = color[:3]
        
        # Look for emission
        if "ShaderNodeEmission" in script_part:
            emission_match = re.search(r'node_emission\.inputs\[1\]\.default_value\s*=\s*([0-9.]+)', script_part)
            if emission_match:
                material["emission"] = True
                material["emissionStrength"] = float(emission_match.group(1))
        
        # Look for other material properties
        roughness_match = re.search(r'node_bsdf\.inputs\["Roughness"\]\.default_value\s*=\s*([0-9.]+)', script_part)
        if roughness_match:
            material["roughness"] = float(roughness_match.group(1))
        
        metallic_match = re.search(r'node_bsdf\.inputs\["Metallic"\]\.default_value\s*=\s*([0-9.]+)', script_part)
        if metallic_match:
            material["metallic"] = float(metallic_match.group(1))
            
        return material
    
    def _extract_rotation(self, script_part: str, obj_name: str) -> List[float]:
        """Extract rotation for an object"""
        rotation_match = re.search(rf'{obj_name}\.rotation_euler\s*=\s*\(([^)]+)\)', script_part)
        if rotation_match:
            return self._parse_vector(rotation_match.group(1))
        return [0, 0, 0]
    
    def _extract_scale(self, script_part: str, obj_name: str) -> List[float]:
        """Extract scale for an object"""
        # Look for uniform scale
        uniform_scale_match = re.search(rf'{obj_name}\.scale\s*=\s*\(([^)]+)\)', script_part)
        if uniform_scale_match:
            return self._parse_vector(uniform_scale_match.group(1))
            
        # Look for scale_xyz
        scale_match = re.search(rf'{obj_name}\.scale\s*=\s*\(([^)]+)\)', script_part)
        if scale_match:
            return self._parse_vector(scale_match.group(1))
        
        return [1, 1, 1]
    
    def _parse_vector(self, vector_str: str) -> List[float]:
        """Parse a vector string into a list of floats"""
        # Handle expressions like 'radians(45)' by evaluating them
        values = []
        components = vector_str.split(',')
        
        for comp in components:
            comp = comp.strip()
            try:
                # Handle radians() function
                if 'radians' in comp:
                    angle_match = re.search(r'radians\(([^)]+)\)', comp)
                    if angle_match:
                        angle = float(angle_match.group(1))
                        rad_value = angle * 3.14159 / 180.0
                        values.append(rad_value)
                    else:
                        values.append(0.0)
                else:
                    # Normal float value
                    values.append(float(comp))
            except ValueError:
                # If we can't parse it, use 0
                values.append(0.0)
        
        return values
    
    def _extract_description(self) -> str:
        """Extract or generate a description of the scene"""
        # Look for a comment at the top of the file that might describe the scene
        desc_match = re.search(r'#\s*(.+)', self.script)
        if desc_match:
            return desc_match.group(1)
        
        # Count objects by type to generate a simple description
        type_counts = {}
        for obj in self.objects:
            obj_type = obj["type"]
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        # Generate a simple description
        description_parts = []
        for obj_type, count in type_counts.items():
            if obj_type not in ["camera", "light"]:
                description_parts.append(f"{count} {obj_type}{'s' if count > 1 else ''}")
        
        if description_parts:
            return "Scene with " + ", ".join(description_parts)
        else:
            return "Empty scene"

# Function to generate Blender script from scene state
def generate_script_from_scene_state(scene_state: Dict[str, Any]) -> str:
    """
    Generate a Blender Python script from a scene state.
    This allows us to continue from a previous scene state.
    """
    script = """import bpy
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

# Set frame range
bpy.context.scene.frame_start = {frame_start}
bpy.context.scene.frame_end = {frame_end}
bpy.context.scene.render.fps = {fps}

# Create and setup world
world = bpy.data.worlds.new(name="Animation World")
bpy.context.scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes["Background"]
bg_node.inputs[0].default_value = ({bg_r}, {bg_g}, {bg_b}, 1.0)
""".format(
        frame_start=scene_state["settings"]["frameStart"],
        frame_end=scene_state["settings"]["frameEnd"],
        fps=scene_state["settings"].get("fps", 25),
        bg_r=scene_state["settings"]["backgroundColor"][0],
        bg_g=scene_state["settings"]["backgroundColor"][1],
        bg_b=scene_state["settings"]["backgroundColor"][2]
    )
    
    # Add environment strength if present
    if "environmentLighting" in scene_state["settings"]:
        script += f"bg_node.inputs[1].default_value = {scene_state['settings']['environmentLighting']}\n"
    
    # Map of object IDs to variable names for references
    obj_var_names = {}
    
    # First add all cameras and lights
    for obj in scene_state["objects"]:
        if obj["type"] == "camera":
            var_name = "camera_object"
            obj_var_names[obj["id"]] = var_name
            
            script += f"""
# Create camera
camera_data = bpy.data.cameras.new(name="{obj["name"]}")
{var_name} = bpy.data.objects.new("{obj["name"]}", camera_data)
bpy.context.scene.collection.objects.link({var_name})

# Set camera location and rotation
{var_name}.location = ({obj["position"][0]}, {obj["position"][1]}, {obj["position"][2]})
{var_name}.rotation_euler = ({obj["rotation"][0]}, {obj["rotation"][1]}, {obj["rotation"][2]})

# Make this the active camera
bpy.context.scene.camera = {var_name}
"""
        elif obj["type"] == "light":
            light_type = obj["properties"].get("lightType", "POINT").upper()
            var_prefix = f"{obj['name'].lower().replace(' ', '_')}"
            var_name = f"{var_prefix}_object"
            obj_var_names[obj["id"]] = var_name
            
            script += f"""
# Create {obj["name"]}
{var_prefix}_data = bpy.data.lights.new(name="{obj["name"]}", type='{light_type}')
{var_name} = bpy.data.objects.new(name="{obj["name"]}", object_data={var_prefix}_data)
bpy.context.scene.collection.objects.link({var_name})
{var_name}.location = ({obj["position"][0]}, {obj["position"][1]}, {obj["position"][2]})
{var_name}.rotation_euler = ({obj["rotation"][0]}, {obj["rotation"][1]}, {obj["rotation"][2]})
{var_prefix}_data.energy = {obj["properties"].get("energy", 1.0)}
"""
    
    # Now add all other objects
    for obj in scene_state["objects"]:
        if obj["type"] not in ["camera", "light"]:
            var_name = obj["name"].lower().replace(" ", "_")
            obj_var_names[obj["id"]] = var_name
            
            if obj["type"] == "sphere":
                script += f"""
# Create {obj["name"]}
bpy.ops.mesh.primitive_uv_sphere_add(
    radius={obj["properties"].get("radius", 1.0)},
    location=({obj["position"][0]}, {obj["position"][1]}, {obj["position"][2]})
)
{var_name} = bpy.context.active_object
{var_name}.rotation_euler = ({obj["rotation"][0]}, {obj["rotation"][1]}, {obj["rotation"][2]})
{var_name}.scale = ({obj["scale"][0]}, {obj["scale"][1]}, {obj["scale"][2]})
"""
            elif obj["type"] == "cube":
                script += f"""
# Create {obj["name"]}
bpy.ops.mesh.primitive_cube_add(
    size={obj["properties"].get("size", 2.0)},
    location=({obj["position"][0]}, {obj["position"][1]}, {obj["position"][2]})
)
{var_name} = bpy.context.active_object
{var_name}.rotation_euler = ({obj["rotation"][0]}, {obj["rotation"][1]}, {obj["rotation"][2]})
{var_name}.scale = ({obj["scale"][0]}, {obj["scale"][1]}, {obj["scale"][2]})
"""
            elif obj["type"] == "cylinder":
                script += f"""
# Create {obj["name"]}
bpy.ops.mesh.primitive_cylinder_add(
    radius={obj["properties"].get("radius", 1.0)},
    depth={obj["properties"].get("depth", 2.0)},
    location=({obj["position"][0]}, {obj["position"][1]}, {obj["position"][2]})
)
{var_name} = bpy.context.active_object
{var_name}.rotation_euler = ({obj["rotation"][0]}, {obj["rotation"][1]}, {obj["rotation"][2]})
{var_name}.scale = ({obj["scale"][0]}, {obj["scale"][1]}, {obj["scale"][2]})
"""
            elif obj["type"] == "plane":
                script += f"""
# Create {obj["name"]}
bpy.ops.mesh.primitive_plane_add(
    size={obj["properties"].get("size", 2.0)},
    location=({obj["position"][0]}, {obj["position"][1]}, {obj["position"][2]})
)
{var_name} = bpy.context.active_object
{var_name}.rotation_euler = ({obj["rotation"][0]}, {obj["rotation"][1]}, {obj["rotation"][2]})
{var_name}.scale = ({obj["scale"][0]}, {obj["scale"][1]}, {obj["scale"][2]})
"""
            
            # Add material if present
            if "material" in obj and obj["material"]:
                mat = obj["material"]
                if "color" in mat or "emission" in mat:
                    script += f"""
# Create material for {obj["name"]}
material = bpy.data.materials.new(name="{obj["name"]}_Material")
material.use_nodes = True
nodes = material.node_tree.nodes
links = material.node_tree.links
nodes.clear()
"""
                    
                    if mat.get("emission", False):
                        script += f"""
# Create emission material
node_emission = nodes.new(type='ShaderNodeEmission')
node_emission.inputs[0].default_value = ({mat["color"][0] if "color" in mat else 1.0}, {mat["color"][1] if "color" in mat else 1.0}, {mat["color"][2] if "color" in mat else 1.0}, 1.0)
node_emission.inputs[1].default_value = {mat.get("emissionStrength", 1.0)}
node_output = nodes.new(type='ShaderNodeOutputMaterial')
links.new(node_emission.outputs[0], node_output.inputs[0])
"""
                    else:
                        script += f"""
# Create principled BSDF material
node_bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
node_bsdf.inputs["Base Color"].default_value = ({mat["color"][0] if "color" in mat else 0.8}, {mat["color"][1] if "color" in mat else 0.8}, {mat["color"][2] if "color" in mat else 0.8}, 1.0)
"""
                        if "roughness" in mat:
                            script += f'node_bsdf.inputs["Roughness"].default_value = {mat["roughness"]}\n'
                        
                        if "metallic" in mat:
                            script += f'node_bsdf.inputs["Metallic"].default_value = {mat["metallic"]}\n'
                        
                        script += f"""
node_output = nodes.new(type='ShaderNodeOutputMaterial')
links.new(node_bsdf.outputs[0], node_output.inputs[0])
"""
                    
                    script += f"""
# Assign material to object
if {var_name}.data.materials:
    {var_name}.data.materials[0] = material
else:
    {var_name}.data.materials.append(material)
"""
    
    # Add animations
    for obj in scene_state["objects"]:
        if "animation" in obj and obj["animation"]:
            var_name = obj_var_names.get(obj["id"])
            if not var_name:
                continue
                
            for anim in obj["animation"]:
                script += f"""
# Animation for {obj["name"]} ({anim["property"]})
"""
                if anim["keyframes"]:
                    for keyframe in anim["keyframes"]:
                        frame = keyframe["frame"]
                        value = keyframe["value"]
                        
                        if anim["property"] == "location" or anim["property"] == "position":
                            script += f"""
{var_name}.location = ({value[0]}, {value[1]}, {value[2]})
{var_name}.keyframe_insert(data_path="location", frame={frame})
"""
                        elif anim["property"] == "rotation":
                            script += f"""
{var_name}.rotation_euler = ({value[0]}, {value[1]}, {value[2]})
{var_name}.keyframe_insert(data_path="rotation_euler", frame={frame})
"""
                        elif anim["property"] == "scale":
                            script += f"""
{var_name}.scale = ({value[0]}, {value[1]}, {value[2]})
{var_name}.keyframe_insert(data_path="scale", frame={frame})
"""
                        elif anim["property"] == "color" and "material" in obj:
                            script += f"""
{var_name}.material.node_tree.nodes[0].inputs[0].default_value = ({value[0]}, {value[1]}, {value[2]}, 1.0)
{var_name}.material.node_tree.nodes[0].inputs[0].keyframe_insert(data_path="default_value", frame={frame})
"""
    
    # Add final export code
    script += """
# Export scene to GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)
"""
    
    return script
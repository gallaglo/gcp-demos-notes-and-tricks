import os
import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from script_parser import ScriptParser, generate_script_from_scene_state
from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from prompts import SCENE_MODIFICATION_SYSTEM_PROMPT, SCENE_MODIFICATION_PROMPT
import logging
from functools import lru_cache

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SceneManager:
    """
    Manages scene state persistence and history.
    """
    
    def __init__(self, storage_dir: str = "/tmp/animation_scenes"):
        self.storage_dir = storage_dir
        # Create storage directory if it doesn't exist
        os.makedirs(storage_dir, exist_ok=True)
        # Load existing scenes from storage
        self.thread_scenes = self._load_thread_scenes()
    
    def _load_thread_scenes(self) -> Dict[str, Dict[str, Any]]:
        """Load existing thread scene mappings"""
        thread_scenes = {}
        thread_file = os.path.join(self.storage_dir, "thread_mappings.json")
        
        if os.path.exists(thread_file):
            try:
                with open(thread_file, "r") as f:
                    thread_scenes = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading thread mappings: {e}")
        
        return thread_scenes
    
    def _save_thread_scenes(self):
        """Save thread scene mappings to disk"""
        thread_file = os.path.join(self.storage_dir, "thread_mappings.json")
        
        try:
            with open(thread_file, "w") as f:
                json.dump(self.thread_scenes, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving thread mappings: {e}")
    
    @lru_cache(maxsize=1)
    def get_llm(self, model_name="gemini-2.0-flash-001"):
        """Get an LLM instance with caching to avoid repeated initialization"""
        try:
            llm = ChatVertexAI(
                model_name=model_name,
                temperature=0.2,  # Lower temperature for more deterministic outputs
                max_output_tokens=2048,
                request_timeout=30
            )
            return llm
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {str(e)}")
            raise
    
    def debug_thread_scenes(self):
        """Debug method to print all thread scenes"""
        logger.info(f"Thread mappings: {json.dumps(self.thread_scenes, indent=2)}")
        
    def debug_scene_state(self, scene_id: str):
        """Debug method to print a scene state"""
        scene_file = os.path.join(self.storage_dir, f"{scene_id}.json")
        if os.path.exists(scene_file):
            try:
                with open(scene_file, "r") as f:
                    scene_data = json.load(f)
                    logger.info(f"Scene {scene_id} exists with {len(scene_data.get('objects', []))} objects")
                    return True
            except Exception as e:
                logger.error(f"Error loading scene {scene_id}: {e}")
        else:
            logger.info(f"Scene file does not exist: {scene_file}")
        return False

    def extract_scene_from_script(self, script: str, prompt: str, thread_id: str) -> Dict[str, Any]:
        """
        Parse a Blender script to extract scene state and save it
        
        Args:
            script (str): The Blender Python script
            prompt (str): The prompt that generated the script
            thread_id (str): The thread ID
            
        Returns:
            Dict[str, Any]: The extracted scene state
        """
        logger.info(f"Extracting scene from script for thread {thread_id}")
        
        try:
            # Pre-process the script to fix common issues that cause parsing errors
            fixed_script = self._preprocess_script(script)
            
            # Use the parser to extract scene state
            parser = ScriptParser(fixed_script)
            scene_state = parser.parse()
            
            # Add metadata
            scene_state["description"] = prompt
            scene_state["createdAt"] = datetime.now().isoformat()
            
            # If we have previous scene for this thread, link them
            if thread_id in self.thread_scenes:
                previous_scene_id = self.thread_scenes[thread_id].get("currentSceneId")
                if previous_scene_id:
                    scene_state["derivedFrom"] = previous_scene_id
                    logger.info(f"Linking new scene to previous scene {previous_scene_id}")
            
            # Save the scene state
            self._save_scene_state(scene_state)
            logger.info(f"Saved scene state with ID: {scene_state['id']}")
            
            # Update thread mapping
            if thread_id not in self.thread_scenes:
                logger.info(f"Creating new thread mapping for thread {thread_id}")
                self.thread_scenes[thread_id] = {
                    "threadId": thread_id,
                    "sceneHistory": []
                }
            
            # Add to history if not already there
            if scene_state["id"] not in self.thread_scenes[thread_id].get("sceneHistory", []):
                self.thread_scenes[thread_id]["sceneHistory"] = \
                    self.thread_scenes[thread_id].get("sceneHistory", []) + [scene_state["id"]]
                logger.info(f"Added scene {scene_state['id']} to thread history")
            
            # Update current scene
            self.thread_scenes[thread_id]["currentSceneId"] = scene_state["id"]
            logger.info(f"Set current scene for thread {thread_id} to {scene_state['id']}")
            
            # Save thread mappings
            self._save_thread_scenes()
            logger.info(f"Saved thread mappings")
            
            # Debug: Verify thread mapping was saved correctly
            self.debug_thread_scenes()
            
            return scene_state
            
        except Exception as e:
            error_msg = f"Error extracting scene from script: {str(e)}"
            logger.error(error_msg)
            
            # Create a simple fallback scene if extraction fails
            fallback_scene = {
                "id": str(uuid.uuid4()),
                "objects": [],
                "settings": {
                    "frameStart": 1,
                    "frameEnd": 250,
                    "fps": 25,
                    "backgroundColor": [0.05, 0.05, 0.05]
                },
                "description": prompt,
                "createdAt": datetime.now().isoformat(),
            }
            
            # Save the fallback scene
            self._save_scene_state(fallback_scene)
            logger.info(f"Saved fallback scene with ID: {fallback_scene['id']}")
            
            # Update thread mapping
            if thread_id not in self.thread_scenes:
                logger.info(f"Creating new thread mapping for thread {thread_id}")
                self.thread_scenes[thread_id] = {
                    "threadId": thread_id,
                    "sceneHistory": []
                }
            
            # Add to history
            self.thread_scenes[thread_id]["sceneHistory"] = \
                self.thread_scenes[thread_id].get("sceneHistory", []) + [fallback_scene["id"]]
            
            # Update current scene
            self.thread_scenes[thread_id]["currentSceneId"] = fallback_scene["id"]
            
            # Save thread mappings
            self._save_thread_scenes()
            
            return fallback_scene
        
    def _preprocess_script(self, script: str) -> str:
        """
        Pre-process the script to fix common issues that cause parsing errors
        
        Args:
            script (str): The original Blender script
            
        Returns:
            str: The fixed script
        """
        try:
            # Fix unbalanced parentheses by making sure to replace incomplete function calls
            # This addresses the "unbalanced parenthesis at position 116" error
            
            # Replace incomplete or malformed radians() calls
            script = re.sub(r'radians\s*\([^)]*$', 'radians(0)', script)
            
            # Fix other common issues
            script = script.replace('bpy.context.scene.objects.link(', 'bpy.context.scene.collection.objects.link(')
            script = script.replace('.rotation =', '.rotation_euler =')
            
            # Fix any case where there are three parameters to bpy.data.objects.new
            script = re.sub(
                r'bpy\.data\.objects\.new\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]+)[\'"],\s*([^)]+)\)', 
                r'bpy.data.objects.new("\1", \3)', 
                script
            )
            
            return script
        except Exception as e:
            logger.error(f"Error preprocessing script: {str(e)}")
            return script  # Return original script if preprocessing fails
    
    def _save_scene_state(self, scene_state: Dict[str, Any]):
        """Save a scene state to disk"""
        scene_file = os.path.join(self.storage_dir, f"{scene_state['id']}.json")
        
        try:
            with open(scene_file, "w") as f:
                json.dump(scene_state, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving scene state: {e}")
    
    def get_scene_state(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get a scene state by ID"""
        scene_file = os.path.join(self.storage_dir, f"{scene_id}.json")
        
        if os.path.exists(scene_file):
            try:
                with open(scene_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading scene state: {e}")
        
        return None
    
    def get_current_scene_for_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get the current scene state for a thread"""
        logger.info(f"Looking for scene for thread {thread_id}")
        logger.info(f"Available threads: {list(self.thread_scenes.keys())}")
        
        if thread_id not in self.thread_scenes:
            logger.info(f"Thread {thread_id} not found in thread_scenes")
            return None
        
        scene_id = self.thread_scenes[thread_id].get("currentSceneId")
        if not scene_id:
            logger.info(f"No currentSceneId for thread {thread_id}")
            return None
        
        logger.info(f"Found currentSceneId {scene_id} for thread {thread_id}")
        scene_state = self.get_scene_state(scene_id)
        
        if scene_state:
            logger.info(f"Successfully retrieved scene state for {scene_id}")
        else:
            logger.info(f"Failed to get scene state for {scene_id}")
        
        return scene_state
    
    def get_thread_scene_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get the scene history for a thread"""
        if thread_id not in self.thread_scenes:
            return []
        
        scene_ids = self.thread_scenes[thread_id].get("sceneHistory", [])
        scene_states = []
        
        for scene_id in scene_ids:
            scene_state = self.get_scene_state(scene_id)
            if scene_state:
                scene_states.append(scene_state)
        
        return scene_states
    
    def generate_script_with_modifications(self, 
                                          thread_id: str, 
                                          prompt: str, 
                                          object_changes: Optional[Dict[str, Any]] = None,
                                          add_objects: Optional[List[Dict[str, Any]]] = None,
                                          remove_object_ids: Optional[List[str]] = None) -> str:
        """
        Generate a script based on the current scene with specified modifications
        
        Args:
            thread_id (str): The thread ID
            prompt (str): The new prompt
            object_changes (Dict[str, Any], optional): Changes to existing objects
            add_objects (List[Dict[str, Any]], optional): New objects to add
            remove_object_ids (List[str], optional): IDs of objects to remove
            
        Returns:
            str: The generated Blender script
        """
        # Get the current scene state
        current_scene = self.get_current_scene_for_thread(thread_id)
        if not current_scene:
            # No existing scene, return empty string to generate from scratch
            logger.error(f"No existing scene found for thread {thread_id}")
            return ""
        
        try:
            # Create a modified copy of the scene
            modified_scene = dict(current_scene)
            modified_scene["id"] = str(uuid.uuid4())  # New ID
            modified_scene["description"] = prompt
            modified_scene["createdAt"] = datetime.now().isoformat()
            modified_scene["derivedFrom"] = current_scene.get("id", "")
            
            # Initialize objects array if it doesn't exist
            if "objects" not in modified_scene:
                modified_scene["objects"] = []
                
            # Make sure all required fields exist
            if "settings" not in modified_scene:
                modified_scene["settings"] = {
                    "frameStart": 1,
                    "frameEnd": 250,
                    "fps": 25,
                    "backgroundColor": [0.05, 0.05, 0.05]
                }
                
            # Make the requested modifications
            if object_changes:
                self._apply_object_changes(modified_scene, object_changes)
            
            if remove_object_ids:
                self._remove_objects(modified_scene, remove_object_ids)
            
            if add_objects:
                # Check that each add_object has an ID, otherwise generate one
                for obj in add_objects:
                    if "id" not in obj or not obj["id"]:
                        obj["id"] = str(uuid.uuid4())
                        
                    # Ensure other required fields exist
                    if "position" not in obj:
                        obj["position"] = [0, 0, 0]
                    if "rotation" not in obj:
                        obj["rotation"] = [0, 0, 0]
                    if "scale" not in obj:
                        obj["scale"] = [1, 1, 1]
                        
                self._add_objects(modified_scene, add_objects)
            
            # Generate a script from the modified scene
            logger.info(f"Generating script for modified scene with {len(modified_scene.get('objects', []))} objects")
            return generate_script_from_scene_state(modified_scene)
            
        except Exception as e:
            logger.error(f"Error generating script with modifications: {str(e)}")
            # Return empty string to fall back to default script generation
            return ""
            
    def _apply_object_changes(self, scene: Dict[str, Any], changes: Dict[str, Any]):
        """Apply changes to objects in the scene"""
        try:
            # Ensure objects exist
            if "objects" not in scene:
                scene["objects"] = []
                return
                
            for obj_id, obj_changes in changes.items():
                # Find the object
                found = False
                for i, obj in enumerate(scene["objects"]):
                    if obj.get("id") == obj_id:
                        found = True
                        # Apply changes
                        for key, value in obj_changes.items():
                            if key in ["position", "rotation", "scale", "material", "properties"]:
                                if isinstance(value, dict) and isinstance(obj.get(key, {}), dict):
                                    # Merge dictionaries for nested properties
                                    obj[key] = {**obj.get(key, {}), **value}
                                else:
                                    obj[key] = value
                        break
                        
                # Log if object wasn't found
                if not found:
                    logger.warning(f"Object with ID {obj_id} not found in scene when applying changes")
        except Exception as e:
            logger.error(f"Error applying object changes: {str(e)}")

    def _remove_objects(self, scene: Dict[str, Any], object_ids: List[str]):
        """Remove objects from the scene"""
        try:
            # Ensure objects exist
            if "objects" not in scene:
                scene["objects"] = []
                return
                
            scene["objects"] = [obj for obj in scene["objects"] if obj.get("id") not in object_ids]
        except Exception as e:
            logger.error(f"Error removing objects: {str(e)}")

    def _add_objects(self, scene: Dict[str, Any], new_objects: List[Dict[str, Any]]):
        """Add new objects to the scene"""
        try:
            # Ensure objects exist
            if "objects" not in scene:
                scene["objects"] = []
                
            # Make sure each object has the required fields
            for obj in new_objects:
                # Generate an ID if missing
                if "id" not in obj or not obj["id"]:
                    obj["id"] = str(uuid.uuid4())
                    
                # Add default values for required fields if missing
                if "name" not in obj:
                    obj["name"] = f"Object_{obj['id'][:8]}"
                if "type" not in obj:
                    obj["type"] = "sphere"  # Default type
                if "position" not in obj:
                    obj["position"] = [0, 0, 0]
                if "rotation" not in obj:
                    obj["rotation"] = [0, 0, 0]
                if "scale" not in obj:
                    obj["scale"] = [1, 1, 1]
                    
                # Add properties based on type if missing
                if "properties" not in obj:
                    if obj["type"] == "sphere":
                        obj["properties"] = {"radius": 1.0}
                    elif obj["type"] == "cube":
                        obj["properties"] = {"size": 2.0}
                    elif obj["type"] == "cylinder":
                        obj["properties"] = {"radius": 1.0, "depth": 2.0}
                    elif obj["type"] == "plane":
                        obj["properties"] = {"size": 5.0}
                
            scene["objects"].extend(new_objects)
            logger.info(f"Added {len(new_objects)} new objects to scene")
        except Exception as e:
            logger.error(f"Error adding objects: {str(e)}")
    
    def update_scene_with_signed_url(self, scene_id: str, signed_url: str):
        """Update a scene with its GLB URL"""
        try:
            scene_state = self.get_scene_state(scene_id)
            if scene_state:
                scene_state["glbUrl"] = signed_url
                self._save_scene_state(scene_state)
                logger.info(f"Updated scene {scene_id} with signed URL")
            else:
                logger.warning(f"Could not find scene {scene_id} to update with signed URL")
        except Exception as e:
            logger.error(f"Error updating scene with signed URL: {str(e)}")
    
    def _generate_object_description(self, obj: Dict[str, Any]) -> str:
        """Generate a human-readable description of an object"""
        obj_type = obj.get("type", "unknown")
        obj_name = obj.get("name", "Unnamed")
        position = obj.get("position", [0, 0, 0])
        
        # Format position values with 2 decimal places
        pos_formatted = [f"{p:.2f}" for p in position]
        
        # Get material color if available
        color_desc = ""
        if "material" in obj and "color" in obj["material"]:
            color = obj["material"]["color"]
            # Try to determine a human-readable color name
            color_name = self._get_color_name(color)
            color_desc = f", {color_name} color"
        
        # Get any special properties based on object type
        props_desc = ""
        if obj_type == "sphere" and "properties" in obj and "radius" in obj["properties"]:
            props_desc = f", radius {obj['properties']['radius']:.2f}"
        elif obj_type == "cube" and "properties" in obj and "size" in obj["properties"]:
            props_desc = f", size {obj['properties']['size']:.2f}"
        
        return f"{obj_name}: {obj_type} at position [{', '.join(pos_formatted)}]{color_desc}{props_desc}"
    
    def _get_color_name(self, rgb: List[float]) -> str:
        """Convert RGB values to an approximate color name"""
        # Simple color name mapping based on RGB values
        if len(rgb) < 3:
            return "unknown color"
            
        r, g, b = rgb[:3]
        
        # Define some basic color thresholds
        if r > 0.7 and g < 0.3 and b < 0.3:
            return "red"
        elif r < 0.3 and g > 0.7 and b < 0.3:
            return "green"
        elif r < 0.3 and g < 0.3 and b > 0.7:
            return "blue"
        elif r > 0.7 and g > 0.7 and b < 0.3:
            return "yellow"
        elif r > 0.7 and g < 0.3 and b > 0.7:
            return "magenta"
        elif r < 0.3 and g > 0.7 and b > 0.7:
            return "cyan"
        elif r > 0.7 and g > 0.3 and b > 0.3:
            return "pink"
        elif r > 0.7 and g > 0.5 and b > 0.0:
            return "orange"
        elif r > 0.8 and g > 0.8 and b > 0.8:
            return "white"
        elif r < 0.2 and g < 0.2 and b < 0.2:
            return "black"
        else:
            return "gray"
    
    def analyze_modification_prompt(self, prompt: str, scene_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a modification prompt to determine object-specific changes using LLM
        
        Args:
            prompt (str): The modification prompt
            scene_state (Dict[str, Any]): The current scene state
            
        Returns:
            Dict[str, Any]: The parsed modification instructions
        """
        try:
            # Get LLM
            llm = self.get_llm()
            
            # Prepare scene information for the prompt
            scene_objects = []
            for obj in scene_state.get("objects", []):
                if obj.get("type") not in ["camera", "light"]:  # Skip cameras and lights in the description
                    scene_objects.append(self._generate_object_description(obj))
            
            scene_description = scene_state.get("description", "3D scene")
            
            # Get the system prompt from prompts.py
            system_prompt = SCENE_MODIFICATION_SYSTEM_PROMPT
            
            # Format object descriptions as a string
            object_descriptions_str = ""
            for i, obj_desc in enumerate(scene_objects, 1):
                object_descriptions_str += f"{i}. {obj_desc}\n"
            
            # Use the template from prompts.py to format the human message
            human_prompt = SCENE_MODIFICATION_PROMPT.format(
                scene_description=scene_description,
                object_descriptions=object_descriptions_str,
                prompt=prompt
            )
            
            # Create messages for the LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            # Get response from LLM
            response = llm.invoke(messages)
            response_text = response.content.strip()
            
            # Extract JSON from the response
            json_text = response_text
            if "```json" in response_text:
                json_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse the JSON
            try:
                changes = json.loads(json_text)
                logger.info(f"Parsed modification request: {json.dumps(changes, indent=2)}")
                
                # Map the object descriptions back to actual object IDs
                processed_changes = self._map_objects_to_ids(changes, scene_state)
                return processed_changes
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing LLM response as JSON: {e}")
                logger.error(f"Raw response: {response_text}")
                return self._fallback_analysis(prompt, scene_state)
                
        except Exception as e:
            logger.error(f"Error in LLM-based modification analysis: {e}")
            # Use fallback method
            return self._fallback_analysis(prompt, scene_state)
    
    def _map_objects_to_ids(self, changes: Dict[str, Any], scene_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map the object changes from LLM to actual object IDs in the scene
        
        Args:
            changes (Dict[str, Any]): The changes from the LLM
            scene_state (Dict[str, Any]): The current scene state
            
        Returns:
            Dict[str, Any]: The mapped changes
        """
        # Initialize the result with the original changes
        result = {
            "object_changes": {},
            "add_objects": changes.get("add_objects", []),
            "remove_object_ids": []
        }
        
        # Get the scene objects with their IDs
        scene_objects = {obj.get("name", ""): obj for obj in scene_state.get("objects", [])}
        
        # Map object changes
        for obj_ref, obj_changes in changes.get("object_changes", {}).items():
            # If the key is already a valid ID in the scene, use it directly
            found = False
            for obj in scene_state.get("objects", []):
                if obj.get("id") == obj_ref:
                    result["object_changes"][obj_ref] = obj_changes
                    found = True
                    break
            
            if not found:
                # Try to match by name
                for obj_name, obj in scene_objects.items():
                    # Check if the name is in the reference or vice versa
                    if obj_name.lower() in obj_ref.lower() or obj_ref.lower() in obj_name.lower():
                        result["object_changes"][obj.get("id")] = obj_changes
                        break
        
        # Map object removals
        for obj_ref in changes.get("remove_object_ids", []):
            # If the reference is already a valid ID in the scene, use it directly
            found = False
            for obj in scene_state.get("objects", []):
                if obj.get("id") == obj_ref:
                    result["remove_object_ids"].append(obj_ref)
                    found = True
                    break
            
            if not found:
                # Try to match by name
                for obj_name, obj in scene_objects.items():
                    # Check if the name is in the reference or vice versa
                    if obj_name.lower() in obj_ref.lower() or obj_ref.lower() in obj_name.lower():
                        result["remove_object_ids"].append(obj.get("id"))
                        break
        
        return result
    
    def _fallback_analysis(self, prompt: str, scene_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback method for analyzing modification prompts when LLM fails
        
        Args:
            prompt (str): The modification prompt
            scene_state (Dict[str, Any]): The current scene state
            
        Returns:
            Dict[str, Any]: Simple modification instructions
        """
        logger.warning("Using fallback analysis for modification prompt")
        
        # Initialize result
        changes = {
            "object_changes": {},
            "add_objects": [],
            "remove_object_ids": []
        }
        
        # Simple keyword-based parsing
        prompt_lower = prompt.lower()
        
        # Check for color changes
        color_mapping = {
            "red": [1.0, 0.0, 0.0],
            "green": [0.0, 1.0, 0.0],
            "blue": [0.0, 0.0, 1.0],
            "yellow": [1.0, 1.0, 0.0],
            "magenta": [1.0, 0.0, 1.0],
            "cyan": [0.0, 1.0, 1.0],
            "white": [1.0, 1.0, 1.0],
            "black": [0.0, 0.0, 0.0],
            "orange": [1.0, 0.5, 0.0],
            "purple": [0.5, 0.0, 0.5],
            "pink": [1.0, 0.5, 0.5]
        }
        
        # Look for color keywords
        color_value = None
        for color_name, rgb in color_mapping.items():
            if color_name in prompt_lower:
                color_value = rgb
                break
        
        # Look for objects mentioned by name
        for obj in scene_state.get("objects", []):
            obj_name = obj.get("name", "").lower()
            obj_type = obj.get("type", "").lower()
            
            # Skip cameras and lights
            if obj_type in ["camera", "light"]:
                continue
            
            # Check if this object is mentioned in the prompt
            if obj_name in prompt_lower or obj_type in prompt_lower:
                obj_changes = {}
                
                # Check for move/position changes
                if any(word in prompt_lower for word in ["move", "position", "translate"]):
                    # Simple move in +X direction
                    current_pos = obj.get("position", [0, 0, 0])
                    obj_changes["position"] = [current_pos[0] + 2, current_pos[1], current_pos[2]]
                
                # Check for rotation
                if any(word in prompt_lower for word in ["rotate", "rotation", "turn"]):
                    # Simple rotation around Y
                    current_rot = obj.get("rotation", [0, 0, 0])
                    obj_changes["rotation"] = [current_rot[0], current_rot[1] + 0.5, current_rot[2]]
                
                # Check for scale
                if any(word in prompt_lower for word in ["scale", "size", "bigger", "smaller"]):
                    scale_factor = 1.5 if "bigger" in prompt_lower else 0.75
                    current_scale = obj.get("scale", [1, 1, 1])
                    obj_changes["scale"] = [s * scale_factor for s in current_scale]
                
                # Check for color
                if color_value and any(word in prompt_lower for word in ["color", "paint"]):
                    obj_changes["material"] = {"color": color_value}
                
                # Add to changes if any modifications were found
                if obj_changes:
                    changes["object_changes"][obj.get("id")] = obj_changes
                
                # Check for removal
                if any(word in prompt_lower for word in ["remove", "delete", "eliminate"]):
                    changes["remove_object_ids"].append(obj.get("id"))
        
        # Check for adding objects
        if "add" in prompt_lower:
            new_obj = None
            # Try to determine object type
            if "sphere" in prompt_lower:
                new_obj = {
                    "id": f"new_sphere_{int(time.time())}",
                    "name": "New Sphere",
                    "type": "sphere",
                    "position": [0, 0, 2],
                    "rotation": [0, 0, 0],
                    "scale": [1, 1, 1],
                    "properties": {"radius": 1.0}
                }
            elif "cube" in prompt_lower:
                new_obj = {
                    "id": f"new_cube_{int(time.time())}",
                    "name": "New Cube",
                    "type": "cube",
                    "position": [0, 0, 2],
                    "rotation": [0, 0, 0],
                    "scale": [1, 1, 1],
                    "properties": {"size": 2.0}
                }
            elif "cylinder" in prompt_lower:
                new_obj = {
                    "id": f"new_cylinder_{int(time.time())}",
                    "name": "New Cylinder",
                    "type": "cylinder",
                    "position": [0, 0, 2],
                    "rotation": [0, 0, 0],
                    "scale": [1, 1, 1],
                    "properties": {"radius": 1.0, "depth": 2.0}
                }
            elif "plane" in prompt_lower:
                new_obj = {
                    "id": f"new_plane_{int(time.time())}",
                    "name": "New Plane",
                    "type": "plane",
                    "position": [0, 0, 0],
                    "rotation": [0, 0, 0],
                    "scale": [1, 1, 1],
                    "properties": {"size": 5.0}
                }
            
            # If we found an object type and there's a color, apply it
            if new_obj and color_value:
                new_obj["material"] = {"color": color_value}
            
            # Add to the list of objects to add
            if new_obj:
                changes["add_objects"].append(new_obj)
        
        return changes
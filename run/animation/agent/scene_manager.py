import os
import json
import time
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
    def get_llm(self, model_name="gemini-2.0-pro-001"):
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
        parser = ScriptParser(script)
        scene_state = parser.parse()
        
        # Add metadata
        scene_state["description"] = prompt
        scene_state["createdAt"] = datetime.now().isoformat()
        
        # If we have previous scene for this thread, link them
        if thread_id in self.thread_scenes:
            previous_scene_id = self.thread_scenes[thread_id].get("currentSceneId")
            if previous_scene_id:
                scene_state["derivedFrom"] = previous_scene_id
        
        # Save the scene state
        self._save_scene_state(scene_state)
        
        # Update thread mapping
        if thread_id not in self.thread_scenes:
            self.thread_scenes[thread_id] = {
                "threadId": thread_id,
                "sceneHistory": []
            }
        
        # Add to history if not already there
        if scene_state["id"] not in self.thread_scenes[thread_id].get("sceneHistory", []):
            self.thread_scenes[thread_id]["sceneHistory"] = \
                self.thread_scenes[thread_id].get("sceneHistory", []) + [scene_state["id"]]
        
        # Update current scene
        self.thread_scenes[thread_id]["currentSceneId"] = scene_state["id"]
        
        # Save thread mappings
        self._save_thread_scenes()
        
        return scene_state
    
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
        if thread_id not in self.thread_scenes:
            return None
        
        scene_id = self.thread_scenes[thread_id].get("currentSceneId")
        if not scene_id:
            return None
        
        return self.get_scene_state(scene_id)
    
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
            return ""
        
        # Create a modified copy of the scene
        modified_scene = dict(current_scene)
        modified_scene["id"] = f"modified_{int(time.time())}"  # New ID
        modified_scene["description"] = prompt
        modified_scene["createdAt"] = datetime.now().isoformat()
        modified_scene["derivedFrom"] = current_scene["id"]
        
        # Make the requested modifications
        if object_changes:
            self._apply_object_changes(modified_scene, object_changes)
        
        if remove_object_ids:
            self._remove_objects(modified_scene, remove_object_ids)
        
        if add_objects:
            self._add_objects(modified_scene, add_objects)
        
        # Generate a script from the modified scene
        return generate_script_from_scene_state(modified_scene)
    
    def _apply_object_changes(self, scene: Dict[str, Any], changes: Dict[str, Any]):
        """Apply changes to objects in the scene"""
        for obj_id, obj_changes in changes.items():
            # Find the object
            for i, obj in enumerate(scene["objects"]):
                if obj["id"] == obj_id:
                    # Apply changes
                    for key, value in obj_changes.items():
                        if key in ["position", "rotation", "scale", "material", "properties"]:
                            if isinstance(value, dict) and isinstance(obj.get(key, {}), dict):
                                # Merge dictionaries for nested properties
                                obj[key] = {**obj.get(key, {}), **value}
                            else:
                                obj[key] = value
                    break
    
    def _remove_objects(self, scene: Dict[str, Any], object_ids: List[str]):
        """Remove objects from the scene"""
        scene["objects"] = [obj for obj in scene["objects"] if obj["id"] not in object_ids]
    
    def _add_objects(self, scene: Dict[str, Any], new_objects: List[Dict[str, Any]]):
        """Add new objects to the scene"""
        scene["objects"].extend(new_objects)
    
    def update_scene_with_signed_url(self, scene_id: str, signed_url: str):
        """Update a scene with its GLB URL"""
        scene_state = self.get_scene_state(scene_id)
        if scene_state:
            scene_state["glbUrl"] = signed_url
            self._save_scene_state(scene_state)
    
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
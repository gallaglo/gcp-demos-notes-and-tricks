import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from script_parser import ScriptParser, generate_script_from_scene_state

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
                print(f"Error loading thread mappings: {e}")
        
        return thread_scenes
    
    def _save_thread_scenes(self):
        """Save thread scene mappings to disk"""
        thread_file = os.path.join(self.storage_dir, "thread_mappings.json")
        
        try:
            with open(thread_file, "w") as f:
                json.dump(self.thread_scenes, f, indent=2)
        except IOError as e:
            print(f"Error saving thread mappings: {e}")
    
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
            print(f"Error saving scene state: {e}")
    
    def get_scene_state(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Get a scene state by ID"""
        scene_file = os.path.join(self.storage_dir, f"{scene_id}.json")
        
        if os.path.exists(scene_file):
            try:
                with open(scene_file, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading scene state: {e}")
        
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
    
    def analyze_modification_prompt(self, prompt: str, scene_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a modification prompt to determine object-specific changes
        
        Args:
            prompt (str): The modification prompt
            scene_state (Dict[str, Any]): The current scene state
            
        Returns:
            Dict[str, Any]: The parsed modification instructions
        """
        # TODO: In real implementation, this would use LLM to parse the prompt
        # and identify specific objects and modifications
        
        # Simple parsing logic for demo purposes
        changes = {
            "object_changes": {},
            "add_objects": [],
            "remove_object_ids": []
        }
        
        # Just a placeholder for now - in reality this would use LLM to
        # understand the user's intent and map it to specific scene objects
        if "move" in prompt.lower() or "position" in prompt.lower():
            for obj in scene_state["objects"]:
                if obj["type"] in ["sphere", "cube", "cylinder"] and obj["name"].lower() in prompt.lower():
                    changes["object_changes"][obj["id"]] = {
                        "position": [obj["position"][0] + 2, obj["position"][1], obj["position"][2]]
                    }
        
        if "rotate" in prompt.lower():
            for obj in scene_state["objects"]:
                if obj["name"].lower() in prompt.lower():
                    changes["object_changes"][obj["id"]] = {
                        "rotation": [obj["rotation"][0] + 0.5, obj["rotation"][1], obj["rotation"][2]]
                    }
        
        if "color" in prompt.lower() or "red" in prompt.lower():
            for obj in scene_state["objects"]:
                if obj["name"].lower() in prompt.lower():
                    changes["object_changes"][obj["id"]] = {
                        "material": {"color": [1.0, 0.0, 0.0]}
                    }
        
        if "add" in prompt.lower() and "sphere" in prompt.lower():
            changes["add_objects"].append({
                "id": f"new_sphere_{int(time.time())}",
                "name": "New Sphere",
                "type": "sphere",
                "position": [0, 0, 2],
                "rotation": [0, 0, 0],
                "scale": [1, 1, 1],
                "properties": {"radius": 1.0}
            })
        
        if "remove" in prompt.lower() or "delete" in prompt.lower():
            for obj in scene_state["objects"]:
                if obj["name"].lower() in prompt.lower():
                    changes["remove_object_ids"].append(obj["id"])
        
        return changes
import os
import json
import requests
from typing import TypedDict, Dict, Any, List, Optional, Union
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from prompts import BLENDER_PROMPT, CHAT_SYSTEM_PROMPT, EDIT_ANALYSIS_PROMPT
import logging
from functools import lru_cache
from dotenv import load_dotenv
from scene_manager import SceneManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BLENDER_SERVICE_URL = os.environ.get("BLENDER_SERVICE_URL")
if not BLENDER_SERVICE_URL:
    raise ValueError("BLENDER_SERVICE_URL environment variable is not set")

# Initialize scene manager
scene_manager = SceneManager()

# Type definitions
class Message(TypedDict):
    role: str  # 'human' or 'ai'
    content: str

class AnimationState(TypedDict):
    prompt: str
    blender_script: str
    generation_status: str
    signed_url: str
    error: str
    history: List[Message]
    current_prompt: str
    thread_id: str  # New field for thread tracking
    scene_state: Dict[str, Any]  # New field for scene state
    is_modification: bool  # Flag to indicate if this is modifying an existing scene
    object_changes: Dict[str, Any]  # Object changes for modifications

def get_id_token(audience: str) -> str:
    """Gets an ID token for authentication with Cloud Run."""
    try:
        # Get ID token for Cloud Run service
        request = Request()
        token = id_token.fetch_id_token(request, audience)
        return token
    except Exception as e:
        logger.error(f"Error getting ID token: {str(e)}")
        raise

@lru_cache()
def get_llm(model_name="gemini-2.0-flash-001"):
    """Creates the LLM instance using cached configuration"""
    try:
        llm = ChatVertexAI(
            model_name=model_name,
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=4096,
            request_timeout=60,
            max_retries=3
        )
        logger.info(f"Successfully initialized LLM: {model_name}")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {str(e)}")
        raise

def analyze_prompt(state: AnimationState) -> AnimationState:
    """
    Analyze the user prompt to determine if it requires animation generation,
    modification of an existing animation, or just a conversational response.
    """
    try:
        # Get LLM for analysis
        llm = get_llm()
        
        # Create the message history for context
        messages = [
            SystemMessage(content=CHAT_SYSTEM_PROMPT),
        ]
        
        # Add conversation history
        for msg in state["history"]:
            if msg["role"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Get the current scene state for this thread if it exists
        current_scene = None
        if state.get("thread_id"):
            current_scene = scene_manager.get_current_scene_for_thread(state["thread_id"])
        
        # Modify the analysis prompt based on whether there's an existing scene
        if current_scene:
            # Prepare scene description for the prompt
            scene_desc = f"""
            Current scene description: {current_scene['description']}
            
            Scene contains:
            """
            
            # Group objects by type for a cleaner description
            obj_types = {}
            for obj in current_scene["objects"]:
                obj_type = obj["type"]
                if obj_type not in obj_types:
                    obj_types[obj_type] = []
                obj_types[obj_type].append(obj["name"])
            
            # Add object descriptions
            for obj_type, names in obj_types.items():
                scene_desc += f"- {len(names)} {obj_type}(s): {', '.join(names)}\n"
            
            analysis_prompt = f"""
            I need to determine if the user is requesting a modification to the existing 3D animation,
            asking for a completely new animation, or just having a conversation.
            
            {scene_desc}
            
            User message: "{state['current_prompt']}"
            
            If the user is asking for a modification to the existing animation (changing colors, moving objects, 
            adding/removing objects, changing animation, etc.), respond with:
            "MODIFY_ANIMATION: <brief description of the modification>"
            
            If the user is requesting a completely new animation unrelated to the current one, respond with:
            "GENERATE_ANIMATION: <brief description of what to animate>"
            
            If the user is just having a conversation, asking a question, or not requesting any visual content,
            respond with "CONVERSATION: <your conversational response to the user>"
            
            Only respond with one of these formats. Don't add any explanation.
            """
        else:
            # No existing scene, use the standard prompt
            analysis_prompt = f"""
            I need to determine if the following user message is requesting a 3D animation to be generated or if it's just regular conversation.
            
            User message: "{state['current_prompt']}"
            
            If the user is clearly requesting a 3D animation, visual content, or mentioning objects, scenes or animations
            respond with "GENERATE_ANIMATION: <brief description of what to animate>".
            
            If the user is just having a conversation, asking a general question, or not requesting any visual content,
            respond with "CONVERSATION: <your conversational response to the user>".
            
            Only respond with one of these formats. Don't add any explanation.
            """
        
        messages.append(HumanMessage(content=analysis_prompt))
        
        # Get response
        response = llm.invoke(messages)
        analysis = response.content.strip()
        
        logger.info(f"Prompt analysis: {analysis}")
        
        # Update state based on analysis
        if analysis.startswith("GENERATE_ANIMATION:"):
            return {
                **state,
                "prompt": state["current_prompt"],
                "generation_status": "analyzing",
                "is_modification": False
            }
        elif analysis.startswith("MODIFY_ANIMATION:"):
            # Handle modification request
            if current_scene:
                return {
                    **state,
                    "prompt": state["current_prompt"],
                    "generation_status": "analyzing_modification",
                    "is_modification": True,
                    "scene_state": current_scene
                }
            else:
                # Fall back to generating a new animation if there's no existing scene
                return {
                    **state,
                    "prompt": state["current_prompt"],
                    "generation_status": "analyzing",
                    "is_modification": False
                }
        elif analysis.startswith("CONVERSATION:"):
            # Extract conversation response (everything after "CONVERSATION:")
            conversation_response = analysis[len("CONVERSATION:"):].strip()
            
            # Update history with the AI response
            updated_history = state["history"] + [
                {"role": "ai", "content": conversation_response}
            ]
            
            return {
                **state,
                "generation_status": "conversation_only",
                "history": updated_history
            }
        else:
            # Default to conversation if analysis is unclear
            return {
                **state,
                "generation_status": "conversation_only",
                "history": state["history"] + [
                    {"role": "ai", "content": "I'm not sure if you're asking for an animation. Could you clarify what you'd like me to help you with?"}
                ]
            }
            
    except Exception as e:
        logger.error(f"Prompt analysis error: {str(e)}")
        return {
            **state,
            "error": f"Failed to analyze prompt: {str(e)}",
            "generation_status": "error"
        }

def analyze_modification_request(state: AnimationState) -> AnimationState:
    """
    Analyze a modification request to determine specific changes to objects.
    """
    try:
        # We need a scene state to modify
        if not state.get("scene_state"):
            return {
                **state,
                "error": "No existing scene to modify",
                "generation_status": "error"
            }
        
        llm = get_llm()
        
        # Prepare the scene description
        scene_desc = json.dumps(state["scene_state"], indent=2)
        
        # Create a prompt for analyzing the modification request
        messages = [
            SystemMessage(content=EDIT_ANALYSIS_PROMPT),
            HumanMessage(content=f"""
            User's modification request: "{state['prompt']}"
            
            Current scene state (JSON):
            ```
            {scene_desc}
            ```
            
            Based on the user's request, identify which objects need to be modified and how.
            Follow the output format instructions exactly.
            """)
        ]
        
        # Get response
        response = llm.invoke(messages)
        analysis = response.content.strip()
        
        logger.info(f"Modification analysis: {analysis}")
        
        # Try to parse the response as JSON
        try:
            # Extract the JSON part if wrapped in ```json or ```
            if "```json" in analysis:
                json_text = analysis.split("```json")[1].split("```")[0]
            elif "```" in analysis:
                json_text = analysis.split("```")[1].split("```")[0]
            else:
                json_text = analysis
                
            # Parse the changes
            object_changes = json.loads(json_text)
            
            return {
                **state,
                "object_changes": object_changes,
                "generation_status": "modification_analyzed"
            }
        except (json.JSONDecodeError, IndexError) as json_err:
            logger.error(f"Error parsing modification JSON: {str(json_err)}")
            logger.error(f"Raw response: {analysis}")
            
            # Fall back to simple analysis
            simple_changes = scene_manager.analyze_modification_prompt(
                state["prompt"], 
                state["scene_state"]
            )
            
            return {
                **state,
                "object_changes": simple_changes,
                "generation_status": "modification_analyzed"
            }
            
    except Exception as e:
        logger.error(f"Modification analysis error: {str(e)}")
        return {
            **state,
            "error": f"Failed to analyze modification: {str(e)}",
            "generation_status": "error"
        }

class BlenderScriptGenerator:
    def generate(self, prompt: str, history: Optional[List[Message]] = None) -> str:
        """
        Generate a Blender Python script from a text prompt.
        
        Args:
            prompt (str): Text description of the animation to create
            history (List[Message], optional): Conversation history for context
            
        Returns:
            str: Python script for Blender
        """
        try:
            logger.info("Sending prompt to LLM")
            llm = get_llm()
            
            # Use the LangChain prompt template
            formatted_prompt = BLENDER_PROMPT.format(user_prompt=prompt)
            response = llm.invoke(formatted_prompt)
            
            # Extract content from AIMessage
            if hasattr(response, 'content'):
                raw_content = response.content
            else:
                raw_content = str(response)
            
            # Extract script from between triple backticks
            if '```python' in raw_content and '```' in raw_content:
                script = raw_content.split('```python')[1].split('```')[0].strip()
            else:
                script = raw_content.strip()
                
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

    def _fix_common_script_issues(self, script: str) -> str:
        """
        Fix common issues in generated Blender scripts.
        
        Args:
            script (str): The original Blender script
        
        Returns:
            str: The corrected script
        """
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
        import re
        pattern = r'bpy\.data\.objects\.new\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]+)[\'"],\s*([^)]+)\)'
        replacement = r'bpy.data.objects.new("\1", \3)'
        script = re.sub(pattern, replacement, script)
        
        return script

    def _modify_script_for_output_path(self, script: str) -> str:
        """
        Ensure the script has proper command-line argument handling for output path.
        
        Args:
            script (str): The original script
            
        Returns:
            str: Script with proper output path handling
        """
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
        """
        Validates the generated script contains required components and no forbidden terms.
        
        Args:
            script (str): The Blender script to validate
            
        Raises:
            ValueError: If the script fails validation
        """
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
            import re
            pattern = r'bpy\.data\.objects\.new\([\'"][^\'"]+[\'"],\s*[\'"][^\'"]+[\'"],\s*[^)]+\)'
            matches = re.findall(pattern, script)
            if matches:
                raise ValueError('Incorrect object creation syntax: too many arguments in bpy.data.objects.new()')
# animation_graph.py
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
from prompts import BLENDER_PROMPT, CHAT_SYSTEM_PROMPT
import logging
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BLENDER_SERVICE_URL = os.environ.get("BLENDER_SERVICE_URL")
if not BLENDER_SERVICE_URL:
    raise ValueError("BLENDER_SERVICE_URL environment variable is not set")

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
def get_llm():
    """Creates the LLM instance using cached configuration"""
    try:
        llm = ChatVertexAI(
            model_name="gemini-2.0-flash-001",  # Using Flash model
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=4096,
            request_timeout=60,
            max_retries=3
        )
        logger.info("Successfully initialized LLM")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {str(e)}")
        raise

def analyze_prompt(state: AnimationState) -> AnimationState:
    """
    Analyze the user prompt to determine if it requires animation generation 
    or just a conversational response.
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
        
        # Add analysis request
        analysis_prompt = f"""
        I need to determine if the following user message is requesting a 3D animation to be generated or if it's just regular conversation.
        
        User message: "{state['current_prompt']}"
        
        If the user is clearly requesting a 3D animation, visual content, or mentioning objects, scenes or animations
        respond with "GENERATE_ANIMATION: <brief description of what to animate>".
        
        If the user is asking a question about a previous animation, wants modification to an existing animation,
        or is referring to a previous animation, respond with "MODIFY_ANIMATION: <brief description of the modification>".
        
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
                "generation_status": "analyzing"
            }
        elif analysis.startswith("MODIFY_ANIMATION:"):
            # For simplicity, we'll treat modifications like new generations for now
            return {
                **state,
                "prompt": state["current_prompt"],
                "generation_status": "analyzing"
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
            
            # Validate script has required components
            self._validate_script_requirements(script)
            
            # Add the command-line argument handling to ensure proper output path
            script = self._modify_script_for_output_path(script)
            
            return script
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise ValueError(f"Failed to generate script: {str(e)}")

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

# Create script generator instance
script_generator = BlenderScriptGenerator()

def generate_blender_script(state: AnimationState) -> AnimationState:
    """Generate Blender script using the BlenderScriptGenerator tool."""
    try:
        # Generate the script using the dedicated tool
        script = script_generator.generate(state["prompt"], state["history"])
        
        # Add AI response about generating the animation to history
        updated_history = state["history"] + [
            {"role": "ai", "content": f"I'm generating a 3D animation based on your request: '{state['prompt']}'. This might take a moment..."}
        ]
        
        # Update state
        return {
            **state,
            "blender_script": script,
            "generation_status": "script_generated",
            "history": updated_history
        }
    except Exception as e:
        logger.error(f"Script generation error: {str(e)}")
        
        # Add error message to history
        updated_history = state["history"] + [
            {"role": "ai", "content": f"I encountered an error while trying to generate the animation: {str(e)}"}
        ]
        
        return {
            **state,
            "error": f"Script generation error: {str(e)}",
            "generation_status": "error",
            "history": updated_history
        }

def render_animation(state: AnimationState) -> AnimationState:
    """Send the script to Blender service for rendering."""
    if state.get("error"):
        return state
    
    try:
        # Get ID token for Cloud Run authentication
        token = get_id_token(BLENDER_SERVICE_URL)
        
        # Prepare request to Blender service
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # The script is passed to your existing Cloud Run service
        payload = {
            "prompt": state["prompt"],
            "script": state["blender_script"]
        }
        
        # Make the request to your Blender service
        response = requests.post(
            f"{BLENDER_SERVICE_URL}/render",
            headers=headers,
            json=payload,
            timeout=300  # 5 minute timeout for rendering
        )
        
        # Check for success
        if response.status_code != 200:
            error_message = f"Blender service error: {response.status_code} - {response.text}"
            logger.error(error_message)
            
            # Add error message to history
            updated_history = state["history"] + [
                {"role": "ai", "content": f"I encountered an error while rendering the animation: {error_message}"}
            ]
            
            return {
                **state,
                "error": error_message,
                "generation_status": "error",
                "history": updated_history
            }
        
        # Parse response
        result = response.json()
        
        # Check for error in response
        if "error" in result:
            # Add error message to history
            updated_history = state["history"] + [
                {"role": "ai", "content": f"I encountered an error while rendering the animation: {result['error']}"}
            ]
            
            return {
                **state,
                "error": result["error"],
                "generation_status": "error",
                "history": updated_history
            }
        
        # Success case - get signed URL
        # Add success message to history
        updated_history = state["history"] + [
            {"role": "ai", "content": "Your animation is ready! You can see it in the viewer. Is there anything you'd like me to change about it?"}
        ]
        
        return {
            **state,
            "signed_url": result["signed_url"],
            "generation_status": "completed",
            "history": updated_history
        }
        
    except Exception as e:
        logger.error(f"Render animation error: {str(e)}")
        
        # Add error message to history
        updated_history = state["history"] + [
            {"role": "ai", "content": f"I encountered an error while rendering the animation: {str(e)}"}
        ]
        
        return {
            **state,
            "error": f"Render animation error: {str(e)}",
            "generation_status": "error",
            "history": updated_history
        }

def router(state: AnimationState) -> str:
    """Route to the next node based on state."""
    if state.get("error"):
        return "end"
    if state.get("generation_status") == "conversation_only":
        return "end"
    if state.get("generation_status") == "analyzing":
        return "generate_script"
    if state.get("generation_status") == "script_generated":
        return "render_animation"
    if state.get("generation_status") == "completed":
        return "end"
    # Default case
    return "analyze_prompt"

def create_animation_graph():
    """Create the LangGraph for animation generation."""
    # Define the workflow graph
    workflow = StateGraph(AnimationState)
    
    # Add nodes
    workflow.add_node("analyze_prompt", analyze_prompt)
    workflow.add_node("generate_script", generate_blender_script)
    workflow.add_node("render_animation", render_animation)
    
    # Define edges with the router function
    workflow.add_conditional_edges(
        "analyze_prompt",
        router,
        {
            "generate_script": "generate_script",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "generate_script",
        router,
        {
            "render_animation": "render_animation",
            "end": END
        }
    )
    
    workflow.add_conditional_edges(
        "render_animation",
        router,
        {
            "end": END
        }
    )
    
    # Set the entry point
    workflow.set_entry_point("analyze_prompt")
    
    return workflow.compile()

# Function to run the graph directly for testing
def run_animation_generation(prompt: str, history: List[Message] = None) -> Dict[str, Any]:
    """Run the animation generation workflow with the given prompt and history."""
    # Initialize history if not provided
    if history is None:
        history = []
    
    # Add current prompt to history
    updated_history = history + [{"role": "human", "content": prompt}]
    
    # Initialize the state
    initial_state = AnimationState(
        prompt="",  # Will be set by analyze_prompt if needed
        current_prompt=prompt,
        blender_script="",
        generation_status="started",
        signed_url="",
        error="",
        history=updated_history
    )
    
    # Create and run the graph
    graph = create_animation_graph()
    result = graph.invoke(initial_state)
    
    # Return the final state
    return result

if __name__ == "__main__":
    # Example for testing
    test_prompt = "planets orbiting sun in solar system"
    result = run_animation_generation(test_prompt)
    print(f"Result: {json.dumps(result, indent=2)}")
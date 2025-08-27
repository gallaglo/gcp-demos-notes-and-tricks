"""Main ADK Animation Agent Orchestrator"""
import logging
from google.adk.agents import Agent, SequentialAgent
from sub_agents.analysis.analysis_agent import analysis_agent
from sub_agents.script_generation.script_generation_agent import script_generation_agent
from sub_agents.storage.storage_agent import storage_agent
from tools.blender_service_tool import render_animation_with_blender, get_render_status
from tools.conversation_tool import handle_conversation, get_conversation_context
from config import GENAI_MODEL, GCS_BUCKET_NAME

logger = logging.getLogger(__name__)

# Main orchestration agent prompt
MAIN_AGENT_PROMPT = """You are the main orchestration agent for the 3D Animation Generation system.

Your responsibilities:
1. Coordinate between analysis, script generation, rendering, and storage agents
2. Handle the complete animation generation workflow
3. Manage conversational interactions when no animation is requested
4. Ensure proper error handling and user feedback
5. Coordinate the upload of rendered animations to cloud storage

Workflow:
1. Analyze user input to determine intent (animation vs conversation)
2. If animation requested:
   - Generate Blender script
   - Render animation using Blender service
   - Upload animation and script to cloud storage
   - Return signed URL for user access
3. If conversation:
   - Provide helpful conversational response

You have access to tools for rendering animations and handling conversations.
You also coordinate with specialized sub-agents for analysis, script generation, and storage.

Always provide clear feedback to users about the current step and any errors that occur.
"""

# Create rendering agent that uses the Blender service
rendering_agent = Agent(
    name="rendering_agent",
    model=GENAI_MODEL,
    description="Renders animations using the Blender service",
    instruction="You render animations by sending Blender scripts to the animator service. Use the render_animation_with_blender tool to send scripts for rendering.",
    tools=[render_animation_with_blender, get_render_status],
    output_key="render_result"
)

# Create conversation agent
conversation_agent = Agent(
    name="conversation_agent", 
    model=GENAI_MODEL,
    description="Handles conversational interactions that don't require animation generation",
    instruction="You handle general conversation and questions about animation. Use the handle_conversation tool to generate appropriate responses.",
    tools=[handle_conversation, get_conversation_context],
    output_key="conversation_result"
)

# Create the animation generation workflow (analysis -> script+validation -> render -> storage)
animation_workflow = SequentialAgent(
    name="animation_workflow",
    sub_agents=[
        analysis_agent,
        script_generation_agent,  # Now includes validation agent
        rendering_agent,
        storage_agent
    ]
)

# Create the main orchestration agent
main_agent = Agent(
    name="animation_orchestrator",
    model=GENAI_MODEL,
    description="Main orchestration agent for 3D animation generation and conversation",
    instruction=MAIN_AGENT_PROMPT,
    tools=[],  # Main agent coordinates through sub-agents
    output_key="final_result"
)

# Note: In a full ADK implementation, you would use conditional routing
# between animation_workflow and conversation_agent based on the analysis result.
# For now, this provides the structure for the refactored system.

if __name__ == "__main__":
    # Example usage - this would normally be handled by ADK deployment
    print("ADK Animation Agent initialized")
    print(f"Components: Analysis, Script Generation, Rendering, Storage")
    print(f"Using model: {GENAI_MODEL}")
    print(f"Storage bucket: {GCS_BUCKET_NAME}")
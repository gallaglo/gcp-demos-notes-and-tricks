"""Script Generation Agent for ADK Animation System"""
from google.adk.agents import Agent, SequentialAgent
from .tools.blender_script_tool import generate_blender_script, get_generated_script
from ..validation.validation_agent import validation_agent
from config import GENAI_MODEL
from prompts.script_generation_prompt import SCRIPT_GENERATION_AGENT_PROMPT

# Create the core script generation agent
core_script_agent = Agent(
    name="core_script_agent",
    model=GENAI_MODEL,
    description="Generates Blender Python scripts for 3D animations based on user prompts",
    instruction=SCRIPT_GENERATION_AGENT_PROMPT,
    tools=[generate_blender_script, get_generated_script],
    output_key="script_result"
)

# Create the script generation workflow that includes validation
script_generation_agent = SequentialAgent(
    name="script_generation_agent",
    description="Generates and validates Blender Python scripts for 3D animations",
    sub_agents=[
        core_script_agent,      # Generate the script
        validation_agent        # Validate and fix the script
    ]
)
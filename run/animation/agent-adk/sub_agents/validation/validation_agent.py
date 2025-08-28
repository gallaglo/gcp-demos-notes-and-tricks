"""Validation Agent for ADK Animation System"""
from google.adk.agents import Agent
from sub_agents.validation.tools.script_validator_tool import (
    validate_blender_script, 
    fix_common_script_issues, 
    get_validation_status
)
from config import GENAI_MODEL
from prompts.validation_prompt import VALIDATION_AGENT_PROMPT

# Create the validation agent
validation_agent = Agent(
    name="validation_agent",
    model=GENAI_MODEL,
    description="Validates Blender scripts for security, correctness, and best practices",
    instruction=VALIDATION_AGENT_PROMPT,
    tools=[
        validate_blender_script,
        fix_common_script_issues,
        get_validation_status
    ],
    output_key="validation_result"
)
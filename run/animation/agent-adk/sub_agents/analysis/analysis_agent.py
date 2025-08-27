"""Analysis Agent for ADK Animation System"""
from google.adk.agents import Agent
from .tools.prompt_analyzer_tool import analyze_user_prompt, get_analysis_result
from config import GENAI_MODEL
from prompts.analysis_prompt import ANALYSIS_AGENT_PROMPT

# Create the analysis agent
analysis_agent = Agent(
    name="analysis_agent",
    model=GENAI_MODEL,
    description="Analyzes user prompts to determine if they require animation generation or are conversational",
    instruction=ANALYSIS_AGENT_PROMPT,
    tools=[analyze_user_prompt, get_analysis_result],
    output_key="analysis_result"
)
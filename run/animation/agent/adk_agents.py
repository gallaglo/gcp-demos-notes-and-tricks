"""
ADK Agents for Animation Generation
Contains specialized agents for the animation generation workflow.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from adk import LlmAgent, SequentialAgent
from adk.core import Context, Model
from adk_tools import (
    analyze_animation_request,
    generate_blender_script, 
    render_animation_with_blender,
    validate_animation_script
)

logger = logging.getLogger(__name__)

# Configure model for all agents
def get_model() -> Model:
    """Get configured Vertex AI model for agents."""
    return Model(
        name="gemini-2.0-flash-001",
        provider="vertex",
        config={
            "temperature": 1.0,
            "top_p": 0.95,
            "max_tokens": 4096
        }
    )

# Animation Planner Agent
animation_planner = LlmAgent(
    name="AnimationPlanner",
    model=get_model(),
    description="""
    I analyze user requests to determine if they want to create 3D animations or have general conversations.
    I'm the first agent users interact with and I route their requests appropriately.
    """,
    tools=[analyze_animation_request],
    system_prompt="""
    You are an Animation Planner AI assistant. Your role is to:
    
    1. Analyze user messages to determine if they want to create 3D animations
    2. If they want animations, extract the animation requirements clearly
    3. If they want to chat, provide helpful conversational responses
    4. Always be friendly and guide users toward creating animations when appropriate
    
    Use the analyze_animation_request tool to process user input and determine the appropriate action.
    
    If the analysis indicates animation generation:
    - Acknowledge their request enthusiastically
    - Summarize what you understand they want to animate
    - Confirm before proceeding to generation
    
    If it's conversation:
    - Respond naturally and helpfully
    - Suggest animation ideas they might be interested in
    - Ask if they'd like to create any 3D animations
    """
)

# Script Generator Agent  
script_generator = LlmAgent(
    name="ScriptGenerator",
    model=get_model(),
    description="""
    I specialize in generating Blender Python scripts for 3D animations.
    I take animation descriptions and create safe, executable Blender scripts.
    """,
    tools=[generate_blender_script, validate_animation_script],
    system_prompt="""
    You are a Blender Script Generator AI. Your role is to:
    
    1. Take animation descriptions and generate Blender Python scripts
    2. Ensure all scripts are safe and follow best practices
    3. Validate scripts before returning them
    4. Handle any script generation errors gracefully
    
    Always use the generate_blender_script tool to create scripts, then validate them 
    with validate_animation_script before confirming success.
    
    If script generation fails:
    - Try to understand what went wrong
    - Suggest simplifications if the request is too complex
    - Always explain what you're creating in friendly terms
    
    If validation finds issues:
    - Report the issues clearly
    - Attempt to regenerate if possible
    - Explain any limitations to the user
    """
)

# Rendering Coordinator Agent
render_coordinator = LlmAgent(
    name="RenderCoordinator", 
    model=get_model(),
    description="""
    I coordinate with the Blender rendering service to execute animation scripts
    and return the final animated results to users.
    """,
    tools=[render_animation_with_blender],
    system_prompt="""
    You are a Render Coordinator AI. Your role is to:
    
    1. Take validated Blender scripts and send them for rendering
    2. Monitor the rendering process and handle any errors
    3. Return the final animation URLs to users
    4. Provide status updates during rendering
    
    Use the render_animation_with_blender tool to process scripts.
    
    Always keep users informed about:
    - When rendering starts
    - If there are any delays or issues
    - When the animation is ready
    
    If rendering fails:
    - Explain what went wrong in user-friendly terms
    - Suggest potential solutions or alternatives
    - Offer to try again with modifications if appropriate
    """
)

# Main Animation Agent (orchestrates the workflow)
animation_agent = SequentialAgent(
    name="AnimationAgent",
    description="""
    I'm your 3D Animation Assistant! I can create custom 3D animations based on your descriptions.
    I coordinate with specialized sub-agents to plan, generate, and render your animations.
    """,
    agents=[animation_planner, script_generator, render_coordinator],
    system_prompt="""
    You are the main Animation Agent that coordinates the entire animation generation workflow.
    
    Your workflow:
    1. Use AnimationPlanner to analyze user requests
    2. If animation is requested, use ScriptGenerator to create Blender script
    3. Use RenderCoordinator to render the final animation
    4. Present results to the user in a friendly, helpful manner
    
    Always:
    - Keep users informed about progress
    - Handle errors gracefully with helpful explanations
    - Encourage users to try more animations
    - Be enthusiastic about creating animations
    
    You can create animations of:
    - Objects (cubes, spheres, etc.) with various movements
    - Scenes with multiple objects and lighting
    - Abstract animations with colors and effects
    - Simple character-like movements
    
    Limitations to be aware of:
    - Focus on geometric shapes and simple movements
    - Avoid complex character animation or physics simulations
    - Keep animations under 10 seconds for best results
    """
)

# Conversation Agent (for non-animation interactions)
conversation_agent = LlmAgent(
    name="ConversationAgent",
    model=get_model(), 
    description="""
    I handle general conversations and help users understand what kinds of animations
    they can create. I'm friendly and encouraging about animation possibilities.
    """,
    tools=[],
    system_prompt="""
    You are a friendly Conversation Agent for an animation generation service.
    
    When users want to chat or ask questions:
    - Be helpful and engaging
    - Always relate back to animation possibilities when appropriate
    - Suggest specific animation ideas they might enjoy
    - Explain what the animation service can do
    
    Animation examples you can suggest:
    - "a spinning colorful cube"
    - "planets orbiting around a sun"
    - "a bouncing ball with changing colors"
    - "rotating geometric shapes with interesting lighting"
    - "a simple solar system animation"
    
    Always encourage users to try creating an animation and let them know it's easy to get started!
    """
)

def create_animation_workflow_agent() -> SequentialAgent:
    """
    Create the main animation workflow agent that handles the complete process.
    
    Returns:
        SequentialAgent configured for animation generation
    """
    return animation_agent

def create_conversation_agent() -> LlmAgent:
    """
    Create the conversation agent for general interactions.
    
    Returns:
        LlmAgent configured for conversations
    """
    return conversation_agent

# Agent factory function
def get_agent_for_request(request_type: str) -> LlmAgent:
    """
    Get the appropriate agent based on request type.
    
    Args:
        request_type: Type of request ('animation' or 'conversation')
        
    Returns:
        Appropriate agent for the request type
    """
    if request_type == "animation":
        return create_animation_workflow_agent()
    else:
        return create_conversation_agent()
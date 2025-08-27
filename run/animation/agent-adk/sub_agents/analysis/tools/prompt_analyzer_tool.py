"""Prompt Analysis Tool for ADK Animation Agent"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def analyze_user_prompt(user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Analyze user message to determine if it requires animation generation or is conversational.
    
    Args:
        user_message: The user's current message
        conversation_history: List of previous messages with role and content
        
    Returns:
        Dictionary containing analysis result and next action
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        # Keywords that strongly indicate animation requests
        animation_keywords = [
            "animate", "animation", "3d", "blender", "render", "create", "generate",
            "spinning", "rotating", "moving", "cube", "sphere", "planet", "orbit",
            "scene", "model", "object", "visual", "show me", "make a", "build"
        ]
        
        # Keywords that indicate modifications to existing animations
        modification_keywords = [
            "change", "modify", "update", "faster", "slower", "bigger", "smaller",
            "different color", "move", "adjust", "fix", "improve"
        ]
        
        # Convert message to lowercase for analysis
        message_lower = user_message.lower()
        
        # Check if this is clearly an animation request
        if any(keyword in message_lower for keyword in animation_keywords):
            result_type = "GENERATE_ANIMATION"
            description = user_message
            action = "generate_script"
        
        # Check if this is a modification request with animation context
        elif any(keyword in message_lower for keyword in modification_keywords) and len(conversation_history) > 0:
            # Look for previous animation context in history
            has_animation_context = any(
                any(anim_keyword in msg.get("content", "").lower() for anim_keyword in animation_keywords)
                for msg in conversation_history
            )
            
            if has_animation_context:
                result_type = "MODIFY_ANIMATION"
                description = user_message
                action = "generate_script"
            else:
                result_type = "CONVERSATION"
                description = "I understand you want to modify something, but could you clarify what animation you're referring to?"
                action = "conversation"
        
        # Default to conversation for questions, greetings, etc.
        else:
            result_type = "CONVERSATION"
            # Generate appropriate conversational response
            if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
                description = "Hello! I'm here to help you create 3D animations. What would you like me to animate for you?"
            elif any(word in message_lower for word in ["help", "what can you do", "capabilities"]):
                description = "I can create 3D animations based on your descriptions! Just tell me what you'd like to see animated - objects, scenes, movements, etc."
            elif any(word in message_lower for word in ["how", "what is", "explain"]):
                description = "I specialize in creating 3D animations using Blender. You can describe what you want to see animated, and I'll generate the code to create it!"
            else:
                description = "I'm not sure if you're asking for an animation. Could you clarify what you'd like me to help you with?"
            action = "conversation"
        
        return {
            "result_type": result_type,
            "description": description,
            "action": action,
            "confidence": "high" if result_type == "GENERATE_ANIMATION" else "medium",
            "message": f"Analysis complete: {result_type}"
        }
        
    except Exception as e:
        error_msg = f"Error analyzing prompt: {str(e)}"
        logger.error(error_msg)
        
        return {
            "result_type": "ERROR",
            "description": "Failed to analyze the user request",
            "action": "error",
            "error": error_msg,
            "message": "Analysis failed due to an error"
        }

async def get_analysis_result() -> Dict[str, Any]:
    """
    Get the current analysis result. Note: In ADK, state is managed differently.
    This function is kept for compatibility but may need refactoring.
    
    Returns:
        Dictionary containing current analysis state
    """
    return {
        "result_type": "UNKNOWN",
        "description": "",
        "action": "unknown",
        "current_prompt": "",
        "error": ""
    }
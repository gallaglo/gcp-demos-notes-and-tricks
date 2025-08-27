"""Conversation Tool for ADK Animation Agent"""
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def handle_conversation( user_message: str, conversation_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Handle conversational interactions that don't require animation generation.
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation messages
        
    Returns:
        Dictionary containing conversational response
    """
    try:
        if conversation_history is None:
            conversation_history = []
        
        # Store conversation context in state
        
        # Generate appropriate conversational responses based on message content
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["hello", "hi", "hey", "greetings"]):
            response = "Hello! I'm here to help you create 3D animations. What would you like me to animate for you?"
        
        elif any(word in message_lower for word in ["help", "what can you do", "capabilities"]):
            response = "I can create 3D animations based on your descriptions! Just tell me what you'd like to see animated - objects, scenes, movements, etc. For example, you could ask me to create 'a spinning cube' or 'planets orbiting the sun'."
        
        elif any(word in message_lower for word in ["how", "what is", "explain"]):
            if "animation" in message_lower or "3d" in message_lower:
                response = "3D animation works by creating objects in a virtual 3D space and defining how they move, rotate, or change over time. I use Blender, a powerful 3D software, to create these animations based on your descriptions."
            else:
                response = "I specialize in creating 3D animations using Blender. You can describe what you want to see animated, and I'll generate the code to create it!"
        
        elif any(word in message_lower for word in ["thank", "thanks"]):
            response = "You're welcome! Feel free to ask me to create any 3D animations you'd like to see."
        
        elif any(word in message_lower for word in ["bye", "goodbye", "see you"]):
            response = "Goodbye! Come back anytime you want to create some amazing 3D animations!"
        
        else:
            response = "I'm not sure if you're asking for an animation or just chatting. Could you clarify what you'd like me to help you with? I'm great at creating 3D animations!"
        
        # Store the response in state
        
        # Update conversation history
        updated_history = conversation_history + [
            {"role": "human", "content": user_message},
            {"role": "ai", "content": response}
        ]
        
        return {
            "status": "success",
            "response": response,
            "conversation_type": "general",
            "message": "Conversational response generated"
        }
        
    except Exception as e:
        error_msg = f"Error handling conversation: {str(e)}"
        logger.error(error_msg)
        
        
        return {
            "status": "error",
            "response": "I apologize, but I encountered an error while processing your message.",
            "error": error_msg,
            "message": "Failed to handle conversation"
        }

async def get_conversation_context() -> Dict[str, Any]:
    """
    Get the current conversation context from tool state.
    
    Args:
        
    Returns:
        Dictionary containing conversation context
    """
    return {
        "conversation_history": [],
        "last_response": "",
        "context": "empty"
    }
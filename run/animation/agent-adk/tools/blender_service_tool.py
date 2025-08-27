"""Blender Service Tool for ADK Animation Agent"""
import logging
import requests
from typing import Dict, Any
from google.adk.tools import tool
from google.adk.tools.context import ToolContext
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from ..config import BLENDER_SERVICE_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

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

@tool
async def render_animation_with_blender(tool_context: ToolContext, script: str, prompt: str) -> Dict[str, Any]:
    """
    Send Blender script to the animator service for rendering.
    
    Args:
        tool_context: ADK tool context
        script: The Blender Python script to render
        prompt: The original user prompt for context
        
    Returns:
        Dictionary containing render result and file path
    """
    try:
        # Get ID token for Cloud Run authentication
        token = get_id_token(BLENDER_SERVICE_URL)
        
        # Prepare request to Blender service
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # The script is passed to the existing Cloud Run service
        payload = {
            "prompt": prompt,
            "script": script
        }
        
        # Log the first 200 characters of the script for debugging
        script_excerpt = script[:200] + "..." if len(script) > 200 else script
        logger.info(f"Sending script to Blender service (excerpt): {script_excerpt}")
        
        # Make the request to Blender service
        response = requests.post(
            f"{BLENDER_SERVICE_URL}/render",
            headers=headers,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )
        
        # Check for success
        if response.status_code != 200:
            error_message = f"Blender service error: {response.status_code} - {response.text}"
            logger.error(error_message)
            
            # Store error in state
            tool_context.state["render_status"] = "error"
            tool_context.state["render_error"] = error_message
            
            return {
                "status": "error",
                "error": error_message,
                "file_path": "",
                "message": "Failed to render animation"
            }
        
        # Parse response
        result = response.json()
        
        # Check for error in response
        if "error" in result and result["error"]:
            # Store error in state
            tool_context.state["render_status"] = "error"
            tool_context.state["render_error"] = result["error"]
            
            return {
                "status": "error",
                "error": result["error"],
                "file_path": "",
                "message": "Blender rendering failed"
            }
        
        # Success case - the old service returns signed_url directly
        # We need to modify this to return file path for the storage agent
        if "signed_url" in result:
            # Store render results in state
            tool_context.state["render_status"] = "success"
            tool_context.state["animation_file_url"] = result["signed_url"]
            
            return {
                "status": "success",
                "file_path": "",  # The old service uploads directly, no local file
                "signed_url": result["signed_url"],
                "message": "Animation rendered successfully (legacy mode)"
            }
        else:
            error_message = "Blender service returned unexpected response format"
            logger.error(error_message)
            
            tool_context.state["render_status"] = "error"
            tool_context.state["render_error"] = error_message
            
            return {
                "status": "error",
                "error": error_message,
                "file_path": "",
                "message": "Unexpected response from Blender service"
            }
        
    except Exception as e:
        error_msg = f"Error communicating with Blender service: {str(e)}"
        logger.error(error_msg)
        
        # Store error in state
        tool_context.state["render_status"] = "error"
        tool_context.state["render_error"] = error_msg
        
        return {
            "status": "error",
            "error": error_msg,
            "file_path": "",
            "message": "Failed to communicate with Blender service"
        }

@tool
async def get_render_status(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Get the current render status from tool context state.
    
    Args:
        tool_context: ADK tool context
        
    Returns:
        Dictionary containing current render status
    """
    render_status = tool_context.state.get("render_status", "not_started")
    render_error = tool_context.state.get("render_error", "")
    animation_file_url = tool_context.state.get("animation_file_url", "")
    
    return {
        "render_status": render_status,
        "error": render_error,
        "animation_file_url": animation_file_url,
        "has_result": bool(animation_file_url)
    }
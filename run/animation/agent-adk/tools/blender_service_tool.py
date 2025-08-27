"""Blender Service Tool for ADK Animation Agent"""
import logging
import requests
from typing import Dict, Any
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

async def render_animation_with_blender(script: str, prompt: str) -> Dict[str, Any]:
    """
    Send Blender script to the animator service for rendering.
    
    Args:
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
            return {
                "status": "error",
                "error": result["error"],
                "file_path": "",
                "message": "Blender rendering failed"
            }
        
        # Success case - the old service returns signed_url directly
        # We need to modify this to return file path for the storage agent
        if "signed_url" in result:
            return {
                "status": "success",
                "file_path": "",  # The old service uploads directly, no local file
                "signed_url": result["signed_url"],
                "message": "Animation rendered successfully (legacy mode)"
            }
        else:
            error_message = "Blender service returned unexpected response format"
            logger.error(error_message)
            
            return {
                "status": "error",
                "error": error_message,
                "file_path": "",
                "message": "Unexpected response from Blender service"
            }
        
    except Exception as e:
        error_msg = f"Error communicating with Blender service: {str(e)}"
        logger.error(error_msg)
        
        return {
            "status": "error",
            "error": error_msg,
            "file_path": "",
            "message": "Failed to communicate with Blender service"
        }

async def get_render_status() -> Dict[str, Any]:
    """
    Get the current render status. Note: In ADK, state is managed differently.
    This function is kept for compatibility but may need refactoring.
    
    Returns:
        Dictionary containing current render status
    """
    return {
        "render_status": "not_started",
        "error": "",
        "animation_file_url": "",
        "has_result": False
    }
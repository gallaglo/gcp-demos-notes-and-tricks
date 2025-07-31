"""
ADK Tools for Animation Generation
Contains all tools used by ADK agents for animation generation workflow.
"""

import os
import json
import requests
import logging
from typing import Dict, Any, Optional, List
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from adk import FunctionTool
from adk.core import Context
import re

logger = logging.getLogger(__name__)

# Configuration
BLENDER_SERVICE_URL = os.environ.get("BLENDER_SERVICE_URL")
if not BLENDER_SERVICE_URL:
    raise ValueError("BLENDER_SERVICE_URL environment variable is not set")

def get_id_token(audience: str) -> str:
    """Gets an ID token for authentication with Cloud Run."""
    try:
        request = Request()
        token = id_token.fetch_id_token(request, audience)
        return token
    except Exception as e:
        logger.error(f"Error getting ID token: {str(e)}")
        raise

@FunctionTool
def analyze_animation_request(context: Context, user_prompt: str) -> Dict[str, Any]:
    """
    Analyze user prompt to determine if it requires animation generation or conversation.
    
    Args:
        user_prompt: The user's input message
        
    Returns:
        Dict containing analysis results with action_type and details
    """
    try:
        # Keywords that indicate animation requests
        animation_keywords = [
            'animate', 'animation', '3d', 'blender', 'render', 'model', 'scene',
            'rotate', 'move', 'spin', 'orbit', 'fly', 'bounce', 'dance', 'walk',
            'cube', 'sphere', 'cylinder', 'torus', 'plane', 'mesh', 'object',
            'camera', 'light', 'material', 'texture', 'color', 'shader',
            'keyframe', 'timeline', 'frame', 'second', 'loop', 'cycle'
        ]
        
        # Check if prompt contains animation-related keywords
        prompt_lower = user_prompt.lower()
        has_animation_keywords = any(keyword in prompt_lower for keyword in animation_keywords)
        
        # Check for explicit animation requests
        animation_phrases = [
            'create', 'make', 'generate', 'build', 'show me', 'i want',
            'can you make', 'please create', 'i need'
        ]
        
        has_creation_intent = any(phrase in prompt_lower for phrase in animation_phrases)
        
        if has_animation_keywords and has_creation_intent:
            return {
                "action_type": "generate_animation",
                "confidence": "high",
                "description": f"User is requesting 3D animation: {user_prompt}",
                "animation_prompt": user_prompt
            }
        elif has_animation_keywords:
            return {
                "action_type": "generate_animation", 
                "confidence": "medium",
                "description": f"User mentions animation-related concepts: {user_prompt}",
                "animation_prompt": user_prompt
            }
        else:
            return {
                "action_type": "conversation",
                "confidence": "high", 
                "description": "User is having a general conversation",
                "response": "I'm here to help you create 3D animations! You can ask me to create animations like 'make a spinning cube' or 'animate planets orbiting the sun'. What would you like me to animate?"
            }
            
    except Exception as e:
        logger.error(f"Error analyzing animation request: {str(e)}")
        return {
            "action_type": "error",
            "error": str(e)
        }

@FunctionTool
def generate_blender_script(context: Context, animation_prompt: str) -> Dict[str, Any]:
    """
    Generate a Blender Python script from animation prompt.
    
    Args:
        animation_prompt: Description of animation to create
        
    Returns:
        Dict containing the generated script or error information
    """
    try:
        from prompts import BLENDER_PROMPT
        from langchain_google_vertexai import ChatVertexAI
        
        # Initialize LLM
        llm = ChatVertexAI(
            model_name="gemini-2.0-flash-001",
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=4096,
            request_timeout=60,
            max_retries=3
        )
        
        # Generate script using the prompt template
        formatted_prompt = BLENDER_PROMPT.format(user_prompt=animation_prompt)
        response = llm.invoke(formatted_prompt)
        
        # Extract script content
        if hasattr(response, 'content'):
            raw_content = response.content
        else:
            raw_content = str(response)
        
        # Extract script from code blocks
        if '```python' in raw_content and '```' in raw_content:
            script = raw_content.split('```python')[1].split('```')[0].strip()
        else:
            script = raw_content.strip()
            
        if not script:
            raise ValueError("Generated script is empty")
        
        # Apply fixes and validation
        script = _fix_common_script_issues(script)
        script = _modify_script_for_output_path(script)
        _validate_script_requirements(script)
        
        return {
            "status": "success",
            "script": script,
            "prompt": animation_prompt
        }
        
    except Exception as e:
        logger.error(f"Error generating Blender script: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

def _fix_common_script_issues(script: str) -> str:
    """Fix common issues in generated Blender scripts."""
    # Fix camera creation syntax
    script = script.replace(
        'camera_object = bpy.data.objects.new("Camera", "Camera", camera_data)',
        'camera_object = bpy.data.objects.new("Camera", camera_data)'
    )
    
    # Fix light object creation
    script = script.replace(
        'light_object = bpy.data.objects.new("Light", "Light", light_data)',
        'light_object = bpy.data.objects.new("Light", light_data)'
    )
    
    # Fix rotation syntax
    script = script.replace('obj.rotation = (', 'obj.rotation_euler = (')
    
    # Fix scene linking
    script = script.replace(
        'bpy.context.scene.objects.link(',
        'bpy.context.scene.collection.objects.link('
    )
    
    # Fix three-argument object creation
    pattern = r'bpy\.data\.objects\.new\([\'"]([^\'"]+)[\'"],\s*[\'"]([^\'"]+)[\'"],\s*([^)]+)\)'
    replacement = r'bpy.data.objects.new("\1", \3)'
    script = re.sub(pattern, replacement, script)
    
    return script

def _modify_script_for_output_path(script: str) -> str:
    """Ensure script has proper command-line argument handling for output path."""
    lines = script.split('\n')
    filtered_lines = [
        line for line in lines 
        if not ('output_path =' in line and 'os.path' in line)
    ]
    
    # Find position after imports
    import_end_idx = 0
    for i, line in enumerate(filtered_lines):
        if line.strip().startswith('import '):
            import_end_idx = i + 1
    
    # Insert path handling code
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

def _validate_script_requirements(script: str) -> None:
    """Validate the generated script contains required components."""
    # Check for forbidden terms
    forbidden_terms = ['subprocess', 'os.system', 'eval(', 'exec(']
    for term in forbidden_terms:
        if term in script:
            raise ValueError(f'Generated script contains forbidden term: {term}')
    
    # Required components
    required_components = [
        'import bpy',
        'bpy.ops.export_scene.gltf(',
        'filepath=output_path',
        'export_format=\'GLB\'',
    ]
    
    for component in required_components:
        if component not in script:
            raise ValueError(f'Generated script missing required component: {component}')

@FunctionTool
def render_animation_with_blender(context: Context, script: str, prompt: str) -> Dict[str, Any]:
    """
    Send Blender script to animator service for rendering.
    
    Args:
        script: The Blender Python script to execute
        prompt: Original animation prompt for context
        
    Returns:
        Dict containing signed URL or error information  
    """
    try:
        # Get ID token for Cloud Run authentication
        token = get_id_token(BLENDER_SERVICE_URL)
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "script": script
        }
        
        # Log script excerpt for debugging
        script_excerpt = script[:200] + "..." if len(script) > 200 else script
        logger.info(f"Sending script to Blender service (excerpt): {script_excerpt}")
        
        # Make request to Blender service
        response = requests.post(
            f"{BLENDER_SERVICE_URL}/render",
            headers=headers,
            json=payload,
            timeout=300  # 5 minute timeout
        )
        
        if response.status_code != 200:
            error_message = f"Blender service error: {response.status_code} - {response.text}"
            logger.error(error_message)
            return {
                "status": "error",
                "error": error_message
            }
        
        result = response.json()
        
        if "error" in result and result["error"]:
            return {
                "status": "error", 
                "error": result["error"]
            }
        
        return {
            "status": "success",
            "signed_url": result["signed_url"],
            "prompt": prompt
        }
        
    except Exception as e:
        logger.error(f"Error rendering animation: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

@FunctionTool
def validate_animation_script(context: Context, script: str) -> Dict[str, Any]:
    """
    Validate a Blender script for safety and correctness.
    
    Args:
        script: The Blender Python script to validate
        
    Returns:
        Dict containing validation results
    """
    try:
        issues = []
        warnings = []
        
        # Security checks
        forbidden_patterns = [
            ('subprocess', 'Contains subprocess calls'),
            ('os.system', 'Contains system command execution'),
            ('eval(', 'Contains eval() calls'),
            ('exec(', 'Contains exec() calls'),
            ('import requests', 'Contains network requests'),
            ('import urllib', 'Contains network requests'),
            ('open(', 'Contains file operations')
        ]
        
        for pattern, message in forbidden_patterns:
            if pattern in script:
                issues.append(f"Security issue: {message}")
        
        # Required components
        required_components = [
            ('import bpy', 'Missing Blender Python API import'),
            ('bpy.ops.export_scene.gltf', 'Missing GLB export operation'),
            ('export_format=\'GLB\'', 'Export format not set to GLB')
        ]
        
        for component, message in required_components:
            if component not in script:
                issues.append(f"Missing requirement: {message}")
        
        # Warnings for common issues
        if 'bpy.data.objects.new(' in script:
            # Check for three-argument pattern
            pattern = r'bpy\.data\.objects\.new\([\'"][^\'"]+[\'"],\s*[\'"][^\'"]+[\'"],\s*[^)]+\)'
            if re.search(pattern, script):
                warnings.append("Object creation may have incorrect syntax")
        
        return {
            "status": "success",
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "issue_count": len(issues),
            "warning_count": len(warnings)
        }
        
    except Exception as e:
        logger.error(f"Error validating script: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "is_valid": False
        }
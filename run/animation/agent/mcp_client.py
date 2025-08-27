import asyncio
import json
import logging
import httpx
from typing import Dict, Any, Optional, List
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPResponse:
    """Response from MCP server operations"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AnimationMCPClient:
    """MCP Client for connecting to the Animation MCP Server"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the MCP client
        
        Args:
            base_url: Base URL of the animator service (defaults to env var BLENDER_SERVICE_URL)
        """
        self.base_url = base_url or os.getenv('BLENDER_SERVICE_URL', 'http://localhost:8080')
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 minute timeout for rendering
        logger.info(f"Initialized MCP client for animator service at: {self.base_url}")
    
    async def get_status(self) -> MCPResponse:
        """
        Get the status of the MCP server
        
        Returns:
            MCPResponse with server status information
        """
        try:
            response = await self.client.get(f"{self.base_url}mcp/status")
            response.raise_for_status()
            
            data = response.json()
            return MCPResponse(success=True, data=data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting MCP status: {str(e)}")
            return MCPResponse(success=False, error=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting MCP status: {str(e)}")
            return MCPResponse(success=False, error=str(e))
    
    async def validate_script(self, script: str) -> MCPResponse:
        """
        Validate a Blender script using the MCP server
        
        Args:
            script: Blender Python script to validate
            
        Returns:
            MCPResponse with validation result
        """
        try:
            payload = {"script": script}
            response = await self.client.post(
                f"{self.base_url}mcp/validate",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            return MCPResponse(success=True, data=data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error validating script: {str(e)}")
            return MCPResponse(success=False, error=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error validating script: {str(e)}")
            return MCPResponse(success=False, error=str(e))
    
    async def render_animation(self, script: str, prompt: Optional[str] = None) -> MCPResponse:
        """
        Render an animation using the MCP server
        
        Args:
            script: Blender Python script to execute
            prompt: Optional description of the animation
            
        Returns:
            MCPResponse with rendering result including signed_url if successful
        """
        try:
            payload = {
                "script": script,
                "prompt": prompt or "Animation rendered via MCP client"
            }
            
            response = await self.client.post(
                f"{self.base_url}mcp/render",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            return MCPResponse(success=True, data=data)
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error rendering animation: {str(e)}")
            return MCPResponse(success=False, error=f"HTTP error: {str(e)}")
        except Exception as e:
            logger.error(f"Error rendering animation: {str(e)}")
            return MCPResponse(success=False, error=str(e))
    
    async def stream_connection(self):
        """
        Establish SSE connection to the MCP server for real-time communication
        
        Yields:
            Dict with event data from the MCP server
        """
        try:
            async with self.client.stream(
                "GET",
                f"{self.base_url}mcp/stream",
                headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"}
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            yield data
                        except json.JSONDecodeError as e:
                            logger.warning(f"Failed to parse SSE data: {line}, error: {e}")
                            continue
                    elif line.strip() == "":
                        # Empty line, continue
                        continue
                        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in SSE stream: {str(e)}")
            yield {"type": "error", "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in SSE stream: {str(e)}")
            yield {"type": "error", "error": str(e)}
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

class MCPToolsRegistry:
    """Registry of MCP tools for LangGraph integration"""
    
    def __init__(self, mcp_client: AnimationMCPClient):
        self.mcp_client = mcp_client
        self.tools = {
            "validate_blender_script": self._validate_script_tool,
            "render_animation": self._render_animation_tool,
            "get_mcp_status": self._get_status_tool,
        }
    
    async def _validate_script_tool(self, script: str) -> Dict[str, Any]:
        """Tool wrapper for script validation"""
        response = await self.mcp_client.validate_script(script)
        if response.success:
            return response.data or {}
        else:
            return {"error": response.error, "valid": False}
    
    async def _render_animation_tool(self, script: str, prompt: Optional[str] = None) -> Dict[str, Any]:
        """Tool wrapper for animation rendering"""
        response = await self.mcp_client.render_animation(script, prompt)
        if response.success:
            return response.data or {}
        else:
            return {"error": response.error, "success": False}
    
    async def _get_status_tool(self) -> Dict[str, Any]:
        """Tool wrapper for getting MCP status"""
        response = await self.mcp_client.get_status()
        if response.success:
            return response.data or {}
        else:
            return {"error": response.error, "mcp_available": False}
    
    def get_tool_descriptions(self) -> List[Dict[str, Any]]:
        """Get descriptions of available MCP tools for LangGraph"""
        return [
            {
                "name": "validate_blender_script",
                "description": "Validate a Blender Python script for security and required components",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "The Blender Python script to validate"
                        }
                    },
                    "required": ["script"]
                }
            },
            {
                "name": "render_animation",
                "description": "Render a 3D animation from a Blender Python script",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script": {
                            "type": "string",
                            "description": "The Blender Python script to execute"
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Optional description of the animation"
                        }
                    },
                    "required": ["script"]
                }
            },
            {
                "name": "get_mcp_status",
                "description": "Get the current status of the MCP animation server",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]

# Global MCP client instance
_mcp_client: Optional[AnimationMCPClient] = None

async def get_mcp_client() -> AnimationMCPClient:
    """Get or create the global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = AnimationMCPClient()
    return _mcp_client

async def cleanup_mcp_client():
    """Cleanup the global MCP client instance"""
    global _mcp_client
    if _mcp_client:
        await _mcp_client.close()
        _mcp_client = None
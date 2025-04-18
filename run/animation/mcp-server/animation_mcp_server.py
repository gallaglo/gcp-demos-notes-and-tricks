# animation_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context
import logging
import requests
import json
import os
import threading
from script_generator import generate_animation_script
from dataclasses import dataclass
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BlenderServiceClient:
    """Client for communicating with the Blender renderer service"""
    endpoint: str = None
    
    def __post_init__(self):
        # Use environment variable if endpoint not provided
        if not self.endpoint:
            self.endpoint = os.environ.get("BLENDER_SERVICE_URL")
            if not self.endpoint:
                logger.warning("BLENDER_SERVICE_URL environment variable not set")
                self.endpoint = "http://localhost:8080"  # Default fallback
    
    def render_animation(self, script: str, prompt: str = "") -> Dict[str, Any]:
        """Send a request to the Blender service to render an animation"""
        try:
            logger.info(f"Requesting animation rendering for prompt: {prompt}")
            
            headers = {"Content-Type": "application/json"}
            
            # Add auth token if available from environment
            auth_token = os.environ.get("BLENDER_SERVICE_TOKEN")
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = requests.post(
                f"{self.endpoint}/render",
                headers=headers,
                json={"script": script, "prompt": prompt},
                timeout=300  # 5 minute timeout
            )
            
            # Check for success
            if response.status_code != 200:
                error_message = f"Blender service error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return {"error": error_message}
            
            # Parse response
            result = response.json()
            logger.info(f"Animation rendering result: {result}")
            
            return result
        except Exception as e:
            logger.error(f"Error in animation rendering request: {str(e)}")
            return {"error": f"Blender service error: {str(e)}"}
    
    def validate_script(self, script: str) -> Dict[str, Any]:
        """Validate a Blender script without rendering it"""
        try:
            logger.info("Validating Blender script")
            
            headers = {"Content-Type": "application/json"}
            
            # Add auth token if available from environment
            auth_token = os.environ.get("BLENDER_SERVICE_TOKEN")
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = requests.post(
                f"{self.endpoint}/validate",
                headers=headers,
                json={"script": script},
                timeout=30  # 30 second timeout
            )
            
            # Check for success
            if response.status_code != 200:
                error_message = f"Validation error: {response.status_code} - {response.text}"
                logger.error(error_message)
                return {"valid": False, "error": error_message}
            
            # Parse response
            result = response.json()
            logger.info(f"Validation result: {result}")
            
            return result
        except Exception as e:
            logger.error(f"Error in script validation request: {str(e)}")
            return {"valid": False, "error": f"Validation error: {str(e)}"}

    def check_health(self) -> bool:
        """Check if the Blender service is healthy"""
        try:
            response = requests.get(f"{self.endpoint}/health", timeout=5)
            return response.ok
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

class AnimationMCPServer:
    """MCP server for animation generation"""
    
    def __init__(self):
        """Initialize the MCP server"""
        self.mcp = FastMCP(
            "AnimationMCP",
            description="Animation generation through the Model Context Protocol"
        )
        
        # Initialize Blender service client
        self.blender_service = BlenderServiceClient()
        
        # Register tools
        self._register_tools()
        
        # Thread for running the MCP server
        self.server_thread = None
        self.is_running = False
    
    def _register_tools(self):
        """Register tools with the MCP server"""
        # Generate animation script
        @self.mcp.tool()
        def generate_animation_script(ctx: Context, prompt: str) -> str:
            """
            Generate a Blender Python script for an animation based on a text prompt.
            
            Parameters:
            - prompt: Text description of the animation to create
            
            Returns a Blender Python script.
            """
            return generate_animation_script(prompt)
        
        # Validate animation script
        @self.mcp.tool()
        def validate_animation_script(ctx: Context, script: str) -> str:
            """
            Validate a Blender animation script to check for any issues before rendering.
            
            Parameters:
            - script: The Blender Python script to validate
            
            Returns information about script validity and any potential issues.
            """
            result = self.blender_service.validate_script(script)
            
            # Format the result
            if result.get("valid", False):
                issues = result.get("potential_issues", [])
                if issues:
                    issues_text = "\n".join([f"- {issue}" for issue in issues])
                    return f"Script is valid, but has potential issues:\n{issues_text}"
                else:
                    return "Script is valid and ready for rendering."
            else:
                error = result.get("error", "Unknown validation error")
                return f"Script validation failed: {error}"
        
        # Render animation
        @self.mcp.tool()
        def render_animation(ctx: Context, script: str, prompt: str = "") -> str:
            """
            Render a 3D animation using a Blender script.
            
            Parameters:
            - script: The Blender Python script to execute
            - prompt: Optional text description of the animation (for logging purposes)
            
            Returns information about the rendered animation including a URL to view it.
            """
            result = self.blender_service.render_animation(script, prompt)
            
            # Handle potential error
            if "error" in result and result["error"]:
                return f"Error rendering animation: {result['error']}"
            
            # Format the result
            signed_url = result.get("signed_url", "")
            expiration = result.get("expiration", "unknown")
            
            response = {
                "signed_url": signed_url,
                "expiration": expiration,
                "message": f"Animation rendered successfully. URL valid for {expiration}."
            }
            
            return json.dumps(response, indent=2)
        
        # Create and render animation
        @self.mcp.tool()
        def create_and_render_animation(ctx: Context, prompt: str) -> str:
            """
            Create and render a 3D animation in one step based on a text prompt.
            
            Parameters:
            - prompt: Text description of the animation to create
            
            Returns information about the rendered animation including a URL to view it.
            """
            # First generate the script
            script = generate_animation_script(prompt)
            
            # Validate the script
            validation_result = self.blender_service.validate_script(script)
            if not validation_result.get("valid", False):
                error = validation_result.get("error", "Unknown validation error")
                return f"Script generation failed validation: {error}"
            
            # Render the animation
            render_result = self.blender_service.render_animation(script, prompt)
            
            # Add the prompt and a script summary to the result
            if "error" in render_result and render_result["error"]:
                return json.dumps({"error": render_result["error"]})
            
            render_result["prompt"] = prompt
            render_result["script_summary"] = script.split("\n")[0:5][-1].strip()
            
            return json.dumps(render_result, indent=2)
        
        # Define animation creation strategy
        @self.mcp.prompt()
        def animation_creation_strategy() -> str:
            """Defines the preferred strategy for creating 3D animations"""
            return """When creating 3D animations, follow these best practices:

1. First understand the scene requirements:
   - What objects need to be in the scene
   - What movements or animations are needed
   - What camera angles and lighting are appropriate

2. For quick animations, use the create_and_render_animation() tool with a clear, detailed prompt.
   Example: "A red ball bouncing on a blue floor, the camera follows the ball"

3. For more complex animations:
   a. Start by creating a script with generate_animation_script()
   b. Validate the script with validate_animation_script()
   c. Modify the script as needed to add specific objects, materials, or animation logic
   d. Render the final animation with render_animation()

4. When crafting animation scripts, follow these guidelines:
   - Set appropriate frame ranges (typically 250 frames for a 10-second animation at 25fps)
   - Add sufficient lighting (usually a key light and fill light)
   - Position the camera to capture the full animation
   - For moving objects, create keyframes at regular intervals
   - For rotating objects, use radians() for rotation angles
   - Always include the export code at the end

5. For generating specific types of animations:
   - For bouncing balls: Create a sphere and keyframe its position in a parabolic motion
   - For rotating objects: Create the object and keyframe its rotation_euler property
   - For orbiting objects (like planets): Calculate positions using sine and cosine functions
   - For character animations: Consider using armatures (though these are complex)

Remember that clear, detailed prompts produce the best results. If the generated animation
doesn't meet expectations, try refining the prompt or manually adjusting the script.
"""
    
    def start(self):
        """Start the MCP server in a background thread"""
        if self.is_running:
            logger.warning("MCP server is already running")
            return
        
        # Function to run the server
        def run_server():
            try:
                logger.info("Starting MCP server")
                self.mcp.run(host="0.0.0.0", port=int(os.environ.get("MCP_PORT", 8000)))
            except Exception as e:
                logger.error(f"Error running MCP server: {str(e)}")
        
        # Start the server in a new thread
        self.server_thread = threading.Thread(target=run_server)
        self.server_thread.daemon = True  # Allow the thread to be terminated when the main thread exits
        self.server_thread.start()
        self.is_running = True
        
        logger.info("MCP server started in background thread")
    
    def stop(self):
        """Stop the MCP server"""
        if not self.is_running:
            logger.warning("MCP server is not running")
            return
        
        # Gracefully shut down the server
        try:
            logger.info("Stopping MCP server")
            # TODO: Add proper server shutdown mechanism when available in MCP
            self.is_running = False
        except Exception as e:
            logger.error(f"Error stopping MCP server: {str(e)}")
    
    def is_healthy(self) -> bool:
        """Check if the MCP server is healthy"""
        # First check if the server thread is alive
        if self.server_thread and not self.server_thread.is_alive():
            logger.error("MCP server thread is not running")
            return False
        
        # Then check if the Blender service is reachable
        return self.blender_service.check_health()
    
    def generate_script(self, prompt: str) -> str:
        """Generate a Blender script for the given prompt"""
        return generate_animation_script(prompt)
    
    def validate_script(self, script: str) -> Dict[str, Any]:
        """Validate a Blender script without rendering it"""
        return self.blender_service.validate_script(script)
    
    def render_animation(self, script: str, prompt: str = "") -> Dict[str, Any]:
        """Render an animation using the Blender service"""
        return self.blender_service.render_animation(script, prompt)
    
    def create_and_render_animation(self, prompt: str) -> Dict[str, Any]:
        """Create and render an animation from a prompt"""
        # First generate the script
        script = self.generate_script(prompt)
        
        # Validate the script
        validation_result = self.validate_script(script)
        if not validation_result.get("valid", False):
            return {"error": validation_result.get("error", "Unknown validation error")}
        
        # Render the animation
        return self.render_animation(script, prompt)

if __name__ == "__main__":
    # Create and run the MCP server directly
    mcp_server = AnimationMCPServer()
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 8000))
    
    # Run the server in the main thread (not in background)
    try:
        logger.info(f"Starting MCP server on port {port}")
        mcp_server.mcp.run(host="0.0.0.0", port=port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
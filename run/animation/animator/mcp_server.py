import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from mcp.server.fastmcp import FastMCP
import tempfile
import os
import uuid
import datetime
from google.cloud import storage
from functools import lru_cache

logger = logging.getLogger(__name__)

# Initialize MCP server
mcp = FastMCP("Animation MCP Server")

# Storage client functions
@lru_cache()
def get_storage_client():
    """Creates a storage client using the configured service account"""
    try:
        client = storage.Client()
        logger.info("Initialized storage client in MCP server")
        return client
    except Exception as e:
        logger.error(f"Error creating storage client in MCP server: {e}")
        raise

@lru_cache()
def get_bucket():
    """Gets the GCS bucket using the storage client"""
    bucket_name = os.getenv('GCS_BUCKET_NAME')
    if not bucket_name:
        raise ValueError("GCS_BUCKET_NAME environment variable is not set")
    client = get_storage_client()
    bucket = client.bucket(bucket_name)
    try:
        bucket.exists()
        return bucket
    except Exception as e:
        logger.error(f"Error accessing bucket {bucket_name} in MCP server: {e}")
        raise

# Blender classes for MCP server
class BlenderScriptValidator:
    @staticmethod
    def validate_script(script: str) -> Dict[str, Any]:
        """Validate the Blender script for security and required components."""
        try:
            # Check for forbidden terms
            forbidden_terms = ['subprocess', 'os.system', 'eval(', 'exec(']
            for term in forbidden_terms:
                if term in script:
                    return {
                        'valid': False,
                        'error': f'Script contains forbidden term: {term}'
                    }
            
            # Required components to check
            required_components = [
                'import sys',
                'import bpy',
                'sys.argv',
                'bpy.ops.export_scene.gltf(',
                'filepath=output_path',
                'export_format=\'GLB\'',
            ]
            
            for component in required_components:
                if component not in script:
                    return {
                        'valid': False,
                        'error': f'Script missing required component: {component}'
                    }
            
            # Check for incorrect camera creation syntax (common issue)
            if 'bpy.data.objects.new("Camera", "Camera", camera_data)' in script:
                return {
                    'valid': False,
                    'error': 'Incorrect camera creation syntax: too many arguments in bpy.data.objects.new()'
                }
            
            return {'valid': True}
        except Exception as e:
            return {
                'valid': False,
                'error': f'Validation error: {str(e)}'
            }

class BlenderRunner:
    @staticmethod
    def run_blender(script_path: str, output_path: str) -> dict:
        import subprocess
        try:
            # Create output directory and log paths
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Created output directory: {os.path.dirname(output_path)}")
            
            blender_path = "/usr/local/blender/blender"
            cmd = [
                blender_path,
                '--background',
                '--factory-startup',
                '--disable-autoexec',
                '--python', script_path,
                '--',
                output_path
            ]
            
            logger.info(f"Running Blender command via MCP")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if any(success_msg in result.stdout for success_msg in [
                "Successfully exported", 
                "Finished glTF 2.0 export"
            ]):
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'Blender error: {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error running Blender in MCP: {str(e)}")
            return {'success': False, 'error': str(e)}

class GCSUploader:
    def __init__(self, bucket):
        self.bucket = bucket
    
    def upload_file_with_script(self, animation_path: str, script_path: str) -> str:
        """Upload files to GCS and return signed URL"""
        try:
            # Generate a unique folder name
            folder_id = str(uuid.uuid4())
            base_path = f'animations/{folder_id}'
            
            # Upload animation
            animation_blob_name = f'{base_path}/animation.glb'
            animation_blob = self.bucket.blob(animation_blob_name)
            with open(animation_path, 'rb') as file_obj:
                animation_blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded animation via MCP to {animation_blob_name}")
            
            # Upload script 
            script_blob_name = f'{base_path}/script.py'
            script_blob = self.bucket.blob(script_blob_name)
            with open(script_path, 'rb') as file_obj:
                script_blob.upload_from_file(file_obj)
            
            # Generate signed URL
            url = animation_blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="GET",
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Error in GCS operation via MCP: {str(e)}")
            raise

# Initialize storage components
try:
    bucket = get_bucket()
    logger.info("Successfully initialized MCP server storage component")
except Exception as e:
    logger.error(f"Failed to initialize MCP server components: {str(e)}")
    raise

@mcp.tool()
def validate_blender_script(script: str) -> Dict[str, Any]:
    """
    Validate a Blender Python script for security and required components.
    
    Args:
        script: The Blender Python script to validate
        
    Returns:
        Dict containing validation result with 'valid' boolean and optional 'error' message
    """
    logger.info("Validating Blender script via MCP")
    validator = BlenderScriptValidator()
    result = validator.validate_script(script)
    
    return {
        "valid": result.get("valid", False),
        "error": result.get("error", ""),
        "message": "Script validation completed"
    }

@mcp.tool()
def render_animation(script: str, prompt: Optional[str] = None) -> Dict[str, Any]:
    """
    Render a 3D animation from a Blender Python script.
    
    Args:
        script: The Blender Python script to execute
        prompt: Optional prompt describing the animation (for logging)
        
    Returns:
        Dict containing signed_url for the rendered animation or error details
    """
    logger.info(f"Rendering animation via MCP with prompt: {prompt}")
    
    try:
        # First validate the script
        validator = BlenderScriptValidator()
        validation_result = validator.validate_script(script)
        
        if not validation_result['valid']:
            return {
                "success": False,
                "error": validation_result['error'],
                "signed_url": None
            }
        
        # Script is valid, proceed with rendering
        blender_runner = BlenderRunner()
        gcs_uploader = GCSUploader(bucket)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            # Write the script to file
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Run Blender
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                try:
                    # Upload to GCS and get signed URL
                    signed_url = gcs_uploader.upload_file_with_script(output_path, script_path)
                    return {
                        "success": True,
                        "signed_url": signed_url,
                        "expiration": "15 minutes",
                        "error": None
                    }
                except Exception as upload_error:
                    logger.error(f"Upload error in MCP: {str(upload_error)}")
                    return {
                        "success": False,
                        "error": f"Failed to upload animation: {str(upload_error)}",
                        "signed_url": None
                    }
            else:
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown rendering error'),
                    "signed_url": None
                }
    
    except Exception as e:
        logger.error(f"Error rendering animation via MCP: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "signed_url": None
        }

@mcp.resource("animation://status")
def get_animation_status() -> str:
    """
    Get the current status of the animation service.
    
    Returns:
        Service status information
    """
    try:
        # Test bucket connectivity
        bucket = get_bucket()
        bucket_accessible = bucket.exists()
        
        status = {
            "service": "Animation MCP Server",
            "status": "healthy",
            "bucket_accessible": bucket_accessible,
            "blender_available": os.path.exists("/usr/local/blender/blender"),
            "capabilities": [
                "validate_blender_script",
                "render_animation"
            ]
        }
        return json.dumps(status, indent=2)
    except Exception as e:
        error_status = {
            "service": "Animation MCP Server",
            "status": "error",
            "error": str(e)
        }
        return json.dumps(error_status, indent=2)

@mcp.resource("animation://templates/{template_name}")
def get_animation_template(template_name: str) -> str:
    """
    Get a Blender script template for common animations.
    
    Args:
        template_name: Name of the template (e.g., 'cube_rotate', 'sphere_bounce')
        
    Returns:
        Blender Python script template
    """
    templates = {
        "cube_rotate": '''
import sys
import bpy
import bmesh
from mathutils import Vector

# Get the output path from command line arguments
if len(sys.argv) > sys.argv.index("--") + 1:
    output_path = sys.argv[sys.argv.index("--") + 1]
else:
    output_path = "/tmp/animation.glb"

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create a cube
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "RotatingCube"

# Add rotation animation
cube.rotation_euler = (0, 0, 0)
cube.keyframe_insert(data_path="rotation_euler", frame=1)

cube.rotation_euler = (0, 0, 6.28319)  # 360 degrees in radians
cube.keyframe_insert(data_path="rotation_euler", frame=120)

# Set frame range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 120

# Create camera
bpy.ops.object.camera_add(location=(7, -7, 5))
camera = bpy.context.active_object
camera.rotation_euler = (1.1, 0, 0.785)

# Create light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))

# Export as GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True
)
''',
        "sphere_bounce": '''
import sys
import bpy
import bmesh
from mathutils import Vector

# Get the output path from command line arguments
if len(sys.argv) > sys.argv.index("--") + 1:
    output_path = sys.argv[sys.argv.index("--") + 1]
else:
    output_path = "/tmp/animation.glb"

# Clear existing mesh objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Create a sphere
bpy.ops.mesh.primitive_uv_sphere_add(location=(0, 0, 5))
sphere = bpy.context.active_object
sphere.name = "BouncingSphere"

# Add bouncing animation
sphere.location = (0, 0, 5)
sphere.keyframe_insert(data_path="location", frame=1)

sphere.location = (0, 0, 1)
sphere.keyframe_insert(data_path="location", frame=30)

sphere.location = (0, 0, 5)
sphere.keyframe_insert(data_path="location", frame=60)

# Set frame range
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 60

# Create camera
bpy.ops.object.camera_add(location=(7, -7, 5))
camera = bpy.context.active_object
camera.rotation_euler = (1.1, 0, 0.785)

# Create light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))

# Export as GLB
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True
)
'''
    }
    
    if template_name in templates:
        return templates[template_name]
    else:
        available = ", ".join(templates.keys())
        return f"Template '{template_name}' not found. Available templates: {available}"

# Function to run the MCP server
def run_mcp_server():
    """Run the MCP server"""
    import uvicorn
    from mcp.server.fastmcp.server import run_server
    
    logger.info("Starting Animation MCP Server")
    
    # Run the MCP server
    run_server(mcp)

if __name__ == "__main__":
    run_mcp_server()
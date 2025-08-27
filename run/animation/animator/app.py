from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.cloud import storage
import os
import subprocess
import tempfile
import uuid
import logging
import datetime
from functools import lru_cache
from typing import Dict, Any, Optional
import json
import asyncio
import time
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project ID for logging
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

# Pydantic models for request/response
class ScriptRequest(BaseModel):
    script: str
    prompt: Optional[str] = None

class ValidationResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    message: Optional[str] = None

class RenderResponse(BaseModel):
    success: bool
    signed_url: Optional[str] = None
    error: Optional[str] = None
    expiration: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    time: str

class MCPStatusResponse(BaseModel):
    mcp_available: bool
    service: str
    capabilities: list
    blender_available: bool
    bucket_configured: bool
    timestamp: str
    error: Optional[str] = None

@lru_cache()
def get_storage_client():
    """Creates a storage client using the configured service account"""
    try:
        client = storage.Client()
        logger.info("Initialized storage client")
        return client
    except Exception as e:
        logger.error(f"Error creating storage client: {e}")
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
        logger.error(f"Error accessing bucket {bucket_name}: {e}")
        raise

# Initialize storage components
try:
    bucket = get_bucket()
    logger.info("Successfully initialized storage component")
except Exception as e:
    logger.error(f"Failed to initialize components: {str(e)}")
    raise

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
        try:
            # Create output directory and log paths
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Created output directory: {os.path.dirname(output_path)}")
            logger.info(f"Script path: {os.path.abspath(script_path)}")
            logger.info(f"Output path: {os.path.abspath(output_path)}")
            
            # Log script content for debugging
            with open(script_path, 'r') as f:
                script_content = f.read()
            logger.info("Generated Blender script content:")
            logger.info(script_content)
            
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
            
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Log Blender output
            logger.info(f"Blender stdout: {result.stdout}")
            if result.stderr:
                logger.info(f"Blender stderr: {result.stderr}")
            
            # Verify file existence after Blender execution
            logger.info(f"Checking if output file exists at: {output_path}")
            if os.path.exists(output_path):
                logger.info(f"Output file exists with size: {os.path.getsize(output_path)} bytes")
            else:
                logger.error(f"Output file does not exist at: {output_path}")
                # Check common alternative locations
                common_paths = [
                    '/app/output.glb',
                    './output.glb',
                    os.path.join(os.path.dirname(script_path), 'output.glb')
                ]
                for path in common_paths:
                    if os.path.exists(path):
                        logger.error(f"Found file at incorrect location: {path}")
            
            if any(success_msg in result.stdout for success_msg in [
                "Successfully exported", 
                "Finished glTF 2.0 export"
            ]):
                return {'success': True}
            else:
                if "could not get a list of mounted file-systems" not in result.stderr:
                    logger.error(f"Blender stderr: {result.stderr}")
                return {
                    'success': False,
                    'error': f'Blender error: {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error running Blender: {str(e)}")
            return {'success': False, 'error': str(e)}

class GCSUploader:
    def __init__(self, bucket):
        self.bucket = bucket
    
    def upload_file_with_script(self, animation_path: str, script_path: str) -> str:
        """
        Uploads both animation and script files to GCS and returns animation signed URL.
        
        Args:
            animation_path (str): Path to the local animation file
            script_path (str): Path to the local script file
            
        Returns:
            str: Signed URL for downloading the animation file
            
        Raises:
            Exception: If upload or URL generation fails
        """
        try:
            # Generate a unique folder name for this animation set
            folder_id = str(uuid.uuid4())
            base_path = f'animations/{folder_id}'
            
            # Upload animation
            animation_blob_name = f'{base_path}/animation.glb'
            animation_blob = self.bucket.blob(animation_blob_name)
            with open(animation_path, 'rb') as file_obj:
                animation_blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded animation to {animation_blob_name}")
            
            # Upload script (for debugging purposes)
            script_blob_name = f'{base_path}/script.py'
            script_blob = self.bucket.blob(script_blob_name)
            with open(script_path, 'rb') as file_obj:
                script_blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded script to {script_blob_name}")
            
            # Generate signed URL only for animation
            url = animation_blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="GET",
            )
            
            logger.info(f"Generated signed URL for animation in {base_path}")
            return url
            
        except Exception as e:
            logger.error(f"Error in GCS operation: {str(e)}")
            raise

# Initialize FastAPI app
app = FastAPI(title="Animation Service", description="Blender animation rendering service with MCP support")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get('/health', response_model=HealthResponse)
async def health():
    """Basic endpoint for Cloud Run startup probe."""
    try:
        return HealthResponse(
            status='healthy',
            time=datetime.datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/render', response_model=RenderResponse)
async def render(request: ScriptRequest):
    """Endpoint for rendering a Blender script received from LangGraph."""
    try:
        # First, validate the script for security
        validator = BlenderScriptValidator()
        validation_result = validator.validate_script(request.script)
        
        if not validation_result['valid']:
            raise HTTPException(status_code=400, detail=validation_result['error'])
        
        # Script is valid, proceed with rendering
        blender_runner = BlenderRunner()
        gcs_uploader = GCSUploader(bucket)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            with open(script_path, 'w') as f:
                f.write(request.script)
            
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                try:
                    signed_url = gcs_uploader.upload_file_with_script(output_path, script_path)
                    return RenderResponse(
                        success=True,
                        signed_url=signed_url,
                        expiration='15 minutes'
                    )
                except Exception as upload_error:
                    logger.error(f"Upload error: {str(upload_error)}")
                    raise HTTPException(
                        status_code=500,
                        detail=f'Failed to upload animation or generate signed URL: {str(upload_error)}'
                    )
            else:
                raise HTTPException(status_code=500, detail=result['error'])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/validate', response_model=ValidationResponse)
async def validate_script(request: ScriptRequest):
    """Endpoint for validating a Blender script without executing it."""
    try:
        # Validate the script
        validator = BlenderScriptValidator()
        validation_result = validator.validate_script(request.script)
        
        if not validation_result['valid']:
            return ValidationResponse(
                valid=False,
                error=validation_result['error']
            )
            
        # Basic syntax check - look for potential issues
        issues = []
        
        # Check for potential issues with camera creation
        if 'bpy.data.objects.new(' in request.script:
            camera_lines = [line for line in request.script.split('\n') 
                           if 'bpy.data.objects.new(' in line and 'camera' in line.lower()]
            for line in camera_lines:
                if line.count(',') > 1:  # More than one comma indicates potential issue
                    issues.append(f"Potential issue with camera creation: {line.strip()}")
        
        return ValidationResponse(
            valid=True,
            message=f"Script validation passed. {len(issues)} potential issues found." if issues else "Script validation passed."
        )
    
    except Exception as e:
        logger.error(f"Error validating script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Keep the original /generate endpoint for backward compatibility
@app.post('/generate')
async def generate(request: ScriptRequest):
    """Deprecated endpoint - use Vertex AI Reasoning Engine."""
    raise HTTPException(
        status_code=400,
        detail='This endpoint is deprecated. Please use Vertex AI Reasoning Engine.'
    )

# MCP Integration
async def run_mcp_server_background():
    """Run MCP server in background"""
    try:
        from mcp_server import mcp
        from mcp.server.fastmcp.server import run_server
        logger.info("Starting MCP server in background")
        await run_server(mcp)
    except Exception as e:
        logger.error(f"Error running MCP server: {str(e)}")

# SSE endpoint for agent communication
@app.get('/mcp/stream')
async def mcp_stream():
    """Server-Sent Events endpoint for MCP agent communication"""
    async def generate():
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connection', 'status': 'connected', 'timestamp': datetime.datetime.utcnow().isoformat()})}\n\n"
            
            # Keep the connection alive and send periodic updates
            while True:
                # Send heartbeat
                yield f"data: {json.dumps({'type': 'heartbeat', 'timestamp': datetime.datetime.utcnow().isoformat()})}\n\n"
                await asyncio.sleep(30)  # Send heartbeat every 30 seconds
                
        except Exception as e:
            logger.error(f"Error in MCP SSE stream: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type='text/event-stream')

@app.get('/mcp/status', response_model=MCPStatusResponse)
async def mcp_status():
    """Get MCP server status"""
    try:
        # Test MCP server availability
        return MCPStatusResponse(
            mcp_available=True,
            service="Animation MCP Server",
            capabilities=[
                "validate_blender_script",
                "render_animation",
                "get_animation_status",
                "get_animation_template"
            ],
            blender_available=os.path.exists("/usr/local/blender/blender"),
            bucket_configured=bool(os.getenv('GCS_BUCKET_NAME')),
            timestamp=datetime.datetime.utcnow().isoformat()
        )
    except Exception as e:
        return MCPStatusResponse(
            mcp_available=False,
            service="Animation MCP Server",
            capabilities=[],
            blender_available=False,
            bucket_configured=False,
            timestamp=datetime.datetime.utcnow().isoformat(),
            error=str(e)
        )

@app.post('/mcp/validate', response_model=ValidationResponse)
async def mcp_validate(request: ScriptRequest):
    """MCP endpoint for script validation"""
    try:
        # Use the existing validator
        validator = BlenderScriptValidator()
        result = validator.validate_script(request.script)
        
        return ValidationResponse(
            valid=result.get("valid", False),
            error=result.get("error", ""),
            message="Script validation completed via MCP endpoint"
        )
        
    except Exception as e:
        logger.error(f"Error in MCP validate endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/mcp/render', response_model=RenderResponse)
async def mcp_render(request: ScriptRequest):
    """MCP endpoint for animation rendering"""
    try:
        # Use existing validation and rendering logic
        validator = BlenderScriptValidator()
        validation_result = validator.validate_script(request.script)
        
        if not validation_result['valid']:
            return RenderResponse(
                success=False,
                error=validation_result['error']
            )
        
        # Render the animation
        blender_runner = BlenderRunner()
        gcs_uploader = GCSUploader(bucket)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            with open(script_path, 'w') as f:
                f.write(request.script)
            
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                try:
                    signed_url = gcs_uploader.upload_file_with_script(output_path, script_path)
                    return RenderResponse(
                        success=True,
                        signed_url=signed_url,
                        expiration="15 minutes"
                    )
                except Exception as upload_error:
                    logger.error(f"Upload error in MCP render: {str(upload_error)}")
                    return RenderResponse(
                        success=False,
                        error=f"Failed to upload animation: {str(upload_error)}"
                    )
            else:
                return RenderResponse(
                    success=False,
                    error=result.get('error', 'Unknown rendering error')
                )
    
    except Exception as e:
        logger.error(f"Error in MCP render endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Initialize MCP server on startup"""
    logger.info("Starting Animation Service with MCP support")
    
    # Start MCP server in background
    asyncio.create_task(run_mcp_server_background())

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
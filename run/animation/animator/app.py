from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.cloud import storage
import os
import subprocess
import tempfile
import uuid
import logging
import datetime
from functools import lru_cache
from typing import Dict, Any

app = FastAPI(title="Animator Service", description="3D Animation rendering service using Blender")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project ID for logging
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

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

class RenderRequest(BaseModel):
    script: str
    prompt: str = "No prompt provided"

class ValidateRequest(BaseModel):
    script: str

class GenerateRequest(BaseModel):
    prompt: str

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

@app.get("/health")
async def health():
    """Basic endpoint for Cloud Run startup probe."""
    try:
        return {
            'status': 'healthy',
            'time': datetime.datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'status': 'unhealthy',
            'error': str(e)
        })

@app.post("/render")
async def render(request: RenderRequest):
    """Endpoint for rendering a Blender script received from LangGraph."""
    script = request.script
    prompt = request.prompt
    
    try:
        # First, validate the script for security
        validator = BlenderScriptValidator()
        validation_result = validator.validate_script(script)
        
        if not validation_result['valid']:
            raise HTTPException(status_code=400, detail={'error': validation_result['error']})
        
        # Script is valid, proceed with rendering
        blender_runner = BlenderRunner()
        gcs_uploader = GCSUploader(bucket)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            with open(script_path, 'w') as f:
                f.write(script)
            
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                try:
                    signed_url = gcs_uploader.upload_file_with_script(output_path, script_path)
                    return {
                        'signed_url': signed_url,
                        'expiration': '15 minutes'
                    }
                except Exception as upload_error:
                    logger.error(f"Upload error: {str(upload_error)}")
                    raise HTTPException(status_code=500, detail={
                        'error': 'Failed to upload animation or generate signed URL',
                        'details': str(upload_error)
                    })
            raise HTTPException(status_code=500, detail={'error': result['error']})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail={'error': str(e)})

@app.post("/validate")
async def validate_script(request: ValidateRequest):
    """Endpoint for validating a Blender script without executing it."""
    script = request.script
    
    try:
        # Validate the script
        validator = BlenderScriptValidator()
        validation_result = validator.validate_script(script)
        
        if not validation_result['valid']:
            raise HTTPException(status_code=400, detail={
                'valid': False,
                'error': validation_result['error']
            })
            
        # Basic syntax check - look for potential issues
        issues = []
        
        # Check for potential issues with camera creation
        if 'bpy.data.objects.new(' in script:
            camera_lines = [line for line in script.split('\n') 
                           if 'bpy.data.objects.new(' in line and 'camera' in line.lower()]
            for line in camera_lines:
                if line.count(',') > 1:  # More than one comma indicates potential issue
                    issues.append(f"Potential issue with camera creation: {line.strip()}")
        
        return {
            'valid': True,
            'potential_issues': issues
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating script: {str(e)}")
        raise HTTPException(status_code=500, detail={
            'valid': False,
            'error': str(e)
        })

# Keep the original /generate endpoint for backward compatibility
@app.post("/generate")
async def generate(request: GenerateRequest):
    raise HTTPException(status_code=400, detail={
        'error': 'This endpoint is deprecated. Please use Vertex AI Reasoning Engine.'
    })

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
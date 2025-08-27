from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import subprocess
import tempfile
import logging
import datetime
from typing import Dict, Any

app = FastAPI(title="Simplified Animator Service", description="3D Animation rendering service using Blender (GCS logic removed)")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get project ID for logging
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')

class RenderRequest(BaseModel):
    script: str
    prompt: str = "No prompt provided"

class ValidateRequest(BaseModel):
    script: str

# Validation logic moved to ADK validation agent
# This service now trusts that scripts have been pre-validated by the agent layer

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
                return {'success': True, 'output_path': output_path}
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

@app.get("/health")
async def health():
    """Basic endpoint for Cloud Run startup probe."""
    try:
        return {
            'status': 'healthy',
            'time': datetime.datetime.utcnow().isoformat(),
            'service': 'simplified-animator'
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            'status': 'unhealthy',
            'error': str(e)
        })

@app.post("/render")
async def render(request: RenderRequest):
    """
    Endpoint for rendering a Blender script - returns local file path instead of uploading to GCS.
    
    Note: 
    - GCS upload logic has been moved to the ADK storage agent
    - Script validation has been moved to the ADK validation agent
    - This service now only handles Blender rendering and trusts pre-validated scripts
    """
    script = request.script
    prompt = request.prompt
    
    try:
        # Script validation is now handled by the ADK validation agent
        # This service trusts that scripts have been pre-validated
        logger.info("Received pre-validated script for rendering")
        
        # Proceed directly with rendering
        blender_runner = BlenderRunner()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            with open(script_path, 'w') as f:
                f.write(script)
            
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                # Instead of uploading to GCS, return the file path for the storage agent
                # In a real implementation, this would be coordinated through the ADK workflow
                
                # Read the file content to return it (temporary solution)
                with open(output_path, 'rb') as f:
                    file_size = len(f.read())
                
                return {
                    'status': 'success',
                    'file_path': output_path,  # Local path - ADK storage agent will handle upload
                    'file_size': file_size,
                    'message': 'Animation rendered successfully. File ready for upload by storage agent.'
                }
            else:
                raise HTTPException(status_code=500, detail={'error': result['error']})
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail={'error': str(e)})

@app.post("/validate")
async def validate_script(request: ValidateRequest):
    """
    Legacy validation endpoint - now deprecated.
    
    Script validation has been moved to the ADK validation agent.
    This endpoint is maintained for backward compatibility but returns a deprecation message.
    """
    return {
        'valid': False,
        'error': 'Script validation has been moved to the ADK validation agent. This endpoint is deprecated.',
        'message': 'Please use the ADK agent service for script validation.',
        'deprecated': True
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
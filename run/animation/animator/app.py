from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import storage
import google.auth
import os
import subprocess
import tempfile
import uuid
import logging
import datetime
from functools import lru_cache

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@lru_cache()
def get_storage_client():
    """Creates a storage client using application default credentials"""
    try:
        credentials, project = google.auth.default()
        client = storage.Client(
            project=project,
            credentials=credentials
        )
        # Test the credentials with a simple operation
        logger.info(f"Initialized storage client with project: {project}")
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
        # Test if we can access the bucket
        bucket.exists()
        return bucket
    except Exception as e:
        logger.error(f"Error accessing bucket {bucket_name}: {e}")
        raise

@lru_cache()
def get_llm():
    """Creates the LLM instance using the API key"""
    api_key = os.getenv('ANIMATOR_KEY_SECRET')
    if not api_key:
        raise ValueError("ANIMATOR_KEY_SECRET environment variable is not set")
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192,
        google_api_key=api_key
    )

# Initialize components
try:
    bucket = get_bucket()
    llm = get_llm()
    logger.info("Successfully initialized storage and LLM components")
except Exception as e:
    logger.error(f"Failed to initialize components: {str(e)}")
    raise

# System prompt for script generation
BLENDER_PROMPT = """Create a Python script for Blender that will generate a 3D animation based on this description:
{user_prompt}

The script must include these essential components:

1. Basic Setup:
   - Import bpy (Blender Python API)
   - Clear existing objects
   - Set frame range (start=1, end=250 for 10-second animation at 25fps)

2. Camera Setup:
   - Create camera at good viewing distance
   - Set camera parameters
   - Add camera motion if appropriate
   - Parent camera to empty object
   - Set up camera constraints

3. Lighting Setup:
   - Create key, fill, and rim lights
   - Set light energy and color values

4. Scene Requirements:
   - Create 3D objects and animation
   - Apply materials and textures
   - Set up environment lighting
   - Configure render settings

5. Animation Export:
   - Set up GLB export settings
   - Use provided output_path
   - Enable animation data
   - Include cameras and lights

The script must run without GUI (headless mode) and include proper error handling."""

class BlenderScriptGenerator:
    def generate(self, prompt: str) -> str:
        try:
            response = llm.invoke(BLENDER_PROMPT.format(user_prompt=prompt))
            script = response.content
            logger.info("Generated Blender script successfully")
            return self.validate_script(script)
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise

    def validate_script(self, script: str) -> str:
        forbidden_terms = ['subprocess']
        for term in forbidden_terms:
            if term in script:
                raise ValueError(f'Generated script contains forbidden term: {term}')
        return script

class BlenderRunner:
    @staticmethod
    def run_blender(script_path: str, output_path: str) -> dict:
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            logger.info(f"Output directory created: {os.path.dirname(output_path)}")
            
            result = subprocess.run([
                'blender',
                '--background',
                '--factory-startup',
                '--disable-autoexec',
                '--python', script_path,
                '--',
                output_path
            ], capture_output=True, text=True)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return {'success': True}
            else:
                return {
                    'success': False,
                    'error': f'Blender error (code {result.returncode}): {result.stderr}'
                }
        except Exception as e:
            logger.error(f"Error running Blender: {str(e)}")
            return {'success': False, 'error': str(e)}

class GCSUploader:
    def __init__(self, bucket):
        self.bucket = bucket
    
    def upload_file(self, local_path: str) -> str:
        try:
            # Create a unique path for the animation
            gcs_path = f'animations/{uuid.uuid4()}.glb'
            blob = self.bucket.blob(gcs_path)
            
            # Upload the file
            with open(local_path, 'rb') as file_obj:
                blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded file to {gcs_path}")
            
            # Generate signed URL with explicit expiration
            url = blob.generate_signed_url(
                version='v4',
                expiration=datetime.timedelta(minutes=60),
                method='GET'
            )
            return url
        except Exception as e:
            logger.error(f"Error uploading to GCS: {str(e)}")
            raise

@app.route('/generate', methods=['POST'])
def generate():
    if not request.content_type or 'application/json' not in request.content_type:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({'error': 'Invalid JSON format'}), 400
    
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        # Initialize components
        script_generator = BlenderScriptGenerator()
        blender_runner = BlenderRunner()
        gcs_uploader = GCSUploader(bucket)
        
        # Generate script
        script = script_generator.generate(prompt)
        logger.info("Script generation completed")
        
        # Create temporary directory for files
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            # Save script
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Run Blender
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                # Upload to GCS
                url = gcs_uploader.upload_file(output_path)
                return jsonify({'animation_url': url})
            else:
                return jsonify({'error': result['error']}), 500
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
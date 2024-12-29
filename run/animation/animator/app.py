from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import storage
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
    """Creates a storage client using Cloud Run's default credentials"""
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

@lru_cache()
def get_llm():
    """Creates the LLM instance using the environment variable GOOGLE_API_KEY"""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=1,
            top_p=0.95,
            max_output_tokens=8192
        )
        logger.info("Successfully initialized LLM")
        return llm
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {str(e)}")
        raise

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

The script must include these essential components in this exact order:

1. Basic Setup:
   - Import bpy (Blender Python API)
   - Clear existing objects
   - Set frame range (start=1, end=250 for 10-second animation at 25fps)
   - Create a new world if it doesn't exist (bpy.data.worlds.new("World"))
   - Link the world to the scene (bpy.context.scene.world = bpy.data.worlds["World"])

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
   - Use bpy.ops.export_scene.gltf() for export (NOT bpy.ops.export.gltf)
   - Set the filepath to output_path
   - Set export_format='GLB'
   - Enable export_animations=True
   - Enable export_cameras=True
   - Enable export_lights=True

The script must run without GUI (headless mode) and include proper error handling.

Important: Use EXACTLY this export code:
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_animations=True,
    export_cameras=True,
    export_lights=True
)"""

class BlenderScriptGenerator:
    def generate(self, prompt: str) -> str:
        try:
            logger.info("Sending prompt to LLM")
            response = llm.invoke(BLENDER_PROMPT.format(user_prompt=prompt))
            logger.info(f"LLM Response type: {type(response)}")
            
            # Log full response to GCS
            try:
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                log_path = f'debug_logs/{timestamp}_llm_response.txt'
                blob = bucket.blob(log_path)
                
                log_content = f"""
Timestamp: {timestamp}
Prompt: {prompt}
Response Type: {type(response)}
Raw Response: {response}
"""
                
                blob.upload_from_string(log_content)
                logger.info(f"Logged LLM response to GCS: {log_path}")
            except Exception as e:
                logger.error(f"Failed to log to GCS: {str(e)}")
            
            if not response:
                logger.error("LLM returned None response")
                raise ValueError("Invalid response from LLM")
            
            # Extract content from AIMessage
            if hasattr(response, 'content'):
                raw_content = response.content
            else:
                raw_content = str(response)
            
            # Extract script from between triple backticks
            if '```python' in raw_content and '```' in raw_content:
                script = raw_content.split('```python')[1].split('```')[0].strip()
                logger.info("Successfully extracted Python script from response")
            else:
                script = raw_content
                logger.info("Using full response as script (no code blocks found)")
                
            if not script:
                logger.error("Generated script is empty")
                raise ValueError("Empty script generated")
                
            logger.info(f"Script length: {len(script)} characters")
            return self.validate_script(script)
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            raise ValueError(f"Failed to generate script: {str(e)}")

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
            logger.info(f"Created output directory: {os.path.dirname(output_path)}")
            
            blender_path = "/usr/local/blender/blender"
            logger.info(f"Using Blender at: {blender_path}")
            
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
            logger.info(f"Blender stdout: {result.stdout}")
            
            # Check if "Successfully exported" or "Finished glTF 2.0 export" is in output
            if any(success_msg in result.stdout for success_msg in [
                "Successfully exported", 
                "Finished glTF 2.0 export"
            ]):
                return {'success': True}
            else:
                # Only log as error if there's a real problem
                if "could not get a list of mounted file-systems" not in result.stderr or not "Finished glTF 2.0 export" in result.stdout:
                    logger.error(f"Blender stderr: {result.stderr}")
                    logger.error(f"Blender stdout: {result.stdout}")
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
    
    def upload_file(self, local_path: str) -> str:
        try:
            gcs_path = f'animations/{uuid.uuid4()}.glb'
            blob = self.bucket.blob(gcs_path)
            
            with open(local_path, 'rb') as file_obj:
                blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded file to {gcs_path}")
            
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
    except Exception:
        return jsonify({'error': 'Invalid JSON format'}), 400
    
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        script_generator = BlenderScriptGenerator()
        blender_runner = BlenderRunner()
        gcs_uploader = GCSUploader(bucket)
        
        script = script_generator.generate(prompt)
        logger.info("Script generation completed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            with open(script_path, 'w') as f:
                f.write(script)
            
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                url = gcs_uploader.upload_file(output_path)
                return jsonify({'animation_url': url})
            return jsonify({'error': result['error']}), 500
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

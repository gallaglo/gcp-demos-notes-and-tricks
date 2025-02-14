from flask import Flask, request, jsonify
from langchain_google_vertexai import ChatVertexAI
from google.cloud import storage
import vertexai
import os
import subprocess
import tempfile
import uuid
import logging
import datetime
from functools import lru_cache
from prompts import BLENDER_PROMPT

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
vertexai.init(project=project_id, location=location)

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

@lru_cache()
def get_llm():
    """Creates the LLM instance using the environment variable GOOGLE_API_KEY"""
    try:
        llm = ChatVertexAI(
            model_name="gemini-1.5-flash-002",  # Using Flash model
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=2048,  # Flash has lower token limit
            request_timeout=60,  # Flash typically needs less time
            max_retries=3
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

class BlenderScriptGenerator:
    def generate(self, prompt: str) -> str:
        try:
            logger.info("Sending prompt to LLM")
            # Use the LangChain prompt template
            formatted_prompt = BLENDER_PROMPT.format(user_prompt=prompt)
            response = llm.invoke(formatted_prompt)
            
            # Extract content from AIMessage
            if hasattr(response, 'content'):
                raw_content = response.content
            else:
                raw_content = str(response)
            
            # Extract script from between triple backticks
            if '```python' in raw_content and '```' in raw_content:
                script = raw_content.split('```python')[1].split('```')[0].strip()
            else:
                script = raw_content.strip()
                
            if not script:
                logger.error("Generated script is empty")
                raise ValueError("Empty script generated")
            
            # Inject the command-line argument handling
            script = self._modify_script_for_output_path(script)
            
            # Validate script has required components
            self._validate_script_requirements(script)
            
            return script
        except Exception as e:
            logger.error(f"Error generating script: {str(e)}")
            raise ValueError(f"Failed to generate script: {str(e)}")

    def _modify_script_for_output_path(self, script: str) -> str:
        # Remove any existing output path assignments
        lines = script.split('\n')
        filtered_lines = [
            line for line in lines 
            if not ('output_path =' in line and 'os.path' in line)
        ]
        
        # Find the position after the imports
        import_end_idx = 0
        for i, line in enumerate(filtered_lines):
            if line.strip().startswith('import '):
                import_end_idx = i + 1
        
        # Insert our path handling code
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

    def _validate_script_requirements(self, script: str) -> None:
        # Check for forbidden terms
        forbidden_terms = ['subprocess']
        for term in forbidden_terms:
            if term in script:
                raise ValueError(f'Generated script contains forbidden term: {term}')
        
        # Required components to check
        required_components = [
            'import sys',
            'sys.argv',
            'bpy.ops.export_scene.gltf(',
            'filepath=output_path',
            'export_format=\'GLB\'',
        ]
        
        for component in required_components:
            if component not in script:
                raise ValueError(f'Generated script missing required component: {component}')

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
    
    def upload_file(self, local_path: str) -> str:
        """
        Uploads a file to GCS and returns a signed URL for downloading.
        
        Args:
            local_path (str): Path to the local file to upload
            
        Returns:
            str: Signed URL for downloading the file
            
        Raises:
            Exception: If upload or URL generation fails
        """
        try:
            # Generate a unique path for the animation
            blob_name = f'animations/{uuid.uuid4()}.glb'
            blob = self.bucket.blob(blob_name)
            
            # Upload the file
            with open(local_path, 'rb') as file_obj:
                blob.upload_from_file(file_obj)
            logger.info(f"Successfully uploaded file to {blob_name}")
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=datetime.timedelta(minutes=15),
                method="GET",
            )
            
            logger.info(f"Generated signed URL for {blob_name}")
            return url
            
        except Exception as e:
            logger.error(f"Error in GCS operation: {str(e)}")
            raise

@app.route('/health')
def health():
    """Basic endpoint for Cloud Run startup probe."""
    try:
        return jsonify({
            'status': 'healthy',
            'time': datetime.datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

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
                try:
                    signed_url = gcs_uploader.upload_file(output_path)
                    return jsonify({
                        'signed_url': signed_url,
                        'expiration': '15 minutes'
                    })
                except Exception as upload_error:
                    logger.error(f"Upload error: {str(upload_error)}")
                    return jsonify({
                        'error': 'Failed to upload animation or generate signed URL',
                        'details': str(upload_error)
                    }), 500
            return jsonify({'error': result['error']}), 500
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
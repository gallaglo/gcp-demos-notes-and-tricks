from flask import Flask, request, jsonify
from langchain_google_vertexai import ChatVertexAI
from google.cloud import storage
import vertexai
import tempfile
import os
import logging
from functools import lru_cache

from script_generator import BlenderScriptGenerator
from blender_runner import BlenderRunner
from gcs_uploader import GCSUploader
from prompts import blender_prompt

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Vertex AI
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
location = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
vertexai.init(project=project_id, location=location)

@lru_cache()
def get_components():
    """Initialize and cache all components"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(os.getenv('GCS_BUCKET_NAME'))
    
    llm = ChatVertexAI(
        model_name="gemini-1.0-flash-pro",  # Using Flash model
        temperature=1.0,
        top_p=0.95,
        max_output_tokens=2048,  # Flash has lower token limit
        request_timeout=60,  # Flash typically needs less time
        max_retries=3
    )
    
    script_generator = BlenderScriptGenerator(llm)
    blender_runner = BlenderRunner()
    gcs_uploader = GCSUploader(bucket)
    
    return script_generator, blender_runner, gcs_uploader

@app.route('/generate', methods=['POST'])
def generate():
    if not request.content_type or 'application/json' not in request.content_type:
        logger.error(f"Invalid content type: {request.content_type}")
        return jsonify({'error': 'Request must be JSON'}), 400
    
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        logger.info(f"Received prompt: {prompt}")
        
        if not prompt:
            logger.error("No prompt provided in request")
            return jsonify({'error': 'No prompt provided'}), 400
        
        script_generator, blender_runner, gcs_uploader = get_components()
        
        # Generate script
        logger.info("Starting script generation")
        script = script_generator.generate(prompt)
        logger.info("Script generation completed successfully")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            logger.info(f"Writing script to {script_path}")
            with open(script_path, 'w') as f:
                f.write(script)
            
            logger.info("Running Blender")
            result = blender_runner.run_blender(script_path, output_path)
            
            if result['success']:
                try:
                    logger.info("Uploading to GCS")
                    signed_url = gcs_uploader.upload_file(output_path)
                    logger.info("Upload successful")
                    return jsonify({
                        'signed_url': signed_url,
                        'expiration': '15 minutes'
                    })
                except Exception as upload_error:
                    logger.error(f"Upload error: {str(upload_error)}")
                    return jsonify({
                        'error': 'Failed to upload animation',
                        'details': str(upload_error)
                    }), 500
            
            logger.error(f"Blender error: {result['error']}")
            return jsonify({'error': result['error']}), 500
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
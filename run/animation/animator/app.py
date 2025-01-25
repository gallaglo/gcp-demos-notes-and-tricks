from flask import Flask, request, jsonify
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import storage
import tempfile
import os
import logging
from functools import lru_cache

from script_generator import BlenderScriptGenerator
from blender_runner import BlenderRunner
from gcs_uploader import GCSUploader
from prompts import blender_prompt  # Add this import

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@lru_cache()
def get_components():
    """Initialize and cache all components"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(os.getenv('GCS_BUCKET_NAME'))
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192
    )
    
    script_generator = BlenderScriptGenerator(llm)
    blender_runner = BlenderRunner()
    gcs_uploader = GCSUploader(bucket)
    
    return script_generator, blender_runner, gcs_uploader

@app.route('/generate', methods=['POST'])
def generate():
    if not request.content_type or 'application/json' not in request.content_type:
        return jsonify({'error': 'Request must be JSON'}), 400
    
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400
        
        script_generator, blender_runner, gcs_uploader = get_components()
        
        # Generate script using function calling
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
                        'error': 'Failed to upload animation',
                        'details': str(upload_error)
                    }), 500
            return jsonify({'error': result['error']}), 500
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
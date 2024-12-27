from flask import Flask, request, jsonify
import os
import subprocess
import tempfile
from google.cloud import storage
from google.cloud import aiplatform
import json
import uuid

app = Flask(__name__)

# Configure GCS
storage_client = storage.Client()
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')
bucket = storage_client.bucket(BUCKET_NAME)

# Configure Vertex AI
aiplatform.init(project=os.getenv('GCP_PROJECT_ID'))

@app.route('/generate', methods=['POST'])
def generate():
    app.logger.info(f"Received request: {request.data}")
    
    if not request.is_json:
        app.logger.error("Request is not JSON")
        return jsonify({'error': 'Request must be JSON'}), 400
        
    prompt = request.json.get('prompt')
    app.logger.info(f"Extracted prompt: {prompt}")
    
    if not prompt:
        app.logger.error("No prompt provided in request")
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        # Generate Blender script using Vertex AI
        script = generate_blender_script(prompt)
        
        # Create temporary directory for working files
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            # Save script to temporary file
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Run Blender headlessly
            result = run_blender(script_path, output_path)
            
            if result['success']:
                # Upload to GCS
                gcs_path = f'animations/{uuid.uuid4()}.glb'
                blob = bucket.blob(gcs_path)
                blob.upload_from_filename(output_path)
                
                # Generate signed URL for frontend access
                url = blob.generate_signed_url(
                    version='v4',
                    expiration=3600,  # 1 hour
                    method='GET'
                )
                
                return jsonify({
                    'animation_url': url
                })
            else:
                return jsonify({'error': result['error']}), 500
    
    except Exception as e:
        import traceback
        app.logger.error(f"Error processing request: {str(e)}")
        app.logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

def generate_blender_script(prompt):
    # Initialize Vertex AI model
    model = aiplatform.TextGenerationModel.from_pretrained("text-bison@001")
    
    # Construct prompt for the LLM
    llm_prompt = f"""
    Create a Python script for Blender that will generate a 3D animation based on this description:
    {prompt}
    
    The script must include these essential components:

    1. Basic Setup:
       - Import bpy (Blender Python API)
       - Clear any existing objects (meshes, lights, cameras)
       - Set frame range (start=1, end=250 for 10-second animation at 25fps)

    2. Camera Setup:
       - Create a camera at a good viewing distance (usually 5-10 units back)
       - Set camera parameters (focal length, sensor size)
       - Add orbit or tracking camera motion if appropriate
       - Parent camera to an empty object for easier animation
       - Set up proper camera constraints if needed

    3. Lighting Setup:
       - Create key light (main illumination)
       - Add fill light (reduce shadows)
       - Include rim/back light for depth
       - Set appropriate light energy and color values

    4. Scene Requirements:
       - Create the 3D objects and animation as described in the prompt
       - Apply materials and textures
       - Set up proper environment lighting
       - Configure render settings for quality output

    5. Animation Export:
       - Set up GLB export settings
       - Use the provided output_path variable for saving
       - Enable animation data in export
       - Include cameras and lights in export

    The script must:
    - Run without GUI (headless mode)
    - Handle materials and textures properly
    - Use best practices for performance
    - Include error handling
    - Set up proper world settings for background
    - Configure view layers and collections appropriately

    Format the code with clear sections and comments for readability."""
    
    # Get response from model
    response = model.predict(llm_prompt)
    
    # Extract and validate Python script
    script = response.text
    validate_script(script)
    
    return script

def validate_script(script):
    # Basic validation of the generated script
    forbidden_terms = ['system', 'os.system', 'subprocess', 'eval', 'exec']
    for term in forbidden_terms:
        if term in script:
            raise ValueError(f'Generated script contains forbidden term: {term}')
    
    # Add more validation as needed
    return True

def run_blender(script_path, output_path):
    try:
        # Run Blender headlessly with the generated script
        result = subprocess.run([
            'blender',
            '--background',
            '--python', script_path,
            '--',
            output_path
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return {'success': True}
        else:
            return {
                'success': False,
                'error': f'Blender error: {result.stderr}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Error running Blender: {str(e)}'
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
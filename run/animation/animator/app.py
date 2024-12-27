from flask import Flask, request, jsonify
import os
import subprocess
import tempfile
from google.cloud import storage
from google import genai
from google.genai import types
import json
import uuid

app = Flask(__name__)

# Configure GCS
storage_client = storage.Client()
BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')
bucket = storage_client.bucket(BUCKET_NAME)

# Configure Gemini
genai_client = genai.Client(
    vertexai=True,
    project=os.getenv('GCP_PROJECT_ID'),
    location="us-central1"
)

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
        # Generate Blender script using Gemini
        script = generate_blender_script(prompt)
        
        # Create temporary directory for working files
        with tempfile.TemporaryDirectory() as temp_dir:
            app.logger.info(f"Created temporary directory: {temp_dir}")
            app.logger.info(f"Temp directory permissions: {oct(os.stat(temp_dir).st_mode)}")
            
            script_path = os.path.join(temp_dir, 'animation.py')
            output_path = os.path.join(temp_dir, 'animation.glb')
            
            # Save script to temporary file
            try:
                with open(script_path, 'w') as f:
                    f.write(script)
                app.logger.info(f"Script saved successfully to {script_path}")
            except Exception as e:
                app.logger.error(f"Error saving script: {str(e)}")
                raise
            
            # Run Blender headlessly
            result = run_blender(script_path, output_path)
            
            if result['success']:
                try:
                    # Upload to GCS
                    gcs_path = f'animations/{uuid.uuid4()}.glb'
                    blob = bucket.blob(gcs_path)
                    blob.upload_from_filename(output_path)
                    app.logger.info(f"File uploaded successfully to GCS: {gcs_path}")
                    
                    # Generate signed URL for frontend access
                    url = blob.generate_signed_url(
                        version='v4',
                        expiration=3600,
                        method='GET'
                    )
                    
                    return jsonify({
                        'animation_url': url
                    })
                except Exception as e:
                    app.logger.error(f"Error uploading to GCS: {str(e)}")
                    raise
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
    app.logger.info("Generating Blender script with Gemini")
    llm_prompt = f"""Create a Python script for Blender that will generate a 3D animation based on this description:
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
    
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(llm_prompt)]
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        top_p=0.95,
        max_output_tokens=8192,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF")
        ],
    )
    
    response = ""
    for chunk in genai_client.models.generate_content_stream(
        model="gemini-2.0-flash-exp",
        contents=contents,
        config=generate_content_config,
    ):
        response += chunk.text
    
    validate_script(response)
    app.logger.info("Generated Blender script:")
    app.logger.info(response)
    
    return response

def validate_script(script):
    forbidden_terms = ['subprocess']
    for term in forbidden_terms:
        if term in script:
            raise ValueError(f'Generated script contains forbidden term: {term}')
    return True

def run_blender(script_path, output_path):
    try:
        # Log filesystem information
        app.logger.info(f"Current working directory: {os.getcwd()}")
        app.logger.info(f"Directory listing: {os.listdir('.')}")
        app.logger.info(f"Temp directory exists: {os.path.exists(os.path.dirname(output_path))}")
        
        # Ensure output directory exists
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            app.logger.info(f"Output directory created/verified")
            app.logger.info(f"Directory permissions: {oct(os.stat(os.path.dirname(output_path)).st_mode)}")
        except Exception as e:
            app.logger.error(f"Error creating output directory: {str(e)}")
            
        # Log the paths being used
        app.logger.info(f"Running Blender with script path: {script_path}")
        app.logger.info(f"Output path: {output_path}")
        
        # Run Blender headlessly with the generated script
        result = subprocess.run([
            'blender',
            '--background',
            '--factory-startup',
            '--python', script_path,
            '--',
            output_path
        ], capture_output=True, text=True)
        
        # Log Blender's output
        app.logger.info(f"Blender stdout: {result.stdout}")
        if result.stderr:
            app.logger.error(f"Blender stderr: {result.stderr}")
            
        # Log file system state after Blender run
        app.logger.info(f"After Blender run - Directory listing: {os.listdir('.')}")
        app.logger.info(f"After Blender run - Output path exists: {os.path.exists(output_path)}")
        if os.path.exists(output_path):
            app.logger.info(f"Output file permissions: {oct(os.stat(output_path).st_mode)}")
            app.logger.info(f"Output file size: {os.path.getsize(output_path)}")
        
        # Check if the output file was created
        if not os.path.exists(output_path):
            app.logger.error(f"Output file was not created at {output_path}")
            return {
                'success': False,
                'error': f'Blender failed to create output file. stderr: {result.stderr}'
            }
        
        if result.returncode == 0:
            app.logger.info(f"Blender execution successful. File exists: {os.path.exists(output_path)}")
            return {'success': True}
        else:
            return {
                'success': False,
                'error': f'Blender error (return code {result.returncode}): {result.stderr}'
            }
    
    except Exception as e:
        app.logger.error(f"Exception in run_blender: {str(e)}")
        return {
            'success': False,
            'error': f'Error running Blender: {str(e)}'
        }

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
from flask import Flask, render_template, request, jsonify, Response
import os
import requests
import google.auth.transport.requests
import google.oauth2.id_token
from urllib.parse import urlparse

app = Flask(__name__)

# Configure backend service URL from environment variable
BACKEND_SERVICE_URL = os.getenv('BACKEND_SERVICE_URL', 'https://animator-342279517497.us-central1.run.app')

def get_authenticated_request(url, method='GET', json_data=None):
    """Creates an authenticated request with IAM ID Token credential."""
    auth_req = google.auth.transport.requests.Request()
    id_token = google.oauth2.id_token.fetch_id_token(auth_req, BACKEND_SERVICE_URL)

    headers = {
        'Authorization': f'Bearer {id_token}',
        'Content-Type': 'application/json'
    }

    if method == 'GET':
        return requests.get(url, headers=headers)
    elif method == 'POST':
        return requests.post(url, headers=headers, json=json_data)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_animation():
    prompt = request.json.get('prompt')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        app.logger.info(f"Sending request to backend: {BACKEND_SERVICE_URL}/generate")
        
        # Call backend service with authentication
        response = get_authenticated_request(
            f"{BACKEND_SERVICE_URL}/generate",
            method='POST',
            json_data={'prompt': prompt}
        )
        
        app.logger.info(f"Backend response status: {response.status_code}")
        app.logger.info(f"Backend response content: {response.text}")
        
        if not response.ok:
            app.logger.error(f"Backend error: {response.text}")
            return jsonify({'error': f'Backend error: {response.text}'}), response.status_code
            
        try:
            data = response.json()
            app.logger.info(f"Parsed response data: {data}")
            
            # Get the signed URL directly from the response
            signed_url = data.get('signed_url')
            if not signed_url:
                app.logger.error("No signed_url in response")
                return jsonify({'error': 'No signed URL in response'}), 400
            
            # Stream the GLB file through our server
            app.logger.info(f"Fetching GLB from signed URL: {signed_url}")
            
            # Use authenticated request for GLB file if needed
            glb_response = get_authenticated_request(signed_url)
            
            app.logger.info(f"GLB response status: {glb_response.status_code}")
            app.logger.info(f"GLB response headers: {dict(glb_response.headers)}")
            
            if not glb_response.ok:
                error_msg = f"Failed to fetch GLB file: {glb_response.text}"
                app.logger.error(error_msg)
                return jsonify({'error': error_msg}), glb_response.status_code
            
            # Extract filename from the URL
            url_parts = urlparse(signed_url)
            filename = url_parts.path.split('/')[-1].split('?')[0]
            
            response = Response(
                glb_response.iter_content(chunk_size=8192),
                content_type='model/gltf-binary',
                headers={
                    'Content-Disposition': f'inline; filename={filename}',
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'no-cache'
                }
            )
            
            app.logger.info(f"Sending response with headers: {dict(response.headers)}")
            return response
            
        except ValueError as e:
            app.logger.error(f"JSON decode error: {str(e)}, Response content: {response.text}")
            return jsonify({'error': f'Invalid JSON response from backend: {response.text}'}), 500
    
    except Exception as e:
        app.logger.error(f"Error: {str(e)}")
        return jsonify({'error': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    # Enable debug mode for detailed error messages
    app.debug = True
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
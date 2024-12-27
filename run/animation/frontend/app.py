from flask import Flask, render_template, request, jsonify
import os
import requests
from google.cloud import storage

app = Flask(__name__)

# Configure backend service URL from environment variable
BACKEND_SERVICE_URL = os.getenv('BACKEND_SERVICE_URL')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_animation():
    prompt = request.json.get('prompt')
    
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400
    
    try:
        # Call backend service to generate animation
        response = requests.post(
            f"{BACKEND_SERVICE_URL}/generate",
            json={'prompt': prompt},
            headers={'Content-Type': 'application/json'}
        )
        
        response.raise_for_status()
        return jsonify(response.json())
    
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Backend service error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
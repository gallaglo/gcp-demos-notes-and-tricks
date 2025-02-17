from flask import Flask, render_template
import os
import socket
import requests

app = Flask(__name__)

def get_metadata(path):
    metadata_server = "http://metadata.google.internal"
    metadata_header = {"Metadata-Flavor": "Google"}
    try:
        response = requests.get(f"{metadata_server}/computeMetadata/v1/{path}", 
                              headers=metadata_header, timeout=2)
        if response.status_code == 200:
            return response.text
        return "Not available"
    except:
        return "Not available"

@app.route('/')
def index():
    # Get deployment type and set appropriate title and emoji
    deployment = os.getenv("DEPLOYMENT", "Unknown")
    if deployment == "Stable":
        title = "Stable Deploy"
        emoji = "🥚"
    elif deployment == "Canary":
        title = "Canary Deploy"
        emoji = "🐦"
    else:
        title = "Unknown Deploy"
        emoji = "❓"
    
    # Get GCP metadata
    zone = get_metadata("instance/zone").split('/')[-1]
    region = '-'.join(zone.split('-')[:-1])
    
    # Get node name (hostname)
    node = socket.gethostname()
    
    # Get cluster name
    cluster = get_metadata("instance/attributes/cluster-name")
    
    # Get pod name from environment variable
    pod = os.getenv("HOSTNAME", "Not available")

    return render_template('index.html', 
                         title=title,
                         emoji=emoji,
                         deployment=deployment,
                         region=region,
                         zone=zone,
                         cluster=cluster,
                         node=node,
                         pod=pod)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

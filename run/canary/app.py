from flask import Flask, render_template
import os
from google.cloud import compute_metadata_server

app = Flask(__name__)

def get_region():
    try:
        metadata_server = compute_metadata_server.MetadataServerClient()
        zone = metadata_server.get('instance/zone').split('/')[-1]
        # Extract region from zone (e.g., us-central1-a -> us-central1)
        region = '-'.join(zone.split('-')[:-1])
        return region
    except:
        return 'Unknown Region'

@app.route('/')
def home():
    deployment = os.getenv('DEPLOYMENT', 'Unknown')
    region = get_region()
    service_id = os.getenv('K_SERVICE', 'Unknown')
    
    emoji = '🥚' if deployment == 'Stable' else '🐦' if deployment == 'Canary' else '❓'
    
    return render_template('index.html',
                         deployment=deployment,
                         region=region,
                         service_id=service_id,
                         emoji=emoji)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)))

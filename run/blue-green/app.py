from flask import Flask, render_template
import os
import logging
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_region():
    """
    Get the current GCP region from metadata server with error handling
    Returns: String representing the region or 'Unknown Region' on error
    """
    try:
        logger.info("Attempting to retrieve region from metadata server")
        response = requests.get(
            'http://metadata.google.internal/computeMetadata/v1/instance/zone',
            headers={'Metadata-Flavor': 'Google'},
            timeout=1
        )
        response.raise_for_status()
        zone = response.text.split('/')[-1]
        # Extract region from zone (e.g., us-central1-a -> us-central1)
        region = '-'.join(zone.split('-')[:-1])
        logger.info(f"Successfully retrieved region: {region}")
        return region
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error accessing metadata server: {e}")
        return "Unknown Region"
    except Exception as e:
        logger.error(f"Unexpected error retrieving region: {str(e)}")
        return "Unknown Region"

def get_service_id():
    """
    Get the Cloud Run service ID with error handling
    Returns: String representing the service ID or 'Unknown Service' on error
    """
    try:
        service_id = os.getenv('K_SERVICE')
        if service_id:
            logger.info(f"Retrieved service ID: {service_id}")
            return service_id
        logger.warning("K_SERVICE environment variable not found")
        return "Unknown Service"
    except Exception as e:
        logger.error(f"Unexpected error retrieving service ID: {str(e)}")
        return "Unknown Service"

@app.route('/')
def home():
    # Get deployment type with fallback
    deployment = os.getenv('DEPLOYMENT', 'Unknown')
    logger.info(f"Current deployment type: {deployment}")

    # Get region and service ID with built-in fallbacks
    region = get_region()
    service_id = get_service_id()
    
    # Determine emoji based on deployment type
    emoji_map = {
        'Blue': '🟦',
        'Green': '🟩',
        'Unknown': '❓'
    }
    emoji = emoji_map.get(deployment, '❓')
    
    return render_template('index.html',
                         deployment=deployment,
                         region=region,
                         service_id=service_id,
                         emoji=emoji)

# This is only used when running locally
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')))
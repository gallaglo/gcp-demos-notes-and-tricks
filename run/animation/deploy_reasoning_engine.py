#!/usr/bin/env python3
# deploy_reasoning_engine.py

import os
import argparse
import time
from google.cloud import storage
from google.cloud import aiplatform
from typing import Dict, Any

def parse_args():
    parser = argparse.ArgumentParser(description='Deploy Animation Generator to Vertex AI Reasoning Engine')
    parser.add_argument('--project-id', required=True, help='Google Cloud Project ID')
    parser.add_argument('--region', default='us-central1', help='Google Cloud Region')
    parser.add_argument('--bucket-name', required=True, help='GCS Bucket for code')
    parser.add_argument('--animator-url', required=True, help='URL of the animator Cloud Run service')
    parser.add_argument('--code-dir', default='./langgraph', help='Directory containing LangGraph code')
    parser.add_argument('--machine-type', default='n1-standard-4', help='Machine type for endpoints')
    parser.add_argument('--min-replicas', type=int, default=1, help='Minimum replica count')
    parser.add_argument('--max-replicas', type=int, default=5, help='Maximum replica count')
    parser.add_argument('--service-account', help='Service account email for Reasoning Engine')
    parser.add_argument('--output-file', default='endpoint_uri.txt', help='File to write endpoint URI to')
    return parser.parse_args()

def upload_code_to_gcs(bucket_name: str, code_dir: str) -> str:
    """
    Upload the LangGraph code to GCS
    
    Args:
        bucket_name: GCS bucket name
        code_dir: Directory containing LangGraph code
        
    Returns:
        GCS path to the uploaded code
    """
    print(f"Uploading code from {code_dir} to gs://{bucket_name}/code/")
    
    # Initialize storage client
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # Upload required files
    required_files = [
        'animation_graph.py',
        'prompts.py',
        'requirements.txt'
    ]
    
    for file_name in required_files:
        file_path = os.path.join(code_dir, file_name)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required file {file_path} not found")
            
        blob = bucket.blob(f"code/{file_name}")
        blob.upload_from_filename(file_path)
        print(f"Uploaded {file_path} to gs://{bucket_name}/code/{file_name}")
    
    return f"gs://{bucket_name}/code"

def deploy_reasoning_engine(
    project_id: str,
    region: str,
    code_gcs_path: str,
    animator_url: str,
    machine_type: str,
    min_replicas: int,
    max_replicas: int,
    service_account: str = None
) -> Dict[str, Any]:
    """
    Deploy the Reasoning Engine to Vertex AI
    
    Args:
        project_id: Google Cloud Project ID
        region: Google Cloud Region
        code_gcs_path: GCS path to code
        animator_url: URL of animator service
        machine_type: Machine type for endpoint
        min_replicas: Minimum replica count
        max_replicas: Maximum replica count
        service_account: Service account email (optional)
        
    Returns:
        Dictionary with deployment info
    """
    print(f"Deploying Reasoning Engine to {project_id} in {region}")
    
    # Initialize Vertex AI
    aiplatform.init(project=project_id, location=region)
    
    # Create environment variables
    env_vars = {
        "BLENDER_SERVICE_URL": animator_url
    }
    
    # Deploy using the SDK
    try:
        from google.cloud.aiplatform.reasoning_engines import Application
        from google.cloud.aiplatform.reasoning_engines import Endpoint
        
        # Create the application
        app = Application.create(
            display_name="animation-generator",
            description="Generates 3D animations from text descriptions using Blender",
            graph_path=code_gcs_path,
            entry_module="animation_graph",
            entry_function="create_animation_graph",
            environment_variables=env_vars,
            network=f"projects/{project_id}/global/networks/default",
            service_account=service_account
        )
        
        print(f"Created Reasoning Engine Application: {app.resource_name}")
        
        # Wait for the application to be ready
        print("Waiting for application to be ready...")
        time.sleep(30)
        
        # Deploy the endpoint
        endpoint = Endpoint.create(
            display_name="animation-endpoint",
            application=app.resource_name,
            machine_type=machine_type,
            min_replica_count=min_replicas,
            max_replica_count=max_replicas,
            container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/langgraph-serving:latest"
        )
        
        print(f"Created Reasoning Engine Endpoint: {endpoint.resource_name}")
        print(f"Endpoint URI: {endpoint.uri}")
        
        return {
            "application_name": app.resource_name,
            "endpoint_name": endpoint.resource_name,
            "endpoint_uri": endpoint.uri
        }
        
    except ImportError as e:
        print(f"Error importing Vertex AI Reasoning Engine modules: {e}")
        print("Attempting to use experimental API...")
        
        # Fallback to experimental API if needed
        try:
            from google.cloud.aiplatform.experimental.reasoning_engines import Application
            from google.cloud.aiplatform.experimental.reasoning_engines import Endpoint
            
            # Create the application
            app = Application.create(
                display_name="animation-generator",
                description="Generates 3D animations from text descriptions using Blender",
                graph_path=code_gcs_path,
                entry_module="animation_graph",
                entry_function="create_animation_graph",
                environment_variables=env_vars,
                network=f"projects/{project_id}/global/networks/default",
                service_account=service_account
            )
            
            print(f"Created Reasoning Engine Application: {app.resource_name}")
            
            # Wait for the application to be ready
            print("Waiting for application to be ready...")
            time.sleep(30)
            
            # Deploy the endpoint
            endpoint = Endpoint.create(
                display_name="animation-endpoint",
                application=app.resource_name,
                machine_type=machine_type,
                min_replica_count=min_replicas,
                max_replica_count=max_replicas,
                container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/langgraph-serving:latest"
            )
            
            print(f"Created Reasoning Engine Endpoint: {endpoint.resource_name}")
            print(f"Endpoint URI: {endpoint.uri}")
            
            return {
                "application_name": app.resource_name,
                "endpoint_name": endpoint.resource_name,
                "endpoint_uri": endpoint.uri
            }
            
        except Exception as e:
            print(f"Failed to deploy using experimental API: {e}")
            raise
    
    except Exception as e:
        print(f"Error deploying Reasoning Engine: {e}")
        raise

def main():
    args = parse_args()
    
    # Upload code to GCS
    code_gcs_path = upload_code_to_gcs(args.bucket_name, args.code_dir)
    
    # Deploy the Reasoning Engine
    result = deploy_reasoning_engine(
        project_id=args.project_id,
        region=args.region,
        code_gcs_path=code_gcs_path,
        animator_url=args.animator_url,
        machine_type=args.machine_type,
        min_replicas=args.min_replicas,
        max_replicas=args.max_replicas,
        service_account=args.service_account
    )
    
    # Write the endpoint URI to a file
    with open(args.output_file, 'w') as f:
        f.write(result["endpoint_uri"])
    
    print(f"Deployment complete. Endpoint URI written to {args.output_file}")

if __name__ == "__main__":
    main()

# Animation Generator

Containerized web application that generates animations based on user prompts using [Gemini 2.0](https://cloud.google.com/vertex-ai/generative-ai/docs/gemini-v2) (LLM) and [Blender](https://www.blender.org/).

![Animation Generator](animation-app.gif)

## Architecture

The application processes animation requests through the following workflow:

1. Frontend sends animation prompt to Agent Service
2. Agent Service validates prompt and calls LLM API
3. Agent Service generates a Blender script
4. Agent Service sends the script to Animator Service
5. Animator Service validates and executes the script in Blender
6. Animator Service saves animation to Cloud Storage
7. Agent Service returns the signed URL to frontend
8. Frontend loads and displays animation

```mermaid
flowchart LR
    User((User))
    GCS[(Cloud Storage)]
    VertexAI[Vertex AI LLM]
    
    subgraph "Frontend Web App"
        WebUI[Prompt Input]
        ThreeJS[Three.js Viewer]
    end
    
    subgraph "Agent Service"
        AgentAPI[FastAPI]
        LangGraph[LangGraph Workflow]
        ScriptGen[BlenderScriptGenerator]
    end
    
    subgraph "Animator Service"
        AnimatorAPI[Flask API]
        BlenderRunner[BlenderRunner]
        GCSUploader[GCSUploader]
    end
    
    User -->|"Submit animation prompt"| WebUI
    WebUI -->|"Send prompt to agent"| AgentAPI
    AgentAPI -->|"Process with LangGraph"| LangGraph
    LangGraph -->|"Generate script"| ScriptGen
    ScriptGen -->|"Request script"| VertexAI
    VertexAI -->|"Return script"| ScriptGen
    ScriptGen -->|"Generate script"| LangGraph
    LangGraph -->|"Send script to animator"| AnimatorAPI
    AnimatorAPI -->|"Validate script"| BlenderRunner
    BlenderRunner -->|"Generate GLB animation"| GCSUploader
    GCSUploader -->|"Upload files"| GCS
    GCS -->|"Return signed URL"| AnimatorAPI
    AnimatorAPI -->|"Return signed URL"| AgentAPI
    AgentAPI -->|"Return signed URL"| ThreeJS
    ThreeJS -->|"Display animation"| User
```

The services communicate securely through Cloud Run's built-in service-to-service authentication.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/) or [Podman](https://podman-desktop.io/downloads/)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- [Docker Compose](https://docs.docker.com/compose/) or [Podman Compose](https://podman-desktop.io/docs/compose/setting-up-compose) for local development
- Active Google Cloud Project

## Cloud Deployment

### Setup Instructions

#### 1. Set Environment Variables

```bash
# Set your project ID
export PROJECT_ID="<your-project-id>"
export REGION="us-central1"  # or your preferred region
export AR_REPO="animator-app"  # name for your Artifact Registry repository
```

#### 2. Authenticate with Google Cloud

```bash
gcloud auth application-default login
```

#### 3. Enable Required APIs

```bash
# Enable required Google Cloud APIs
gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    apikeys.googleapis.com \
    generativelanguage.googleapis.com \
    secretmanager.googleapis.com \
    iam.googleapis.com
```

#### 4. Create Artifact Registry Repository

```bash
# Create a Docker repository in Artifact Registry
gcloud artifacts repositories create $AR_REPO \
    --repository-format=docker \
    --location=$REGION \
    --description="Repository for Animation Generator"
```

#### 5. Configure Docker Authentication

```bash
# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

#### 6. Build and Push Container Images

```bash
# Build frontend image
gcloud builds submit ./frontend \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/frontend:latest

# Build agent image
gcloud builds submit ./agent-service \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/agent:latest

# Build animator image
gcloud builds submit ./animator \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/animator:latest
```

#### 7. Deploy to Cloud Run

Navigate to the `terraform/` directory and run Terraform to deploy the services.

```bash
# Navigate into the terraform/ directory
cd terraform
# Initialize terraform
terraform init
# Deploy cloud run services
terraform apply \                
    -var "project_id=${PROJECT_ID}" \
    -var "region=${REGION}" \
    -var "animator_container_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/animator:latest" \
    -var "agent_container_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/agent:latest" \
    -var "frontend_container_image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/frontend:latest"
```

### Cleanup

To avoid incurring charges, clean up the resources when no longer needed:

```bash
# Delete Cloud Run services
cd terraform
terraform destroy
# Delete Artifact Registry repository
gcloud artifacts repositories delete $AR_REPO \
    --location=$REGION
```

## Local Development

Build and run the services locally using Docker Compose or Podman Compose for development and testing.

> **Note**: Steps create and save an [IAM service account key](https://cloud.google.com/iam/docs/service-account-creds#user-managed-keys) to a local JSON file.

### Setup

1. Set Environment Variables

   ```bash
   # Set your project ID
   export PROJECT_ID="<your-project-id>"
   export REGION="us-central1"  # or your preferred region
   ```

2. Authenticate with Google Cloud

   ```bash
   gcloud auth application-default login
   ```

3. Deploy infrastructure using Terraform

   ```bash
   cd terraform
   # Create terraform.tfvars file
   cat << EOF > terraform.tfvars
   project_id = "${PROJECT_ID}"
   region = "${REGION}"
   local_testing_mode = true
   EOF
   
   terraform init
   terraform apply  # enter yes to proceed
   cd ..
   ```

4. Set up the local environment

   ```bash
   ./setup-local-env.sh
   ```

5. Start the services locally

   ```bash
   # Using Docker Compose
   docker-compose up
   
   # Or using Podman Compose
   podman-compose up
   ```

6. Access the application at <http://localhost:3000>

### Local Cleanup

1. Press `Ctrl+C` to stop the containers
2. Delete GCP resources and service account key file provisioned in Terraform

```bash
cd terraform
terraform destroy
```

# GCP Cloud Run Markdown Preview Editor

> **Note**: This demo is based on the [Securing Cloud Run services tutorial](https://cloud.google.com/run/docs/tutorials/secure-services) from the Google Cloud documentation.

## Architecture

![Cloud Run Architecture](https://cloud.google.com/static/run/docs/tutorials/images/secure-services-architecture.svg)

The application consists of two Cloud Run services:
1. **Editor Service**: Serves the markdown editor interface and handles user interactions
2. **Renderer Service**: Processes markdown content and returns rendered HTML
   
The services communicate securely through Cloud Run's built-in service-to-service authentication.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)
- [Terraform](https://developer.hashicorp.com/terraform/install)
- Active Google Cloud Project

## Setup Instructions

### 1. Set Environment Variables

```bash
# Set your project ID
export PROJECT_ID="<your-project-id>"
export REGION="us-central1"  # or your preferred region
export AR_REPO="markdown-preview"  # name for your Artifact Registry repository
```

### 2. Enable Required APIs

```bash
# Enable required Google Cloud APIs
gcloud services enable \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    run.googleapis.com
```

### 3. Create Artifact Registry Repository

```bash
# Create a Docker repository in Artifact Registry
gcloud artifacts repositories create $AR_REPO \
    --repository-format=docker \
    --location=$REGION \
    --description="Repository for Markdown Preview Editor"
```

### 4. Configure Docker Authentication

```bash
# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### 5. Build and Push Container Images

```bash
# Build frontend image
gcloud builds submit ./editor \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/editor:latest

# Build backend image
gcloud builds submit ./renderer \
    --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/renderer:latest
```

### 6. Deploy to Cloud Run

```bash
# navigate into the terraform/ directory
cd terraform

# write your input variable values to terraform.tvars
cat << EOF > terraform.tfvars
project_id="<project id>"
editor_container_image="<editor image uri>"
renderer_container_image="renderer image uri>"
EOF

# intialize terraform
terraform init

# deploy cloud run services
terraform apply
```

## Request Workflow

![HTTP Request Workflow](https://cloud.google.com/static/run/docs/tutorials/images/secure-services-sequence.svg)

The sequence diagram above illustrates the HTTP request flow:
1. User sends markdown content through the frontend interface
2. Frontend service makes an HTTP POST request to the backend
3. Backend service processes the markdown and returns rendered HTML
4. Frontend displays the rendered content to the user

## Clean Up

To avoid incurring charges, clean up the resources when no longer needed:

```bash
# Delete Cloud Run services
cd terraform
terraform destroy

# Delete Artifact Registry repository
gcloud artifacts repositories delete $AR_REPO \
    --location=$REGION
```
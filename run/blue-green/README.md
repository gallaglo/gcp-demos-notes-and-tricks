# Cloud Run Blue/Green Deployment Demo

This application demonstrates Cloud Run's traffic management capabilities using a blue/green deployment strategy. The app displays different colored backgrounds and emojis (🟦 for blue, 🟩 for green) based on the deployment version, along with the current region and service ID information.

## Features

- Visual distinction between blue and green deployments
  - Blue version: Blue gradient background and 🟦 emoji
  - Green version: Green gradient background and 🟩 emoji
- Displays Cloud Run region and service ID
- Responsive web interface
- Environment variable configuration

## Prerequisites

- Google Cloud SDK installed and configured
- Docker installed locally (for local testing)
- An active Google Cloud Project
- Required permissions:
  - Cloud Run Admin
  - Storage Admin (for Artifact Registry)
  - Service Account User
  - Cloud Build Editor

## Environment Variables

- `DEPLOYMENT`: Sets the deployment type (default: "Unknown")
  - "Blue" - Shows blue styling and 🟦
  - "Green" - Shows green styling and 🟩

## Local Development

1. Build the container locally:
```bash
docker build -t bluegreen-demo .
```

2. Run the container locally:
```bash
# Test blue version
docker run -p 8080:8080 -e PORT=8080 -e DEPLOYMENT=Blue bluegreen-demo

# Test green version
docker run -p 8080:8080 -e PORT=8080 -e DEPLOYMENT=Green bluegreen-demo
```

Access the application at http://localhost:8080

## Cloud Deployment

1. Set your project ID and region:
```bash
export PROJECT_ID="your-project-id"
export REGION="your-region"  # e.g., us-central1
export REPO_NAME="cloud-run-demos"
```

2. Enable required services:
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com
```

3. Create Artifact Registry repository (if not already created):
```bash
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Repository for Cloud Run demos"
```

4. Configure Docker authentication:
```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

## Building and Deploying

1. Build and push the container using Cloud Build:
```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION="${REGION}",_REPO_NAME="${REPO_NAME}"
```

2. Deploy the initial blue version:
```bash
gcloud run deploy bluegreen-demo \
  --image ${REGION}-docker.pkg.dev/$PROJECT_ID/${REPO_NAME}/blue-green-demo:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars DEPLOYMENT=Blue \
  --tag blue
```

3. Deploy the green version with no traffic:
```bash
gcloud run deploy bluegreen-demo \
  --image ${REGION}-docker.pkg.dev/$PROJECT_ID/${REPO_NAME}/blue-green-demo:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars DEPLOYMENT=Green \
  --tag green \
  --no-traffic
```

## Testing and Traffic Management

1. Test the green version using the tag URL:
```bash
# Get the green revision URL
gcloud run services describe bluegreen-demo \
  --platform managed \
  --region $REGION \
  --format='value(status.url)' \
  --tag green
```

2. Migrate traffic to green version:
```bash
# Gradual migration (optional)
gcloud run services update-traffic bluegreen-demo \
  --region $REGION \
  --to-tags green=50

# Full migration to green
gcloud run services update-traffic bluegreen-demo \
  --region $REGION \
  --to-tags green=100
```

3. Rollback to blue version if needed:
```bash
gcloud run services update-traffic bluegreen-demo \
  --to-tags blue=100
```

## Monitoring

View service details and traffic split:
```bash
gcloud run services describe bluegreen-demo \
  --region $REGION
```

Check application logs:
```bash
# View logs
gcloud run services logs read bluegreen-demo --region $REGION

# Stream logs
gcloud run services logs tail bluegreen-demo --region $REGION
```

## Cleanup

1. Delete the Cloud Run service:
```bash
gcloud run services delete bluegreen-demo \
  --region $REGION
```

2. Delete the container images:
```bash
gcloud artifacts packages delete bluegreen-demo \
  --repository=$REPO_NAME \
  --location=$REGION \
  --quiet
```

3. (Optional) Delete the Artifact Registry repository:
```bash
gcloud artifacts repositories delete $REPO_NAME \
  --location=$REGION \
  --quiet
```
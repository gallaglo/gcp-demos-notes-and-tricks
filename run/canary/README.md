# Cloud Run Canary Deployment Demo

This application demonstrates Cloud Run's traffic splitting capabilities using a simple Flask web application. The app displays different emojis and deployment information based on whether it's running as a stable (🥚) or canary (🐦) deployment.

## Features

- Visual distinction between stable and canary deployments
- Displays Cloud Run region and service ID
- Configurable via environment variables

## Prerequisites

- Google Cloud SDK installed and configured
- Docker installed locally (for local testing)
- An active Google Cloud Project
- Required permissions:
  - Cloud Run Admin
  - Artifact Registry Administrator
  - Storage Admin
  - Service Account User
  - Cloud Build Editor

## Environment Variables

- `DEPLOYMENT`: Sets the deployment type (default: "Stable")
  - "Stable" - Shows egg emoji 🥚
  - "Canary" - Shows bird emoji 🐦

## Local Development

1. Build the container locally:
```bash
docker build -t canary-demo .
```

2. Run the container locally:
```bash
docker run -p 8080:8080 -e PORT=8080 canary-demo
```

Access the application at http://localhost:8080

## Cloud Deployment Setup

1. Set your project ID and region:
```bash
export PROJECT_ID="<your-project-id>"
export REGION="<your-region>"  # e.g., us-central1
export REPO_NAME="cloud-run-demos"
```

2. Enable required services:
```bash
gcloud services enable \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  run.googleapis.com
```

3. Create an Artifact Registry repository:
```bash
gcloud artifacts repositories create $REPO_NAME \
  --repository-format=docker \
  --location=$REGION \
  --description="Repository for Cloud Run demos"
```

4. Configure Docker authentication for Artifact Registry:
```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

## Building and Deploying

1. Build and push the container using Cloud Build:
```bash
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_REGION="${REGION}",_REPO_NAME="${REPO_NAME}"
```

3. Deploy the stable version:
```bash
gcloud run deploy canary-demo \
  --image ${REGION}-docker.pkg.dev/$PROJECT_ID/${REPO_NAME}/canary-demo:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars DEPLOYMENT=Stable \
  --tag stable
```

4. Deploy the canary version:
```bash
gcloud run deploy canary-demo \
  --image ${REGION}-docker.pkg.dev/$PROJECT_ID/${REPO_NAME}/canary-demo:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars DEPLOYMENT=Canary \
  --tag canary \
  --no-traffic
```

5. Set up traffic splitting (e.g., 90% stable, 10% canary):
```bash
gcloud run services update-traffic canary-demo \
  --region $REGION \
  --to-tags stable=90,canary=10
```

## Testing the Deployment

1. Get the service URL:
```bash
gcloud run services describe canary-demo \
  --platform managed \
  --region $REGION \
  --format 'value(status.url)'
```

2. Open the URL in a browser and refresh multiple times. You should see:
   - The egg emoji (🥚) approximately 90% of the time (stable)
   - The bird emoji (🐦) approximately 10% of the time (canary)

## Increase traffic to Canary Deployment

1. Update traffic splitting (e.g., 50% stable, 50% canary):
```bash
gcloud run services update-traffic canary-demo \
  --region $REGION \
  --to-tags stable=50,canary=50
```
2. Open the URL in a browser and refresh multiple times. You should see:
   - The egg emoji (🥚) approximately 50% of the time (stable)
   - The bird emoji (🐦) approximately 50% of the time (canary)

## Monitoring and Rollback

To monitor the deployment:
```bash
gcloud run services describe canary-demo \
  --region $REGION
```

To rollback (return all traffic to stable):
```bash
gcloud run services update-traffic canary-demo \
  --to-tags stable=100
```

## Cleanup

1. Delete the Cloud Run service:
```bash
gcloud run services delete canary-demo \
  --region $REGION
```

2. Delete the container images:
```bash
gcloud artifacts packages delete canary-demo \
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

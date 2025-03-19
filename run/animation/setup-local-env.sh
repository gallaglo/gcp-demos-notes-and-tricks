#!/bin/bash
set -e
# Script to generate local.env file from Terraform outputs
# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Retrieving values from Terraform...${NC}"
# Change to terraform directory
echo -e "${YELLOW}Current directory: $(pwd)${NC}"
if [ ! -d "terraform" ]; then
  echo -e "${RED}Error: terraform directory not found in $(pwd)${NC}"
  exit 1
fi
cd terraform
echo -e "${YELLOW}Changed to directory: $(pwd)${NC}"

# Debug: List terraform outputs
echo -e "${YELLOW}Listing all terraform outputs:${NC}"
terraform output || echo -e "${RED}Failed to run terraform output command${NC}"

# Get project ID from terraform output
echo -e "${YELLOW}Attempting to get project_id...${NC}"
PROJECT_ID=$(terraform output -raw project_id 2>&1)
if [ $? -ne 0 ]; then
  echo -e "${RED}Error: Failed to get project_id from terraform output${NC}"
  echo -e "${RED}Error message: ${PROJECT_ID}${NC}"
  echo -e "${RED}Make sure you're in the correct directory and terraform has been applied${NC}"
  echo -e "${RED}Try running: terraform init && terraform apply${NC}"
  exit 1
fi
echo -e "${GREEN}Successfully retrieved project_id: ${PROJECT_ID}${NC}"

# Get bucket name from terraform output
echo -e "${YELLOW}Attempting to get bucket_name...${NC}"
BUCKET_NAME=$(terraform output -raw bucket_name 2>&1)
if [ $? -ne 0 ]; then
  echo -e "${RED}Error: Failed to get bucket_name from terraform output${NC}"
  echo -e "${RED}Error message: ${BUCKET_NAME}${NC}"
  exit 1
fi
echo -e "${GREEN}Successfully retrieved bucket_name: ${BUCKET_NAME}${NC}"

# Get region from terraform output
echo -e "${YELLOW}Attempting to get region...${NC}"
REGION=$(terraform output -raw region 2>&1)
if [ $? -ne 0 ]; then
  echo -e "${YELLOW}Warning: Failed to get region from terraform output, using default us-central1${NC}"
  echo -e "${YELLOW}Error message: ${REGION}${NC}"
  REGION="us-central1"
fi
echo -e "${GREEN}Region set to: ${REGION}${NC}"

# Check if we're in local testing mode by checking the deployment_mode output
echo -e "${YELLOW}Attempting to get deployment_mode...${NC}"
DEPLOYMENT_MODE=$(terraform output -raw deployment_mode 2>&1)
if [ $? -ne 0 ]; then
  echo -e "${YELLOW}Warning: Failed to get deployment_mode from terraform output, assuming local testing${NC}"
  echo -e "${YELLOW}Error message: ${DEPLOYMENT_MODE}${NC}"
  DEPLOYMENT_MODE="local testing"
fi
echo -e "${GREEN}DEPLOYMENT_MODE: ${DEPLOYMENT_MODE}${NC}"

# Determine if we're in local testing mode
IS_LOCAL_TESTING=false
if [[ "$DEPLOYMENT_MODE" == *"local"* ]]; then
  IS_LOCAL_TESTING=true
  echo -e "${GREEN}Local testing mode detected${NC}"
fi

# Set the paths for service account key
echo -e "${YELLOW}Setting service account key paths...${NC}"
HOST_SERVICE_ACCOUNT_KEY_PATH="animator-sa-key.json"
CONTAINER_SERVICE_ACCOUNT_KEY_PATH="/app/animator-sa-key.json"
echo -e "${YELLOW}Host path: ${HOST_SERVICE_ACCOUNT_KEY_PATH}${NC}"
echo -e "${YELLOW}Container path: ${CONTAINER_SERVICE_ACCOUNT_KEY_PATH}${NC}"

# If local testing mode is true, verify the service account key exists
if [[ "$IS_LOCAL_TESTING" == "true" ]]; then
  echo -e "${YELLOW}Local testing mode detected. Verifying service account key...${NC}"
  
  # Check if the service account key exists in project root
  if [ -f "../$HOST_SERVICE_ACCOUNT_KEY_PATH" ]; then
    echo -e "${GREEN}Service account key found at ../${HOST_SERVICE_ACCOUNT_KEY_PATH}${NC}"
    chmod 600 "../$HOST_SERVICE_ACCOUNT_KEY_PATH"
    echo -e "${GREEN}Permissions set to 600${NC}"
  # Check if the service account key exists in terraform directory
  elif [ -f "$HOST_SERVICE_ACCOUNT_KEY_PATH" ]; then
    echo -e "${GREEN}Service account key found at ${HOST_SERVICE_ACCOUNT_KEY_PATH}${NC}"
    # Copy to project root where docker-compose expects it
    cp "$HOST_SERVICE_ACCOUNT_KEY_PATH" "../$HOST_SERVICE_ACCOUNT_KEY_PATH"
    chmod 600 "../$HOST_SERVICE_ACCOUNT_KEY_PATH"
    echo -e "${GREEN}Copied key to project root and set permissions to 600${NC}"
  else
    echo -e "${RED}Error: No service account key found at ${HOST_SERVICE_ACCOUNT_KEY_PATH} or ../${HOST_SERVICE_ACCOUNT_KEY_PATH}${NC}"
    echo -e "${RED}Files in current directory: $(ls -la)${NC}"
    echo -e "${RED}Files in parent directory: $(ls -la ..)${NC}"
    echo -e "${RED}Ensure Terraform generated the key with 'terraform apply'.${NC}"
    exit 1
  fi
fi

# Extract service endpoints for local development
echo -e "${YELLOW}Getting service endpoints...${NC}"
ANIMATOR_URL=$(terraform output -raw animator_url 2>/dev/null || echo "http://animator:8080")
AGENT_URL=$(terraform output -raw agent_url 2>/dev/null || echo "http://agent:8081")
FRONTEND_URL=$(terraform output -raw frontend_url 2>/dev/null || echo "http://localhost:3000")

# Change back to the project root
echo -e "${YELLOW}Changing back to project root...${NC}"
cd ..
echo -e "${YELLOW}Current directory: $(pwd)${NC}"

# Create local.env file
echo -e "${YELLOW}Creating local.env file...${NC}"
cat > local.env << EOF
# Generated from Terraform outputs on $(date)
GOOGLE_CLOUD_PROJECT=${PROJECT_ID}
GCS_BUCKET_NAME=${BUCKET_NAME}
VERTEX_AI_LOCATION=${REGION}
# This is the path within the container
GOOGLE_APPLICATION_CREDENTIALS=${CONTAINER_SERVICE_ACCOUNT_KEY_PATH}

# Connection between services (using docker service names)
BLENDER_SERVICE_URL=http://animator:8080
LANGGRAPH_ENDPOINT=http://agent:8080
NEXT_PUBLIC_LANGGRAPH_ENDPOINT=http://localhost:8081
EOF

echo -e "${GREEN}Created local.env file with the following values:${NC}"
echo -e "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
echo -e "GCS_BUCKET_NAME=${BUCKET_NAME}"
echo -e "VERTEX_AI_LOCATION=${REGION}"
echo -e "GOOGLE_APPLICATION_CREDENTIALS=${CONTAINER_SERVICE_ACCOUNT_KEY_PATH}"
echo -e "BLENDER_SERVICE_URL=http://animator:8080"
echo -e "AGENT_SERVICE_URL=http://agent:8081"
echo -e "NEXT_PUBLIC_AGENT_SERVICE_URL=http://localhost:8081"

echo -e "\n${GREEN}You can now run:${NC}"
echo -e "podman compose --env-file local.env up"
echo -e "or"
echo -e "docker compose --env-file local.env up"
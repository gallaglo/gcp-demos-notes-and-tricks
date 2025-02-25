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
REGION=$(terraform output -raw region 2>&1 || echo "us-central1")
echo -e "${GREEN}Successfully retrieved region: ${REGION}${NC}"

# Check if local testing mode is true
echo -e "${YELLOW}Attempting to get local_testing_mode...${NC}"
LOCAL_TESTING_MODE=$(terraform output -raw local_testing_mode 2>&1 || echo "Error retrieving local_testing_mode")
echo -e "${GREEN}LOCAL_TESTING_MODE: ${LOCAL_TESTING_MODE}${NC}"

# Set the path for the service account key (now generated in the project root by Terraform)
echo -e "${YELLOW}Setting service account key path...${NC}"
SERVICE_ACCOUNT_KEY_PATH="animator-sa-key.json"
echo -e "${YELLOW}SERVICE_ACCOUNT_KEY_PATH set to: ${SERVICE_ACCOUNT_KEY_PATH}${NC}"

# If local testing mode is true, verify the service account key exists
if [[ "$LOCAL_TESTING_MODE" == "true" || "$LOCAL_TESTING_MODE" == "Error retrieving local_testing_mode" ]]; then
  echo -e "${YELLOW}Local testing mode detected or assumed. Verifying service account key...${NC}"
  
  # Check if the service account key exists
  if [ -f "../$SERVICE_ACCOUNT_KEY_PATH" ]; then
    # Key file already exists in project root
    echo -e "${GREEN}Service account key found at ../${SERVICE_ACCOUNT_KEY_PATH}${NC}"
    # Ensure proper permissions
    chmod 600 "../$SERVICE_ACCOUNT_KEY_PATH"
    echo -e "${GREEN}Permissions set to 600${NC}"
  elif [ -f "$SERVICE_ACCOUNT_KEY_PATH" ]; then
    # Key file exists in terraform directory
    echo -e "${GREEN}Service account key found at ${SERVICE_ACCOUNT_KEY_PATH}${NC}"
    # Ensure proper permissions
    chmod 600 "$SERVICE_ACCOUNT_KEY_PATH"
    echo -e "${GREEN}Permissions set to 600${NC}"
  else
    echo -e "${RED}Error: No service account key found at ${SERVICE_ACCOUNT_KEY_PATH} or ../${SERVICE_ACCOUNT_KEY_PATH}${NC}"
    echo -e "${RED}Files in current directory: $(ls -la)${NC}"
    echo -e "${RED}Files in parent directory: $(ls -la ..)${NC}"
    echo -e "${RED}Ensure Terraform generated the key.${NC}"
    exit 1
  fi
fi

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
GOOGLE_APPLICATION_CREDENTIALS=${SERVICE_ACCOUNT_KEY_PATH}
EOF

echo -e "${GREEN}Created local.env file with the following values:${NC}"
echo -e "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
echo -e "GCS_BUCKET_NAME=${BUCKET_NAME}"
echo -e "VERTEX_AI_LOCATION=${REGION}"
echo -e "GOOGLE_APPLICATION_CREDENTIALS=${SERVICE_ACCOUNT_KEY_PATH}"

echo -e "\n${GREEN}You can now run:${NC}"
echo -e "podman compose --env-file local.env up"
echo -e "or"
echo -e "docker compose --env-file local.env up"
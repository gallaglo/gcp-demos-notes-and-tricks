# Multi-region Cloud Run Deployment

This repo deploys Cloud Run services to two GCP cloud regions and configures a Global Application Load Balancer to route traffic to the two services. The deployment includes automated setup of Secret Manager for secure API key management.

If the variable `enable_https` is set to `true`, the load balancer will be configured for HTTPS and will serve traffic at `https://<ip-address>.nip.io`.

## Features

- **Multi-region deployment** - Cloud Run services in two regions for high availability
- **Global Load Balancer** - Routes traffic to the closest healthy region
- **Secret Management** - Automated OpenWeather API key storage in Secret Manager
- **HTTPS Support** - Optional SSL/TLS termination with automatic certificate management
- **IAP Integration** - Optional Identity-Aware Proxy protection
- **Service Account** - Least-privilege IAM configuration with required permissions

## Prerequisites

- Terraform >= 1.0
- Google Cloud SDK (gcloud) configured
- Required GCP APIs enabled:
  - Cloud Run API
  - Compute Engine API
  - Cloud Load Balancing API
  - Secret Manager API (automatically enabled)
- (Optional) [OpenWeather API Key](https://openweathermap.org/api) for weather functionality

## OpenWeather API Key Setup

The Terraform configuration automatically creates and manages an OpenWeather API key secret in Secret Manager:

### Option 1: Set API Key via Terraform Variable (Initial Setup)
```bash
# Set the API key as a Terraform variable
export TF_VAR_openweather_api_key="your-actual-openweather-api-key"
terraform apply
```

### Option 2: Update Secret Manually (Recommended for Production)
```bash
# After initial deployment, update the secret manually for better security
gcloud secrets versions add <service-name-prefix>-openweather-api-key \
  --data-file=- <<< "your-actual-openweather-api-key"
```

### Option 3: Skip Weather Features
```bash
# Deploy without weather functionality (uses mock data)
terraform apply -var="openweather_api_key=placeholder"
```

**Note:** If you don't provide a valid API key, the application will automatically use mock weather data and log appropriate warnings.

## Quick Start

1. **Clone and configure:**
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   
   # Copy and customize variables
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Set required variables in `terraform.tfvars`:**
   ```hcl
   project_id      = "your-gcp-project-id"
   container_image = "us-west1-docker.pkg.dev/your-project/your-repo/whereami:latest"
   openweather_api_key = "your-openweather-api-key"  # Optional
   ```

3. **Deploy:**
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

4. **Access your application:**
   ```bash
   # Get the load balancer IP
   terraform output load_balancer_ip
   
   # Visit your application
   curl http://<load-balancer-ip>
   ```

## Configuration Examples

### Basic Deployment (HTTP only)
```hcl
project_id           = "my-gcp-project"
container_image      = "us-west1-docker.pkg.dev/my-project/my-repo/whereami:latest"
service_name_prefix  = "whereami"
openweather_api_key  = "your-api-key-here"
```

### Production Deployment (HTTPS + IAP)
```hcl
project_id           = "my-gcp-project"
container_image      = "us-west1-docker.pkg.dev/my-project/my-repo/whereami:latest"
service_name_prefix  = "whereami-prod"
enable_https         = true
enable_iap           = true
openweather_api_key  = "your-api-key-here"
region_1            = "us-central1"
region_2            = "europe-west1"
```

### Development Deployment (Mock Weather Data)
```hcl
project_id           = "my-dev-project"
container_image      = "us-west1-docker.pkg.dev/my-project/my-repo/whereami:latest"
service_name_prefix  = "whereami-dev"
# No openweather_api_key specified - will use mock data
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| container\_image | Container image URI (example: us-west1-docker.pkg.dev/logan-gallagher/cloud-run-source-deploy/whereami:latest) | `string` | `""` | yes |
| enable\_https | Enforce HTTPS for load balancer | `bool` | `false` | no |
| enable\_iap | Enable Identity-Aware Proxy protection. NOTE: enable\_https must be set to `true` | `bool` | `false` | no |
| openweather\_api\_key | OpenWeather API key for weather functionality. If not provided or set to placeholder values, the app will use mock weather data. | `string` | `"placeholder"` | no |
| project\_id | GCP Project ID | `string` | `""` | yes |
| region\_1 | Region of the first Cloud Run service | `string` | `"us-west1"` | no |
| region\_2 | Region of the second Cloud Run service | `string` | `"us-east1"` | no |
| service\_name\_prefix | Prefix for the Cloud Run service name | `string` | `"cloud-run"` | no |

## Outputs

| Name | Description |
|------|-------------|
| cloud\_run\_services | URLs of the deployed Cloud Run services |
| load\_balancer\_ip | IP address of the Global Load Balancer |
| secret\_manager\_secret | Name of the Secret Manager secret containing the OpenWeather API key |
| service\_account\_email | Email of the created service account |

## Secret Management

The Terraform configuration automatically:

1. **Creates a Secret Manager secret** for the OpenWeather API key
2. **Grants the service account** `secretmanager.secretAccessor` role
3. **Configures Cloud Run** to inject the secret as an environment variable
4. **Uses lifecycle rules** to prevent accidental secret data changes

### Manual Secret Updates

To update the API key after deployment:

```bash
# Update the secret version
echo "new-api-key" | gcloud secrets versions add <service-name-prefix>-openweather-api-key --data-file=-

# Restart Cloud Run services to pick up the new secret
gcloud run services update <service-name-prefix>-us-west1 --region=us-west1
gcloud run services update <service-name-prefix>-us-east1 --region=us-east1
```

### Viewing Current Secret

```bash
# List secret versions
gcloud secrets versions list <service-name-prefix>-openweather-api-key

# View current secret value (requires appropriate permissions)
gcloud secrets versions access latest --secret=<service-name-prefix>-openweather-api-key
```

## Architecture

```
Internet → Global Load Balancer → Cloud Run (Region 1)
                               → Cloud Run (Region 2)
                                     ↓
                               Secret Manager
```

- **Traffic Distribution**: Global Load Balancer routes traffic to the nearest healthy region
- **High Availability**: If one region fails, traffic automatically routes to the other
- **Security**: API keys stored encrypted in Secret Manager, never in plain text
- **Scalability**: Cloud Run automatically scales based on traffic

## Troubleshooting

### Weather Features Not Working

1. **Check secret configuration:**
   ```bash
   gcloud secrets describe <service-name-prefix>-openweather-api-key
   ```

2. **Verify service account permissions:**
   ```bash
   gcloud projects get-iam-policy <project-id> --flatten="bindings[].members" --filter="bindings.members:serviceAccount:<service-name-prefix>*"
   ```

3. **Check Cloud Run logs:**
   ```bash
   gcloud logs read "resource.type=cloud_run_revision" --project=<project-id> --limit=50
   ```

### Common Issues

- **Invalid API Key**: Application logs will show warnings about placeholder values
- **Permission Denied**: Verify service account has `secretmanager.secretAccessor` role
- **Secret Not Found**: Ensure Secret Manager API is enabled and secret exists

### Log Messages to Look For

```
INFO - OPENWEATHER_API_KEY is configured and appears valid.
WARNING - OPENWEATHER_API_KEY is set to an invalid placeholder value: 'placeholder'
INFO - Using mock weather data for location: New York
```

## Cleanup

To destroy all resources:

```bash
terraform destroy
```

This will remove:
- Cloud Run services
- Load balancer and networking components
- Service account and IAM bindings
- Secret Manager secret (if not referenced elsewhere)

## Security Best Practices

- **Secrets**: Never commit API keys to version control
- **IAM**: Service account follows principle of least privilege
- **HTTPS**: Enable HTTPS for production deployments
- **IAP**: Consider enabling Identity-Aware Proxy for additional security
- **Monitoring**: Enable Cloud Logging and Monitoring for production use
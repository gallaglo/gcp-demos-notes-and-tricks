# Multi-region Cloud Run Deployment

This repo deploys Cloud Run services to two GCP cloud regions and configures a Global Application Load Balancer to route traffic to the two services.

If the variable `enable_https` is set to `true`, the load balancer will be configured for HTTPS and will serve traffic at `https://<ip-address>.nip.io`.

## Inputs 

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| container\_image | Container image URI (example: us-west1-docker.pkg.dev/logan-gallagher/cloud-run-source-deploy/whereami:latest) | `string` | `""` | yes |
| enable\_https | Enforce HTTPS for load balancer | `bool` | `false` | no |
| enable\_iap | Enable Identity-Aware Proxy protection. NOTE: enable\_https must be set to `true` | `bool` | `false` | no |
| project\_id | GCP Project ID | `string` | `""` | yes |
| region\_1 | Region of the first Cloud Run service | `string` | `"us-west1"` | no |
| region\_2 | Region of the second Cloud Run service | `string` | `"us-east1"` | no |
| service\_name\_prefix | Prefix for the Cloud Run service name | `string` | `"cloud-run"` | no |     

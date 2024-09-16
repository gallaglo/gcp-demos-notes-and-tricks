# HTTP Load Balancer and Managed Instance Group

The Terraform files in this directory provision a GCP HTTP load balancer and Managed Instance Group.

By default, the resources are deployed into the us-west1 region (Oregon) in the "default" VPC network. The only required attribute that *must* be updated to successfully deploy is the `project_id` value, which can be specified in `terraform.tfvars` or [passed at the command line](https://developer.hashicorp.com/terraform/language/values/variables#variables-on-the-command-line).

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| enable\_https | Enforce HTTPS for load balancer | `bool` | `false` | no |
| machine_type | Machine type to create | `string` |  `"e2-micro"` | no |
| project_id | The GCP project to use for integration tests | `string` | n/a | yes |
| region | The GCP region to create and test resources in | `string` | `"us-west1"` | no |
| service\_name\_prefix | Prefix for the Cloud Run service name | `string` | `"webserver"` | no |
| source_image_family | Source image family | `string` | `"debian-11"` | no |
| source_image_project |Project where the source image comes from | `string` | `"debian-cloud"` | no |

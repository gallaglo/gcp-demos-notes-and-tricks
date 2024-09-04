variable "container_image" {
  description = "Container image URI"
  type        = string
}

variable "enable_https" {
  description = "Enforce HTTPS for load balancer"
  type = bool
  default = false
}

variable "enable_iap" {
  description = "Enable Identity-Aware Proxy protection. NOTE: enable_https must be set to `true`"
  type = bool
  default = false
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region_1" {
  description = "Region of the first Cloud Run service"
  type        = string
  default     = "us-west1"
}

variable "region_2" {
  description = "Region of the second Cloud Run service"
  type        = string
  default     = "us-east1"
}

variable "service_name_prefix" {
  description = "Prefix for the Cloud Run service name"
  type        = string
  default     = "cloud-run"
}

variable "machine_type" {
  description = "Machine type to create, defaults to e2-micro"
  type        = string
  default     = "e2-micro"
}

variable "project_id" {
  description = "GCP Project ID value"
  type        = string
}

variable "region" {
  description = "GCP region, defaults to us-west1 (Oregon)"
  type        = string
  default     = "us-west1"
}

variable "source_image_family" {
  description = "Source image family, defaults to debian-11"
  type        = string
  default     = "debian-11"
}

variable "source_image_project" {
  description = "Project where the source image comes from, defaults to debian-cloud"
  type        = string
  default     = "debian-cloud"
}

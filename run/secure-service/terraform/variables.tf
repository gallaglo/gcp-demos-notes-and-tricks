variable "editor_container_image" {
  description = "Editor (Frontend) container image URI"
  type        = string
}

variable "renderer_container_image" {
  description = "Renderer (Backend) container image URI"
  type        = string
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Cloud Region for the Cloud Run services"
  type        = string
  default     = "us-west1"
}

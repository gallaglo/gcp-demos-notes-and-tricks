variable "project_id" {
  description = "The ID of the Google Cloud project"
  type        = string
}

variable "region" {
  description = "The region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "animator_container_image" {
  description = "The container image URL for the animator service"
  type        = string
}

variable "frontend_container_image" {
  description = "The container image URL for the frontend service"
  type        = string
}
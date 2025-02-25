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
  default     = ""
}

variable "frontend_container_image" {
  description = "The container image URL for the frontend service"
  type        = string
  default     = ""
}

variable "local_testing_mode" {
  description = "If true, skips creation of Cloud Run services for local development"
  type        = bool
  default     = false
}

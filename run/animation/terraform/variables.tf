variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region"
  type        = string
  default     = "us-central1"
}

variable "animator_container_image" {
  description = "Container image for the Blender animation service"
  type        = string
  default     = "gcr.io/your-project-id/animator:latest"
}

variable "agent_container_image" {
  description = "Container image for the LangGraph service"
  type        = string
  default     = "gcr.io/your-project-id/langgraph:latest"
}

variable "frontend_container_image" {
  description = "Container image for the frontend service"
  type        = string
  default     = "gcr.io/your-project-id/frontend:latest"
}

variable "local_testing_mode" {
  description = "Enable local testing mode (disables cloud resources)"
  type        = bool
  default     = false
}

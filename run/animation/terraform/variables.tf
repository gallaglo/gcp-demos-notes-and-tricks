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

# Add these variables to your variables.tf file

variable "animation_graph_path" {
  description = "Local path to the animation_graph.py file"
  type        = string
  default     = "../langgraph/animation_graph.py"
}

variable "prompts_path" {
  description = "Local path to the prompts.py file"
  type        = string
  default     = "../langgraph/prompts.py"
}

variable "requirements_path" {
  description = "Local path to the requirements.txt file for Reasoning Engine"
  type        = string
  default     = "../langgraph/requirements.txt"
}

variable "reasoning_engine_machine_type" {
  description = "Machine type for Vertex AI Reasoning Engine"
  type        = string
  default     = "n1-standard-4"
}

variable "reasoning_engine_min_replicas" {
  description = "Minimum number of replicas for Reasoning Engine"
  type        = number
  default     = 1
}

variable "reasoning_engine_max_replicas" {
  description = "Maximum number of replicas for Reasoning Engine"
  type        = number
  default     = 5
}

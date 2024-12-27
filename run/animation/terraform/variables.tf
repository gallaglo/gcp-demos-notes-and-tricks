variable "region" {
  description = "The region to deploy the services"
  type        = string
}

variable "animator_container_image" {
  description = "The container image URL for the animator service"
  type        = string
}

variable "frontend_container_image" {
  description = "The container image URL for the frontend service"
  type        = string
}

variable "bucket_name" {
  description = "Name of existing bucket. Leave empty for first deployment to create new bucket"
  type        = string
  default     = ""
}

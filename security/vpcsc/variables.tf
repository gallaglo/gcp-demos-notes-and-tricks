variable "project_id" {
  type        = string
  description = "GCP Project ID"
}

variable "region" {
  type        = string
  description = "GCP Region"
  default     = "us-central1"
}

variable "zone" {
  type        = string
  description = "GCP Zone"
  default     = "us-central1-a"
}

variable "service_perimeter_name" {
  type        = string
  description = "Name for the VPC Service Controls perimeter"
  default     = "storage_perimeter"
}

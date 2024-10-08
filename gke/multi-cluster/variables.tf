variable "project_id" {
  description = "value of the project_id"
  type        = string
}

variable "region_1" {
  description = "The region of the first cluster"
  type        = string
  default     = "us-west1"
}

variable "region_2" {
  description = "The region of the second cluster"
  type        = string
  default     = "us-east1"
}

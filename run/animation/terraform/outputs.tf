output "frontend_url" {
  description = "The URL of the frontend service"
  value       = var.local_testing_mode ? "http://localhost:3000" : try(google_cloud_run_v2_service.frontend[0].uri, null)
}

output "animator_url" {
  description = "The URL of the animator backend service"
  value       = var.local_testing_mode ? "http://localhost:8080" : try(google_cloud_run_v2_service.animator[0].uri, null)
}

output "bucket_name" {
  description = "The name of the GCS bucket for animator assets"
  value       = google_storage_bucket.animator_assets.name
}

output "project_id" {
  description = "The Google Cloud project ID"
  value       = var.project_id
}

output "region" {
  description = "The deployment region"
  value       = var.region
}

output "deployment_mode" {
  description = "The current deployment mode"
  value       = var.local_testing_mode ? "local testing" : "cloud deployment"
}

# Output the Reasoning Engine endpoint URL
output "reasoning_engine_endpoint" {
  value       = google_vertex_ai_reasoning_engine_endpoint.animation_endpoint.uri
  description = "URI of the deployed Reasoning Engine endpoint"
}

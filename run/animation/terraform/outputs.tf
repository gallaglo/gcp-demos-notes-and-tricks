# Outputs
output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "animator_url" {
  value = google_cloud_run_v2_service.animator.uri
}
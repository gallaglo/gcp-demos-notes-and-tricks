output "editor_service_url" {
  description = "The URL of the editor Cloud Run service"
  value       = google_cloud_run_v2_service.editor.uri
}

output "renderer_service_url" {
  description = "The URL of the renderer Cloud Run service"
  value       = google_cloud_run_v2_service.renderer.uri
}

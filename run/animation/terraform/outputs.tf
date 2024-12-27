output "frontend_url" {
  value = google_cloud_run_v2_service.frontend.uri
}

output "animator_url" {
  value = google_cloud_run_v2_service.animator.uri
}

output "bucket_name" {
  value = var.bucket_name != "" ? data.google_storage_bucket.existing_assets[0].name : google_storage_bucket.new_assets[0].name
}

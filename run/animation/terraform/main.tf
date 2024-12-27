# Service account for the animator service
resource "google_service_account" "animator" {
  account_id   = "animator-identity"
  display_name = "Service identity of the Animator (Backend) service."
}

# Animator service configuration
resource "google_cloud_run_v2_service" "animator" {
  name                = "animator"
  location            = var.region
  deletion_protection = false # set to "true" in production

  template {
    containers {
      # Replace with the URL of your Animator service image
      #   gcr.io/<PROJECT_ID>/animator
      image = var.animator_container_image
    }
    service_account = google_service_account.animator.email
  }
}

# Service account for frontend service
resource "google_service_account" "frontend" {
  account_id   = "frontend-identity"
  display_name = "Service identity of the Frontend service."
}

# Grant access to the frontend-identity to invoke the animator service
resource "google_cloud_run_service_iam_member" "frontend_invokes_animator" {
  location = google_cloud_run_v2_service.animator.location
  service  = google_cloud_run_v2_service.animator.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend.email}"
}

# Frontend service
resource "google_cloud_run_v2_service" "frontend" {
  name                = "frontend"
  location            = var.region
  deletion_protection = false # set to "true" in production

  template {
    containers {
      # Replace with the URL of your Frontend service image
      #   gcr.io/<PROJECT_ID>/frontend
      image = var.frontend_container_image
      env {
        name  = "FRONTEND_ANIMATOR_URL"
        value = google_cloud_run_v2_service.animator.uri
      }
    }
    service_account = google_service_account.frontend.email
  }
}

# Allow public access to frontend service
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location    = google_cloud_run_v2_service.frontend.location
  project     = google_cloud_run_v2_service.frontend.project
  service     = google_cloud_run_v2_service.frontend.name
  policy_data = data.google_iam_policy.noauth.policy_data
}

# Try to get the existing bucket if it exists
data "google_storage_bucket" "existing_assets" {
  count = var.bucket_name != "" ? 1 : 0
  name  = var.bucket_name
}

# Create new bucket if it doesn't exist
resource "google_storage_bucket" "new_assets" {
  count    = var.bucket_name != "" ? 0 : 1
  name     = "animation-assets-${random_string.bucket_suffix[0].result}"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy               = false

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90 # days
    }
    action {
      type = "Delete"
    }
  }
}

# Random suffix for new bucket
resource "random_string" "bucket_suffix" {
  count   = var.bucket_name != "" ? 0 : 1
  length  = 8
  special = false
  upper   = false
}

# Grant animator service access to GCS bucket
resource "google_storage_bucket_iam_member" "animator_bucket_access" {
  bucket = var.bucket_name != "" ? data.google_storage_bucket.existing_assets[0].name : google_storage_bucket.new_assets[0].name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.animator.email}"
}

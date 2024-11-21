# service account to serve as the "compute identity" of the render service
resource "google_service_account" "renderer" {
  account_id   = "renderer-identity"
  display_name = "Service identity of the Renderer (Backend) service."
}

# deny unauthenticated access to renderer service
resource "google_cloud_run_v2_service" "renderer" {
  name     = "renderer"
  location = var.region

  deletion_protection = false # set to "true" in production

  template {
    containers {
      # Replace with the URL of your Secure Services > Renderer image.
      #   gcr.io/<PROJECT_ID>/renderer
      image = var.renderer_container_image
    }
    service_account = google_service_account.renderer.email
  }
}

# service account for editor (frontend) service
resource "google_service_account" "editor" {
  account_id   = "editor-identity"
  display_name = "Service identity of the Editor (Frontend) service."
}

# Grant access to the editor-identity compute identity to invoke the Markdown rendering service
resource "google_cloud_run_service_iam_member" "editor_invokes_renderer" {
  location = google_cloud_run_v2_service.renderer.location
  service  = google_cloud_run_v2_service.renderer.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.editor.email}"
}

# editor service
resource "google_cloud_run_v2_service" "editor" {
  name     = "editor"
  location = var.region

  deletion_protection = false # set to "true" in production

  template {
    containers {
      # Replace with the URL of your Secure Services > Editor image.
      #   gcr.io/<PROJECT_ID>/editor
      image = var.editor_container_image
      env {
        name  = "EDITOR_UPSTREAM_RENDER_URL"
        value = google_cloud_run_v2_service.renderer.uri
      }
    }
    service_account = google_service_account.editor.email

  }
}

# Grant allUsers permission to invoke the editor service
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_v2_service.editor.location
  project  = google_cloud_run_v2_service.editor.project
  service  = google_cloud_run_v2_service.editor.name

  policy_data = data.google_iam_policy.noauth.policy_data
}
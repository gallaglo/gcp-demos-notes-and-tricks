# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "aiplatform.googleapis.com",
    "generativelanguage.googleapis.com",
    "apikeys.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com"
  ])

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Resource ID suffix for GCS bucket and API key
resource "random_id" "resource_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "animator_assets" {
  name          = "${var.project_id}-animator-assets-${random_id.resource_suffix.hex}"
  project       = var.project_id
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }
}

# Service account for animator service
resource "google_service_account" "animator" {
  depends_on   = [google_project_service.required_apis]
  account_id   = "animator-identity"
  display_name = "Service identity of the Animator service"
  project      = var.project_id
}

# Grant animator service account required permissions
resource "google_project_iam_member" "animator_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.animator.email}"
}

resource "google_project_iam_member" "animator_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.animator.email}"
}

# API key for Vertex AI and Gemini
# adds a random suffix to the key name to ensure uniqueness due to apparent sof-deletion/caching issue
resource "google_apikeys_key" "animator_api_key" {
  depends_on = [google_project_service.required_apis]
  name         = "animator-api-key-${random_id.resource_suffix.hex}"
  display_name = "Animator Service API Key"
  project      = var.project_id

  restrictions {
    api_targets {
      service = "aiplatform.googleapis.com"  # Vertex AI API
    }

    api_targets {
      service = "generativelanguage.googleapis.com"  # Generative Language API
    }

    api_targets {
      service = "gemini.generativelanguage.googleapis.com"  # Gemini for Google Cloud API
    }
  }
}

# Animator service
resource "google_cloud_run_v2_service" "animator" {
  name                = "animator"
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    containers {
      image = var.animator_container_image

      ports {
        container_port = 8080
      }

      resources {
        limits = {
          cpu    = "1000m"
          memory = "1Gi"
        }
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.animator_assets.name
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "GOOGLE_APPLICATION_CREDENTIALS"
        value = "/run/secrets/key.json"
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret = google_secret_manager_secret.animator_api_key.secret_id
            version = "latest"
          }
        }
      }

      volume_mounts {
        name       = "service-account"
        mount_path = "/run/secrets"
      }
    }

    volumes {
      name = "service-account"
      secret {
        secret = google_secret_manager_secret.animator_sa_key.secret_id
        items {
          version = "latest"
          path    = "key.json"
        }
      }
    }

    service_account = google_service_account.animator.email
  }
}

# Frontend service account
resource "google_service_account" "frontend" {
  account_id   = "frontend-identity"
  display_name = "Service identity of the Frontend service"
  project      = var.project_id
}

# Grant frontend service account permission to invoke animator
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
  project             = var.project_id
  deletion_protection = false

  template {
    containers {
      image = var.frontend_container_image

      env {
        name  = "BACKEND_SERVICE_URL"
        value = google_cloud_run_v2_service.animator.uri
      }
    }

    service_account = google_service_account.frontend.email
  }
}

# Allow public access to frontend
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "public_frontend" {
  location    = google_cloud_run_v2_service.frontend.location
  project     = google_cloud_run_v2_service.frontend.project
  service     = google_cloud_run_v2_service.frontend.name
  policy_data = data.google_iam_policy.noauth.policy_data
}

# Secrets
resource "google_secret_manager_secret" "animator_api_key" {
  secret_id = "animator-api-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "animator_api_key_version" {
  secret      = google_secret_manager_secret.animator_api_key.id
  secret_data = google_apikeys_key.animator_api_key.key_string
}

resource "google_secret_manager_secret" "animator_sa_key" {
  secret_id = "animator-sa-key"
  project   = var.project_id

  replication {
    auto {}
  }
}

resource "google_service_account_key" "animator_sa_key" {
  service_account_id = google_service_account.animator.name
}

resource "google_secret_manager_secret_version" "animator_sa_key_version" {
  secret      = google_secret_manager_secret.animator_sa_key.id
  secret_data = base64decode(google_service_account_key.animator_sa_key.private_key)
}
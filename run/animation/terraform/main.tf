locals {
  required_apis = [
    "aiplatform.googleapis.com",
    "generativelanguage.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "iam.googleapis.com",
    "storage.googleapis.com"
  ]

  service_name_prefix = "${var.project_id}-animator"

  animator_iam_roles = [
    "roles/storage.admin",
    "roles/aiplatform.user"
  ]

  # Simplify conditional logic
  create_cloud_resources = !var.local_testing_mode
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset(local.required_apis)

  project = var.project_id
  service = each.value

  disable_on_destroy = false
}

# Storage bucket for animator assets
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_storage_bucket" "animator_assets" {
  name          = "${local.service_name_prefix}-assets-${random_id.bucket_suffix.hex}"
  project       = var.project_id
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.required_apis["storage.googleapis.com"]]
}

# Service accounts
resource "google_service_account" "animator" {
  account_id   = "animator-identity"
  display_name = "Service identity of the Animator service"
  project      = var.project_id

  depends_on = [google_project_service.required_apis["iam.googleapis.com"]]
}

resource "google_service_account" "frontend" {
  count        = local.create_cloud_resources ? 1 : 0
  account_id   = "frontend-identity"
  display_name = "Service identity of the Frontend service"
  project      = var.project_id

  depends_on = [google_project_service.required_apis["iam.googleapis.com"]]
}

# Service account key 
resource "google_service_account_key" "animator_sa_key" {
  service_account_id = google_service_account.animator.name
}

# Secret management for service account key
resource "google_secret_manager_secret" "animator_sa_key" {
  count     = local.create_cloud_resources ? 1 : 0
  secret_id = "animator-sa-key"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.required_apis["secretmanager.googleapis.com"]]
}

resource "google_secret_manager_secret_version" "animator_sa_key_version" {
  count       = local.create_cloud_resources ? 1 : 0
  secret      = google_secret_manager_secret.animator_sa_key[0].id
  secret_data = base64decode(google_service_account_key.animator_sa_key.private_key)
}

# IAM permissions
resource "google_secret_manager_secret_iam_member" "animator_secret_accessor" {
  count     = local.create_cloud_resources ? 1 : 0
  project   = var.project_id
  secret_id = google_secret_manager_secret.animator_sa_key[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.animator.email}"
}

# Simplified IAM role assignments using for_each
resource "google_project_iam_member" "animator_roles" {
  for_each = toset(local.animator_iam_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.animator.email}"
}

# Cloud Run Services
resource "google_cloud_run_v2_service" "animator" {
  count               = local.create_cloud_resources ? 1 : 0
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

      startup_probe {
        initial_delay_seconds = 15
        timeout_seconds       = 5
        period_seconds        = 10
        failure_threshold     = 3
        http_get {
          path = "/health"
          port = 8080
        }
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        period_seconds    = 30
        timeout_seconds   = 10
        failure_threshold = 3
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

      volume_mounts {
        name       = "service-account"
        mount_path = "/run/secrets"
      }
    }

    volumes {
      name = "service-account"
      secret {
        secret = google_secret_manager_secret.animator_sa_key[0].secret_id
        items {
          version = "latest"
          path    = "key.json"
        }
      }
    }

    service_account = google_service_account.animator.email
  }

  depends_on = [
    google_secret_manager_secret_version.animator_sa_key_version,
    google_project_service.required_apis["run.googleapis.com"]
  ]
}

resource "google_cloud_run_v2_service" "frontend" {
  count               = local.create_cloud_resources ? 1 : 0
  name                = "frontend"
  location            = var.region
  project             = var.project_id
  deletion_protection = false

  template {
    containers {
      image = var.frontend_container_image

      env {
        name  = "BACKEND_SERVICE_URL"
        value = google_cloud_run_v2_service.animator[0].uri
      }
    }

    service_account = google_service_account.frontend[0].email
  }

  depends_on = [google_project_service.required_apis["run.googleapis.com"]]
}

# IAM policy for animator service access
resource "google_cloud_run_service_iam_member" "frontend_invokes_animator" {
  count    = local.create_cloud_resources ? 1 : 0
  project  = var.project_id
  location = google_cloud_run_v2_service.animator[0].location
  service  = google_cloud_run_v2_service.animator[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.frontend[0].email}"
}

# Public access policy
data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "public_frontend" {
  count       = local.create_cloud_resources ? 1 : 0
  location    = google_cloud_run_v2_service.frontend[0].location
  project     = google_cloud_run_v2_service.frontend[0].project
  service     = google_cloud_run_v2_service.frontend[0].name
  policy_data = data.google_iam_policy.noauth.policy_data
}

# Local testing specific resources
resource "local_file" "animator_sa_key" {
  count           = var.local_testing_mode ? 1 : 0
  filename        = "../animator-sa-key.json"
  content         = base64decode(google_service_account_key.animator_sa_key.private_key)
  file_permission = "0600"
}

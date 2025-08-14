provider "google" {
  project = var.project_id
}

locals {
  # trim any trailing hyphen from the service name prefix
  service_name_prefix = trimsuffix(var.service_name_prefix, "-")
}

# Enable required APIs
resource "google_project_service" "secretmanager" {
  project = var.project_id
  service = "secretmanager.googleapis.com"
}

module "service_accounts" {
  source       = "terraform-google-modules/service-accounts/google"
  version      = "~> 4.0"
  project_id   = var.project_id
  prefix       = local.service_name_prefix
  names        = ["service"]
  display_name = "Cloud Run Service Account"
  description  = "Service Account for ${local.service_name_prefix}"
  project_roles = [
    "${var.project_id}=>roles/aiplatform.user",
    "${var.project_id}=>roles/compute.viewer",
    "${var.project_id}=>roles/serviceusage.serviceUsageViewer",
    "${var.project_id}=>roles/logging.logWriter",
    "${var.project_id}=>roles/monitoring.metricWriter",
    "${var.project_id}=>roles/cloudtrace.agent",
    "${var.project_id}=>roles/secretmanager.secretAccessor"
  ]
}

# Create the secret for OpenWeather API key
resource "google_secret_manager_secret" "openweather_api_key" {
  project   = var.project_id
  secret_id = "${local.service_name_prefix}-openweather-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# Create a secret version (you'll need to update this with the actual API key)
# Note: It's recommended to set this manually after creation for security
resource "google_secret_manager_secret_version" "openweather_api_key" {
  secret      = google_secret_manager_secret.openweather_api_key.id
  secret_data = var.openweather_api_key # Define this as a sensitive variable

  lifecycle {
    ignore_changes = [secret_data]
  }
}

resource "google_cloud_run_v2_service" "default" {
  for_each = toset([var.region_1, var.region_2])
  name     = "${local.service_name_prefix}-${each.key}"
  location = each.key
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = module.service_accounts.email

    containers {
      image = var.container_image
      resources {
        limits = {
          memory = "1Gi"
        }
      }

      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }

      # Add environment variable for the secret
      env {
        name = "OPENWEATHER_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.openweather_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [
    google_secret_manager_secret_version.openweather_api_key
  ]
}

# allow unauthenicated invocations of the Cloud Run service
# NOTE: the Cloud Run service will still not be directly accessible, 
# all traffic must go through the load balancer due to the `ingress` property
resource "google_cloud_run_service_iam_member" "public-access" {
  for_each = toset([var.region_1, var.region_2])

  project  = var.project_id
  location = google_cloud_run_v2_service.default[each.key].location
  service  = google_cloud_run_v2_service.default[each.key].name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  for_each = toset([var.region_1, var.region_2])

  provider              = google-beta
  region                = each.key
  project               = var.project_id
  name                  = "${each.key}-serverless-neg"
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_v2_service.default[each.key].name
  }
}

# only create public IP address and SSL certificate if var.enable_https is `true`
module "https" {
  source = "../../modules/https"
  count  = var.enable_https ? 1 : 0
  name   = local.service_name_prefix
}

module "lb-http" {
  source  = "terraform-google-modules/lb-http/google//modules/serverless_negs"
  version = "~> 10.0"

  name                  = local.service_name_prefix
  project               = var.project_id
  load_balancing_scheme = "EXTERNAL_MANAGED"
  labels = {
    "service-name" = var.service_name_prefix,
    "project-id"   = var.project_id
  }

  # if var.enable_https is `true` set the following attributes to `true`
  ssl = var.enable_https

  # if var.enable_https is `true` set the following attributes to `false`
  create_address = var.enable_https ? false : true
  http_forward   = var.enable_https ? false : true

  # if var.enable_https is `true`, provide IP address and SSL certificate created by https module
  ssl_certificates = var.enable_https ? [module.https[0].ssl_certificate] : []
  address          = var.enable_https ? module.https[0].ip_address : null

  backends = {
    default = {
      description = null
      groups = [
        for region in toset([var.region_1, var.region_2]) : {
          group = google_compute_region_network_endpoint_group.serverless_neg[region].id
        }
      ]
      enable_cdn = false

      # only allow iap_config to be enabled if var.enable_https is `true`
      iap_config = {
        enable = var.enable_https ? var.enable_iap : false
      }
      log_config = {
        enable = false
      }
    }
  }
}

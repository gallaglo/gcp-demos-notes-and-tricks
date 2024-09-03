provider "google" {
  project = var.project_id
}

locals {
  # trim any trailing hyphen from the service name prefix
  service_name_prefix = trimsuffix(var.service_name_prefix, "-")
}

module "service_accounts" {
  source      = "terraform-google-modules/service-accounts/google"
  version     = "~> 4.0"
  project_id  = var.project_id
  prefix      = local.service_name_prefix
  description = "Service account for Cloud Run service"
  project_roles = [
    "roles/aiplatform.user"
  ]
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
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
    }
  }
}

resource "google_compute_region_network_endpoint_group" "serverless_neg" {
  for_each = toset([var.region_1, var.region_2])

  provider              = google-beta
  region                = each.key
  name                  = "${each.key}-serverless-neg"
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = google_cloud_run_service.default[each.key].name
  }
}

module "lb-http" {
  source  = "terraform-google-modules/lb-http/google//modules/serverless_negs"
  version = "~> 10.0"

  name    = "${local.service_name_prefix}-lb"
  project = var.project_id

  #ssl                             = var.ssl
  #managed_ssl_certificate_domains = [var.domain]
  #https_redirect                  = var.ssl
  #labels = { "example-label" = "cloud-run-example" }

  backends = {
    default = {
      description = null
      groups = [
        {
          group = google_compute_region_network_endpoint_group.serverless_neg[var.region_1].id
        },
        {
          group = google_compute_region_network_endpoint_group.serverless_neg[var.region_2].id
        }
      ]
      enable_cdn = false

      iap_config = {
        enable = false
      }
      log_config = {
        enable = false
      }
    }
  }
}

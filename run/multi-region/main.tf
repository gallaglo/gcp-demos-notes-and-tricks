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
        {
          group = google_compute_region_network_endpoint_group.serverless_neg[var.region_1].id
        },
        {
          group = google_compute_region_network_endpoint_group.serverless_neg[var.region_2].id
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

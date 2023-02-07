provider "google" {
  project = var.project_id
}

# retrieve ID of "default" VPC network in project
data "google_compute_network" "default" {
  name = "default"
}

data "google_compute_subnetwork" "default" {
  name   = "default"
  region = var.region
}

module "instance_template" {
  source  = "terraform-google-modules/vm/google//modules/instance_template"
  version = "8.0.0"
  access_config = [{
    nat_ip       = null
    network_tier = "STANDARD"
  }]
  name_prefix  = "webserver-template"
  machine_type = var.machine_type
  network      = data.google_compute_network.default.self_link
  subnetwork   = data.google_compute_subnetwork.default.self_link
  service_account = {
    email  = ""
    scopes = ["cloud-platform"]
  }
  source_image_family  = var.source_image_family
  source_image_project = var.source_image_project
  startup_script       = file("${path.module}/startup-script")
  tags                 = []
}

module "mig" {
  source            = "terraform-google-modules/vm/google//modules/mig"
  version           = "8.0.0"
  instance_template = module.instance_template.self_link
  region            = var.region
  hostname          = "webserver-mig"
  target_size       = 2
  named_ports = [{
    name = "http",
    port = 80
  }]
  update_policy = [{
    type                         = "PROACTIVE"
    minimal_action               = "REPLACE"
    max_surge_fixed              = 4
    instance_redistribution_type = null
    max_surge_percent            = null
    max_unavailable_fixed        = null
    max_unavailable_percent      = null
    min_ready_sec                = null
    replacement_method           = null
  }]
}

module "gce-lb-http" {
  source            = "GoogleCloudPlatform/lb-http/google"
  version           = "7.0.0"
  name              = "webserver-http-lb"
  project           = var.project_id
  target_tags       = []
  firewall_networks = [data.google_compute_network.default.name]


  backends = {
    default = {
      description                     = null
      protocol                        = "HTTP"
      port                            = 80
      port_name                       = "http"
      timeout_sec                     = 10
      connection_draining_timeout_sec = null
      enable_cdn                      = false
      compression_mode                = null
      security_policy                 = null
      session_affinity                = null
      affinity_cookie_ttl_sec         = null
      custom_request_headers          = null
      custom_response_headers         = null

      health_check = {
        check_interval_sec  = null
        timeout_sec         = null
        healthy_threshold   = null
        unhealthy_threshold = null
        request_path        = "/"
        port                = 80
        host                = null
        logging             = null
      }

      log_config = {
        enable      = false
        sample_rate = null
      }

      groups = [
        {
          group                        = module.mig.instance_group
          balancing_mode               = null
          capacity_scaler              = null
          description                  = null
          max_connections              = null
          max_connections_per_instance = null
          max_connections_per_endpoint = null
          max_rate                     = null
          max_rate_per_instance        = null
          max_rate_per_endpoint        = null
          max_utilization              = null
        }
      ]

      iap_config = {
        enable               = false
        oauth2_client_id     = ""
        oauth2_client_secret = ""
      }
    }
  }
}

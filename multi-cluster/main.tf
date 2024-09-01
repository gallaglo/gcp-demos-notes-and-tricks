provider "google" {
  project = var.project_id
}

data "google_project" "project" {
  project_id = var.project_id
}

# enable the required APIs if they are not already enabled
module "project-services" {
  source  = "terraform-google-modules/project-factory/google//modules/project_services"
  version = "~> 16.0"

  project_id                  = var.project_id
  disable_services_on_destroy = false

  activate_apis = [
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "container.googleapis.com",
    "gkehub.googleapis.com",
    "trafficdirector.googleapis.com",
    "multiclusterservicediscovery.googleapis.com",
    "multiclusteringress.googleapis.com"
  ]
}

resource "google_container_cluster" "cluster_1" {
  depends_on          = [module.project-services]
  name                = "${var.region_1}-gke-cluster"
  location            = "${var.region_1}-a"
  project             = var.project_id
  initial_node_count  = 3
  deletion_protection = false
  cluster_autoscaling {
    enabled = true
    resource_limits {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 12
    }
    resource_limits {
      resource_type = "memory"
      minimum       = 1
      maximum       = 64
    }
  }
  fleet {
    project = var.project_id
  }
  gateway_api_config {
    channel = "CHANNEL_STANDARD"
  }
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

resource "google_container_cluster" "cluster_2" {
  depends_on          = [module.project-services]
  name                = "${var.region_2}-gke-cluster"
  location            = "${var.region_2}-a"
  project             = var.project_id
  initial_node_count  = 3
  deletion_protection = false
  cluster_autoscaling {
    enabled = true
    resource_limits {
      resource_type = "cpu"
      minimum       = 1
      maximum       = 12
    }
    resource_limits {
      resource_type = "memory"
      minimum       = 1
      maximum       = 64
    }
  }
  fleet {
    project = var.project_id
  }
  gateway_api_config {
    channel = "CHANNEL_STANDARD"
  }
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
}

# Enable multi-cluster Services in your fleet for the registered clusters 
resource "google_gke_hub_feature" "services" {
  name     = "multiclusterservicediscovery"
  location = "global"
}

# Grant Identity and Access Management (IAM) permissions required by the MCS controller
resource "google_project_iam_binding" "network_viewer" {
  depends_on = [google_gke_hub_feature.services]
  project    = var.project_id
  role       = "roles/compute.networkViewer"
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[gke-mcs/gke-mcs-importer]"
  ]
}

# Enable multi-cluster Gateway and specify the region_1 cluster as the config cluster in your fleet
resource "google_gke_hub_feature" "ingress" {
  name     = "multiclusteringress"
  location = var.region_1
  spec {
    multiclusteringress {
      config_membership = google_container_cluster.cluster_1.fleet.0.membership
    }
  }
}

# Grant Identity and Access Management (IAM) permissions required by the multi-cluster Gateway controller
resource "google_project_iam_binding" "container_admin" {
  depends_on = [google_gke_hub_feature.ingress]
  project    = var.project_id
  role       = "roles/container.admin"
  members = [
    "serviceAccount:service-${data.google_project.project.number}@gcp-sa-multiclusteringress.iam.gserviceaccount.com"
  ]
}


provider "google" {
  project = var.project_id
}

# Retrieve ID of "default" VPC network in project
data "google_compute_network" "default" {
  name = "default"
}

data "google_compute_subnetwork" "default" {
  name   = "default"
  region = var.region
}

# Get the project information
data "google_project" "project" {
  project_id = var.project_id
}

# Get current access policy
data "google_access_context_manager_access_policy" "default" {
  parent = "organizations/${data.google_project.project.org_id}"
}

###########################
# Storage Bucket
###########################

resource "google_storage_bucket" "vpcsc_demo_bucket" {
  name     = "${var.project_id}-vpcsc-demo-bucket"
  location = var.region

  # Recommended settings for production
  uniform_bucket_level_access = true

  # Depends on the service perimeter being created
  depends_on = [
    google_access_context_manager_service_perimeter.storage_perimeter
  ]
}

###########################
# Compute Engine VM
###########################

resource "google_compute_instance" "vm_instance" {
  name         = "vpcsc-demo-vm"
  machine_type = "e2-medium"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
    }
  }

  network_interface {
    network    = data.google_compute_network.default.self_link
    subnetwork = data.google_compute_subnetwork.default.self_link

    access_config {
    }
  }

  # Grant the VM access to GCS
  service_account {
    # Default compute service account
    email = "${data.google_project.project.number}-compute@developer.gserviceaccount.com"
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_write",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/compute",
    ]
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    apt-get update
    apt-get install -y google-cloud-sdk
    
    # Test access to the bucket
    echo "Testing access to GCS bucket..."
    gsutil ls gs://${var.project_id}-vpcsc-demo-bucket || echo "Access failed"
  EOF

  # Ensure the VM is created after the VPC SC perimeter
  depends_on = [
    google_access_context_manager_service_perimeter.storage_perimeter
  ]
}

###########################
# VPC Service Controls
###########################

resource "google_access_context_manager_service_perimeter" "storage_perimeter" {
  parent = "accessPolicies/${data.google_access_context_manager_access_policy.default[0].name}"
  name   = "accessPolicies/${data.google_access_context_manager_access_policy.default[0].name}/servicePerimeters/${var.service_perimeter_name}"
  title  = var.service_perimeter_name

  status {
    restricted_services = ["storage.googleapis.com"]

    vpc_accessible_services {
      enable_restriction = true
      allowed_services   = ["storage.googleapis.com"]
    }

    # Add the project to the perimeter
    resources = ["projects/${data.google_project.project.number}"]

    # Configure ingress policy to allow access from the default VPC
    ingress_policies {
      ingress_from {
        sources {
          resource = "projects/${data.google_project.project.number}/networks/${data.google_compute_network.default.name}"
        }
        identity_type = "ANY_IDENTITY"
      }

      ingress_to {
        resources = ["*"]
        operations {
          service_name = "storage.googleapis.com"
          method_selectors {
            method = "*"
          }
        }
      }
    }
  }

  # Specify the perimeter type
  perimeter_type = "PERIMETER_TYPE_REGULAR"
}

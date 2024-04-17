module "test-vpc-module" {
  source       = "terraform-google-modules/network/google"
  version      = "~> 9.0"
  project_id   = var.project_id
  network_name = "my-serverless-network"
  mtu          = 1460

  subnets = [
    {
      subnet_name   = "serverless-subnet"
      subnet_ip     = "10.10.10.0/28"
      subnet_region = var.region
    }
  ]
}

module "serverless-connector" {
  source     = "terraform-google-modules/network/google//modules/vpc-serverless-connector-beta"
  version    = "~> 9.0"
  project_id = var.project_id
  vpc_connectors = [{
    name          = "central-serverless"
    region        = var.region
    subnet_name   = module.test-vpc-module.subnets["us-central1/serverless-subnet"].name
    machine_type  = "e2-standard-4"
    min_instances = 2
    max_instances = 7
    }
  ]
}

resource "google_redis_instance" "myinstance" {
  name           = "myinstance"
  memory_size_gb = 2
  region         = var.region
  redis_version  = "REDIS_6_X"

  authorized_network = module.test-vpc-module.network.self_link

  redis_configs = {
    maxmemory-policy = "volatile-lru"
  }
}

resource "google_cloud_run_service" "my_service" {
  name     = "visit-counter"
  location = var.region

  template {
    spec {
      containers {
        image = "us-docker.pkg.dev/${var.project_id}/visit-count/main"
        env {
          name  = "REDISHOST"
          value = google_redis_instance.myinstance.host
        }

        env {
          name  = "REDISPORT"
          value = google_redis_instance.myinstance.port
        }
      }
    }
  }

  metadata {
    annotations = {
      "run.googleapis.com/vpc-access-connector" = module.serverless-connector.vpc_connectors["central-serverless"].connector_id
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }
}

data "google_iam_policy" "noauth" {
  binding {
    role = "roles/run.invoker"
    members = [
      "allUsers",
    ]
  }
}

resource "google_cloud_run_service_iam_policy" "noauth" {
  location = google_cloud_run_service.my_service.location
  project  = google_cloud_run_service.my_service.project
  service  = google_cloud_run_service.my_service.name

  policy_data = data.google_iam_policy.noauth.policy_data
}

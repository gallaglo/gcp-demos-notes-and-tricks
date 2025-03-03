# Service account for the Reasoning Engine
resource "google_service_account" "reasoning_engine" {
  account_id   = "reasoning-engine-identity"
  display_name = "Service identity of the Reasoning Engine"
  project      = var.project_id

  depends_on = [google_project_service.required_apis["iam.googleapis.com"]]
}

# IAM roles for Reasoning Engine service account
locals {
  reasoning_engine_iam_roles = [
    "roles/storage.admin",
    "roles/aiplatform.user",
    "roles/run.invoker" # To invoke the Blender service
  ]
}

resource "google_project_iam_member" "reasoning_engine_roles" {
  for_each = toset(local.reasoning_engine_iam_roles)

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.reasoning_engine.email}"
}

# Storage bucket for code and models
resource "google_storage_bucket" "reasoning_engine_code" {
  name          = "${local.service_name_prefix}-code-${random_id.bucket_suffix.hex}"
  project       = var.project_id
  location      = var.region
  force_destroy = true

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  depends_on = [google_project_service.required_apis["storage.googleapis.com"]]
}

# Upload code to GCS
resource "google_storage_bucket_object" "animation_graph" {
  name   = "code/animation_graph.py"
  bucket = google_storage_bucket.reasoning_engine_code.name
  source = var.animation_graph_path

  depends_on = [google_storage_bucket.reasoning_engine_code]
}

resource "google_storage_bucket_object" "prompts" {
  name   = "code/prompts.py"
  bucket = google_storage_bucket.reasoning_engine_code.name
  source = var.prompts_path

  depends_on = [google_storage_bucket.reasoning_engine_code]
}

resource "google_storage_bucket_object" "requirements" {
  name   = "code/requirements.txt"
  bucket = google_storage_bucket.reasoning_engine_code.name
  source = var.requirements_path

  depends_on = [google_storage_bucket.reasoning_engine_code]
}

# Create the Vertex AI Reasoning Engine Application
resource "google_vertex_ai_reasoning_engine_application" "animation_engine" {
  project      = var.project_id
  region       = var.region
  display_name = "animation-generator"
  description  = "Generates 3D animations from text descriptions using Blender"

  graph_path     = "gs://${google_storage_bucket.reasoning_engine_code.name}/code/"
  entry_module   = "animation_graph"
  entry_function = "create_animation_graph"

  service_account = google_service_account.reasoning_engine.email

  network = "projects/${var.project_id}/global/networks/default"

  environment_variables = {
    BLENDER_SERVICE_URL = google_cloud_run_v2_service.animator[0].uri
  }

  depends_on = [
    google_project_service.required_apis["aiplatform.googleapis.com"],
    google_storage_bucket_object.animation_graph,
    google_storage_bucket_object.prompts,
    google_storage_bucket_object.requirements
  ]
}

# Create the Vertex AI Reasoning Engine Endpoint
resource "google_vertex_ai_reasoning_engine_endpoint" "animation_endpoint" {
  project      = var.project_id
  region       = var.region
  display_name = "animation-generator-endpoint"
  application  = google_vertex_ai_reasoning_engine_application.animation_engine.id

  machine_type      = var.reasoning_engine_machine_type
  min_replica_count = var.reasoning_engine_min_replicas
  max_replica_count = var.reasoning_engine_max_replicas

  container_image_uri = "us-docker.pkg.dev/vertex-ai/prediction/langgraph-serving:latest"

  depends_on = [google_vertex_ai_reasoning_engine_application.animation_engine]
}

# outputs.tf

output "cloud_run_services" {
  description = "URLs of the deployed Cloud Run services"
  value = {
    for region, service in google_cloud_run_v2_service.default : region => {
      name     = service.name
      url      = service.uri
      location = service.location
      status   = service.status
    }
  }
}

output "load_balancer_ip" {
  description = "IP address of the Global Load Balancer"
  value       = var.enable_https ? module.https[0].ip_address : module.lb-http.external_ip
}

output "secret_manager_secret" {
  description = "Name of the Secret Manager secret containing the OpenWeather API key"
  value       = google_secret_manager_secret.openweather_api_key.secret_id
}

output "service_account_email" {
  description = "Email of the created service account"
  value       = module.service_accounts.email
}

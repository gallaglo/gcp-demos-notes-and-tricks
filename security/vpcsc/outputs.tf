output "bucket_name" {
  value       = google_storage_bucket.vpcsc_demo_bucket.name
  description = "Name of the created GCS bucket"
}

output "vm_name" {
  value       = google_compute_instance.vm_instance.name
  description = "Name of the created VM instance"
}

output "vm_internal_ip" {
  value       = google_compute_instance.vm_instance.network_interface[0].network_ip
  description = "Internal IP of the VM instance"
}

output "vm_external_ip" {
  value       = google_compute_instance.vm_instance.network_interface[0].access_config[0].nat_ip
  description = "External IP of the VM instance"
}

output "vpc_network_name" {
  value       = data.google_compute_network.default.name
  description = "The VPC network name"
}

output "vpc_subnetwork_name" {
  value       = data.google_compute_subnetwork.default.name
  description = "The VPC subnetwork name"
}

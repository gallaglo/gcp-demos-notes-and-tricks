output "certificate_map_id" {
  value = google_certificate_manager_certificate_map.certificate_map.id
}

output "ip_address" {
  value = google_compute_global_address.default.address
}

#output "ssl_certificate" {
#  value = google_compute_managed_ssl_certificate.default.self_link
#}

output "domain_name" {
  value = "${google_compute_global_address.default.address}.nip.io"
}

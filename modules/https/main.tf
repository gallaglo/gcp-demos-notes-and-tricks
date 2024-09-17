resource "google_compute_global_address" "default" {
  name         = "${var.name}-ip"
  address_type = "EXTERNAL"
}

#resource "google_compute_managed_ssl_certificate" "default" {
#  name = "${var.name}-certificate"
#
#  managed {
#    domains = ["${google_compute_global_address.default.address}.nip.io"]
#  }
#}

resource "google_certificate_manager_certificate" "certificate" {
  name        = "${vat.name}-certificate"
  description = "${var.name} certificate"
  scope       = "DEFAULT"
  managed {
    domains = [
      google_certificate_manager_dns_authorization.instance.domain,
    ]
    dns_authorizations = [
      google_certificate_manager_dns_authorization.instance.id,
    ]
  }
}

resource "google_certificate_manager_dns_authorization" "instance" {
  name        = "${var.name}-dns-auth"
  description = "${var.name} dnss"
  domain      = "${google_compute_global_address.default.address}.nip.io"
}

resource "google_certificate_manager_certificate_map" "certificate_map" {
  name        = "${var.name}-cert-map"
  description = "${var.name} certificate map"
}

resource "google_certificate_manager_certificate_map_entry" "default" {
  name         = "${var.name}-cert-map-entry"
  description  = "${var.name} certificate map entry"
  map          = google_certificate_manager_certificate_map.certificate_map.name
  certificates = [google_certificate_manager_certificate.certificate.id]
  matcher      = "PRIMARY"
}

resource "google_compute_global_address" "default" {
  name          = "${var.name}-ip"
  address_type  = "EXTERNAL"
}

resource "google_compute_managed_ssl_certificate" "default" {
  name = "${var.name}-certificate"

  managed {
    domains = ["${google_compute_global_address.default.address}.nip.io"]
  }
}


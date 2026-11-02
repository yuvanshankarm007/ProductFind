output "firestore_database_name" {
  description = "The resource name of the Firestore database"
  value       = google_firestore_database.default.name
}

output "firestore_location" {
  description = "Firestore geographic multi-region or regional location"
  value       = google_firestore_database.default.location_id
}

output "redis_host" {
  description = "The IP address of the Memorystore Redis instance"
  value       = google_redis_instance.price_cache.host
}

output "redis_port" {
  description = "The port of the Memorystore Redis instance"
  value       = google_redis_instance.price_cache.port
}

output "service_account_email" {
  description = "The email of the provisioned service account"
  value       = google_service_account.sentinel_backend.email
}

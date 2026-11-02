terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required Google Cloud APIs
resource "google_project_service" "firestore" {
  project                    = var.project_id
  service                    = "firestore.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

resource "google_project_service" "redis" {
  project                    = var.project_id
  service                    = "redis.googleapis.com"
  disable_dependent_services = false
  disable_on_destroy         = false
}

# 2. Google Cloud Firestore in Native Mode (Multi-Region nam5, PITR Enabled)
resource "google_firestore_database" "default" {
  project                           = var.project_id
  name                              = "(default)"
  location_id                       = var.firestore_location
  type                              = "FIRESTORE_NATIVE"
  concurrency_mode                  = "OPTIMISTIC"
  app_engine_integration_mode       = "DISABLED"
  point_in_time_recovery_enablement = "POINT_IN_TIME_RECOVERY_ENABLED"
  delete_protection_state           = "DELETE_PROTECTION_DISABLED"

  depends_on = [google_project_service.firestore]
}

# 3. Composite Index for Dispute Dossiers (Query by order_id and timestamp)
resource "google_firestore_index" "dispute_dossiers_idx" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "dispute_dossiers"

  fields {
    field_path = "paypal_order_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "timestamp"
    order      = "DESCENDING"
  }
}

# 4. Composite Index for Autonomous Merchant Skills (Query by domain and confidence)
resource "google_firestore_index" "merchants_skills_idx" {
  project    = var.project_id
  database   = google_firestore_database.default.name
  collection = "merchants_skills"

  fields {
    field_path = "merchant_domain"
    order      = "ASCENDING"
  }

  fields {
    field_path = "confidence"
    order      = "DESCENDING"
  }
}

# 5. Memorystore Redis / Valkey Cache for Low-Latency Real-Time Price Predictions
resource "google_redis_instance" "price_cache" {
  project        = var.project_id
  name           = "productfind-price-cache-${var.environment}"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  authorized_network = "default"

  redis_version = "REDIS_7_0"
  display_name  = "ProductFind 90-Day Trajectory Price Cache"

  depends_on = [google_project_service.redis]
}

# 6. Service Account with Least-Privilege Datastore Access
resource "google_service_account" "sentinel_backend" {
  project      = var.project_id
  account_id   = "productfind-sentinel-sa"
  display_name = "ProductFind Sentinel Backend Service Account"
}

resource "google_project_iam_member" "datastore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.sentinel_backend.email}"
}

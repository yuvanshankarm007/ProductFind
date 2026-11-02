variable "project_id" {
  description = "The Google Cloud Project ID where ProductFind resources will be deployed"
  type        = string
  default     = "productfind-sentinel-prod"
}

variable "region" {
  description = "The default GCP region for regional resources (e.g., Memorystore, Cloud Run)"
  type        = string
  default     = "us-central1"
}

variable "firestore_location" {
  description = "The location ID for Google Cloud Firestore (multi-region 'nam5' or regional 'us-central1')"
  type        = string
  default     = "nam5"
}

variable "environment" {
  description = "Deployment environment (development, staging, production)"
  type        = string
  default     = "production"
}

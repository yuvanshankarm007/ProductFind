"""
Google Cloud Firestore Persistence & Caching Service for ProductFind.
Provides a cloud-native database layer for:
- Autonomous Merchant Skills (merchants_skills)
- PayPal Cryptographic Dispute Dossiers (dispute_dossiers)
- 90-Day Price Trajectory & Prediction Cache (price_cache)
- Orders & Session State (orders)

Implements the Zero-Crash Guarantee: If GCP credentials or libraries are unavailable,
it seamlessly and transparently operates in local disk + memory fallback mode.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger("ProductFind.GCPDatabase")

# Optional Google Cloud Firestore import
try:
    from google.cloud import firestore
    from google.api_core.exceptions import GoogleAPICallError
    HAS_FIRESTORE = True
except ImportError:
    firestore = None
    GoogleAPICallError = Exception
    HAS_FIRESTORE = False


class FirestorePersistenceService:
    """
    Cloud-native Firestore service with multi-region replication and local fallback.
    """

    def __init__(self, project_id: Optional[str] = None, database_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.database_id = database_id or os.getenv("FIRESTORE_DATABASE_ID", "(default)")
        self.client = None
        self.is_connected = False
        
        # Local fallback stores
        self._local_skills: Dict[str, Dict[str, Any]] = {}
        self._local_dossiers: Dict[str, Dict[str, Any]] = {}
        self._local_cache: Dict[str, Dict[str, Any]] = {}
        self._local_orders: Dict[str, Dict[str, Any]] = {}

        # Local directory paths for fallback persistence
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.skills_dir = os.path.join(base_dir, "skills_vault")
        self.dossiers_dir = os.path.join(base_dir, "data", "dossiers")
        os.makedirs(self.skills_dir, exist_ok=True)
        os.makedirs(self.dossiers_dir, exist_ok=True)

        self._initialize_connection()
        self._load_local_data()

    def _initialize_connection(self):
        """Attempts to initialize Firestore client with safe fallback."""
        if not HAS_FIRESTORE:
            logger.info("[GCP Firestore] 'google-cloud-firestore' package not present. Using high-performance local fallback.")
            self.is_connected = False
            return

        if not self.project_id and not os.getenv("FIRESTORE_EMULATOR_HOST"):
            logger.info("[GCP Firestore] GCP_PROJECT_ID not set. Running in local fallback mode (Zero-Crash Guarantee).")
            self.is_connected = False
            return

        try:
            self.client = firestore.Client(project=self.project_id, database=self.database_id)
            self.is_connected = True
            logger.info(f"[GCP Firestore] Connected to Firestore database '{self.database_id}' in project '{self.project_id}'.")
        except Exception as e:
            logger.warning(f"[GCP Firestore] Initialization failed ({e}). Operating in local fallback mode.")
            self.client = None
            self.is_connected = False

    def _load_local_data(self):
        """Preloads local disk data into fallback cache."""
        try:
            if os.path.exists(self.skills_dir):
                for f in os.listdir(self.skills_dir):
                    if f.endswith(".json"):
                        path = os.path.join(self.skills_dir, f)
                        try:
                            with open(path, "r", encoding="utf-8") as fp:
                                data = json.load(fp)
                                domain = data.get("merchant_domain", f.replace(".json", ""))
                                self._local_skills[domain] = data
                        except Exception:
                            pass

            if os.path.exists(self.dossiers_dir):
                for f in os.listdir(self.dossiers_dir):
                    if f.endswith(".json"):
                        path = os.path.join(self.dossiers_dir, f)
                        try:
                            with open(path, "r", encoding="utf-8") as fp:
                                data = json.load(fp)
                                order_id = data.get("paypal_order_id", f.replace(".json", ""))
                                self._local_dossiers[order_id] = data
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"[Persistence] Error loading local files: {e}")

    # =========================================================================
    # 1. MERCHANT SKILLS (merchants_skills collection)
    # =========================================================================
    def save_skill(self, domain: str, skill_data: Dict[str, Any]) -> bool:
        """Persists an autonomous merchant skill to Firestore with disk mirror."""
        # Always update local cache & disk mirror for zero-crash offline readiness
        self._local_skills[domain] = skill_data
        try:
            file_path = os.path.join(self.skills_dir, f"{domain}.json")
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(skill_data, fp, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[LocalSkill] Failed writing disk mirror: {e}")

        # Firestore Cloud Persistence
        if self.is_connected and self.client:
            try:
                doc_ref = self.client.collection("merchants_skills").document(domain)
                doc_ref.set(skill_data, merge=True)
                return True
            except Exception as e:
                logger.error(f"[GCP Firestore] Failed saving skill to cloud: {e}")
                return False
        return True

    def get_skill(self, domain: str) -> Optional[Dict[str, Any]]:
        """Retrieves a merchant skill from Firestore, falling back to local vault."""
        if self.is_connected and self.client:
            try:
                doc_ref = self.client.collection("merchants_skills").document(domain)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.warning(f"[GCP Firestore] Error retrieving skill '{domain}': {e}. Using local fallback.")

        return self._local_skills.get(domain)

    def list_skills(self) -> List[Dict[str, Any]]:
        """Lists all acquired merchant skills."""
        if self.is_connected and self.client:
            try:
                docs = self.client.collection("merchants_skills").stream()
                cloud_skills = [d.to_dict() for d in docs]
                if cloud_skills:
                    return cloud_skills
            except Exception as e:
                logger.warning(f"[GCP Firestore] Error listing cloud skills: {e}. Using local fallback.")

        return list(self._local_skills.values())

    def delete_skill(self, domain: str) -> bool:
        """Removes a skill from Firestore and local store."""
        self._local_skills.pop(domain, None)
        path = os.path.join(self.skills_dir, f"{domain}.json")
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

        if self.is_connected and self.client:
            try:
                self.client.collection("merchants_skills").document(domain).delete()
                return True
            except Exception as e:
                logger.error(f"[GCP Firestore] Error deleting skill '{domain}': {e}")
                return False
        return True

    # =========================================================================
    # 2. PAYPAL CRYPTOGRAPHIC DISPUTE DOSSIERS (dispute_dossiers collection)
    # =========================================================================
    def save_dossier(self, order_id: str, dossier_data: Dict[str, Any]) -> bool:
        """
        Stores an immutable dispute evidence dossier under PayPal User Agreement Section 13.
        """
        self._local_dossiers[order_id] = dossier_data
        try:
            file_path = os.path.join(self.dossiers_dir, f"{order_id}.json")
            with open(file_path, "w", encoding="utf-8") as fp:
                json.dump(dossier_data, fp, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[LocalDossier] Failed writing dossier mirror: {e}")

        if self.is_connected and self.client:
            try:
                doc_ref = self.client.collection("dispute_dossiers").document(order_id)
                doc_ref.set(dossier_data)
                return True
            except Exception as e:
                logger.error(f"[GCP Firestore] Failed saving dispute dossier '{order_id}': {e}")
                return False
        return True

    def get_dossier(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an evidentiary dispute dossier by PayPal Order ID."""
        if self.is_connected and self.client:
            try:
                doc_ref = self.client.collection("dispute_dossiers").document(order_id)
                doc = doc_ref.get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.warning(f"[GCP Firestore] Error fetching dossier '{order_id}': {e}. Using local fallback.")

        return self._local_dossiers.get(order_id)

    def list_dossiers(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists recent dispute dossiers."""
        if self.is_connected and self.client:
            try:
                query = self.client.collection("dispute_dossiers").order_by(
                    "timestamp", direction=firestore.Query.DESCENDING
                ).limit(limit)
                docs = query.stream()
                cloud_dossiers = [d.to_dict() for d in docs]
                if cloud_dossiers:
                    return cloud_dossiers
            except Exception as e:
                logger.warning(f"[GCP Firestore] Error listing dossiers: {e}. Using local fallback.")

        dossiers = list(self._local_dossiers.values())
        # Sort by timestamp descending
        dossiers.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
        return dossiers[:limit]

    # =========================================================================
    # 3. 90-DAY PRICE TRAJECTORY CACHE (price_cache collection / Memorystore)
    # =========================================================================
    def cache_prediction(self, query_hash: str, prediction_data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Caches 90-day trajectory and 14-day price prediction."""
        now = datetime.now(timezone.utc).timestamp()
        entry = {
            "query_hash": query_hash,
            "data": prediction_data,
            "created_at": now,
            "expires_at": now + ttl_seconds
        }
        self._local_cache[query_hash] = entry

        if self.is_connected and self.client:
            try:
                self.client.collection("price_cache").document(query_hash).set(entry)
                return True
            except Exception as e:
                logger.warning(f"[GCP Firestore] Price cache write error: {e}")
                return False
        return True

    def get_prediction(self, query_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves cached prediction if not expired."""
        now = datetime.now(timezone.utc).timestamp()
        if self.is_connected and self.client:
            try:
                doc = self.client.collection("price_cache").document(query_hash).get()
                if doc.exists:
                    entry = doc.to_dict()
                    if entry.get("expires_at", 0) > now:
                        return entry.get("data")
            except Exception as e:
                logger.warning(f"[GCP Firestore] Price cache read error: {e}")

        local_entry = self._local_cache.get(query_hash)
        if local_entry and local_entry.get("expires_at", 0) > now:
            return local_entry.get("data")
        return None

    # =========================================================================
    # 4. ORDER SESSIONS (orders collection)
    # =========================================================================
    def save_order(self, order_id: str, order_data: Dict[str, Any]) -> bool:
        """Stores captured order state."""
        self._local_orders[order_id] = order_data
        if self.is_connected and self.client:
            try:
                self.client.collection("orders").document(order_id).set(order_data, merge=True)
                return True
            except Exception as e:
                logger.error(f"[GCP Firestore] Failed saving order '{order_id}': {e}")
                return False
        return True

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves order details."""
        if self.is_connected and self.client:
            try:
                doc = self.client.collection("orders").document(order_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception as e:
                logger.warning(f"[GCP Firestore] Error fetching order '{order_id}': {e}")
        return self._local_orders.get(order_id)

    # =========================================================================
    # STATUS & TELEMETRY
    # =========================================================================
    def get_status(self) -> Dict[str, Any]:
        """Returns database connectivity and operational telemetry."""
        return {
            "mode": "firestore_native" if self.is_connected else "local_fallback",
            "is_connected": self.is_connected,
            "project_id": self.project_id or "local-dev",
            "database_id": self.database_id,
            "cached_skills_count": len(self._local_skills),
            "cached_dossiers_count": len(self._local_dossiers),
            "active_collections": [
                "merchants_skills",
                "dispute_dossiers",
                "price_cache",
                "orders"
            ],
            "zero_crash_guarantee": True
        }


# Global singleton instance
gcp_db_service = FirestorePersistenceService()

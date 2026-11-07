"""
Temporal Price Volatility & Deal Lock (Snipe Engine).
Analyzes historical 30-day volatility indices, flags algorithmic flash dips,
and issues pre-authorized 1-click escrow deal snipe locks with SHA-256 receipts.
"""

import math
import uuid
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from .arbitrage_catalogue import generate_mock_price_history, PricePoint


class VolatilityAnalysis(BaseModel):
    listing_id: str
    product_title: str
    current_price: float
    mrp: float
    all_time_low: float
    all_time_high: float
    volatility_index: float  # standard deviation or normalized variance
    is_algorithmic_dip: bool
    dip_percentage: float
    predicted_trend: str     # "ACCELERATING_UP", "FLASH_DIP_ACTIVE", "STABLE"
    snipe_recommended: bool
    preauth_token: Optional[str] = None
    history: List[PricePoint] = []


class SnipeLockRequest(BaseModel):
    listing_id: str
    target_price: float
    preauth_payment_method: str = "ONE_CLICK_ESCROW"
    auto_execute_within_seconds: int = 300


class SnipeLockResponse(BaseModel):
    lock_id: str
    listing_id: str
    locked_price: float
    status: str  # "SECURED_LOCKED", "PENDING_EXECUTION"
    expires_at: str
    receipt_hash: str
    created_at: Optional[str] = None


class TemporalVolatilityEngine:
    """
    Temporal Price Volatility & Snipe Alert Engine.
    Detects dynamic pricing trends, algorithmic flash dips, and manages pre-authorized 1-click snipe locks.
    """
    
    def __init__(self, dip_alert_threshold: float = 0.08):
        # Cache for active snipe locks: lock_id -> data
        self.active_locks: Dict[str, Dict[str, Any]] = {}
        self.dip_alert_threshold = dip_alert_threshold
        
    def analyze_item_volatility(self, item: Dict[str, Any]) -> VolatilityAnalysis:
        listing_id = item.get("id") or item.get("listing_id", "item-001")
        current_price = float(item.get("current_price") or item.get("base_price", 1000.0))
        mrp = float(item.get("original_mrp") or (current_price * 1.25))
        retailer = item.get("retailer") or item.get("merchant", "Amazon")
        
        # Generate or fetch 30-day history
        history = generate_mock_price_history(listing_id, current_price, retailer)
        prices = [p.price for p in history]
        
        atl = min(prices)
        ath = max(prices)
        mean_price = sum(prices) / max(1, len(prices))
        
        # Calculate standard deviation
        variance = sum((p - mean_price) ** 2 for p in prices) / max(1, len(prices))
        std_dev = math.sqrt(variance)
        normalized_volatility = round(min(1.0, std_dev / (mean_price if mean_price > 0 else 1.0)), 3)
        
        # Check if current price is an algorithmic flash dip
        # Dip is considered active if current price is at or near ATL or >8% below 30-day average
        dip_percentage = round(((mean_price - current_price) / mean_price) * 100.0, 1) if mean_price > 0 else 0.0
        is_algo_dip = (dip_percentage >= (self.dip_alert_threshold * 100.0)) or (current_price <= (atl * 1.02))
        
        # Predict trend
        if is_algo_dip:
            trend = "FLASH_DIP_ACTIVE"
            snipe_recommended = True
        elif current_price > (mean_price * 1.05):
            trend = "ACCELERATING_UP"
            snipe_recommended = False
        else:
            trend = "STABLE"
            snipe_recommended = False

        preauth_token = f"SNIPE-AUTH-{uuid.uuid4().hex[:12].upper()}" if snipe_recommended else None

        return VolatilityAnalysis(
            listing_id=listing_id,
            product_title=item.get("title") or item.get("product_title", f"Listing {listing_id}"),
            current_price=round(current_price, 2),
            mrp=round(mrp, 2),
            all_time_low=round(atl, 2),
            all_time_high=round(ath, 2),
            volatility_index=normalized_volatility,
            is_algorithmic_dip=is_algo_dip,
            dip_percentage=max(0.0, dip_percentage),
            predicted_trend=trend,
            snipe_recommended=snipe_recommended,
            preauth_token=preauth_token,
            history=history
        )

    def lock_snipe_deal(self, listing_id: str, target_price: float, auto_execute_seconds: int = 300) -> SnipeLockResponse:
        """
        Executes a 1-click pre-authorized deal lock-in, freezing the rate with an escrow receipt hash.
        """
        lock_id = f"LOCK-{uuid.uuid4().hex[:10].upper()}"
        expires_at = (datetime.now() + timedelta(seconds=auto_execute_seconds)).strftime("%Y-%m-%d %H:%M:%S")
        
        # Generate receipt hash
        raw_sig = f"{lock_id}:{listing_id}:{target_price}:{expires_at}:SECURE_ESCROW"
        receipt_hash = hashlib.sha256(raw_sig.encode()).hexdigest()
        
        lock_data = {
            "lock_id": lock_id,
            "listing_id": listing_id,
            "locked_price": target_price,
            "status": "SECURED_LOCKED",
            "expires_at": expires_at,
            "receipt_hash": receipt_hash,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.active_locks[lock_id] = lock_data
        
        return SnipeLockResponse(**lock_data)

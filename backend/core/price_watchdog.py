"""
Price Drop Watchdog & Automated Notification Dispatcher for ProductFind Sentinel.
Tracks user target price thresholds across retailers, evaluates flash dips and price projections,
and simulates/dispatches real-time alerts via Email, Telegram, Webhooks, or Browser push.
"""

import json
import os
import time
import uuid
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PriceAlertSubscription(BaseModel):
    id: str = Field(default_factory=lambda: f"alert-{uuid.uuid4().hex[:8]}")
    product_title: str
    target_price: float
    current_price: float
    currency: str = "INR"
    user_contact: str = "user@example.com"
    channel: str = "email"  # 'email', 'telegram', 'webhook', 'browser'
    status: str = "ACTIVE"  # 'ACTIVE', 'TRIGGERED', 'EXPIRED'
    created_at: float = Field(default_factory=time.time)
    triggered_at: Optional[float] = None
    last_scouted_price: Optional[float] = None
    notification_log: Optional[str] = None


class PriceWatchdogService:
    def __init__(self, storage_path: Optional[str] = None):
        if not storage_path:
            storage_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "data",
                "price_alerts.json"
            )
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._alerts: Dict[str, PriceAlertSubscription] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        alert = PriceAlertSubscription(**item)
                        self._alerts[alert.id] = alert
            except Exception:
                self._alerts = {}
        else:
            # Seed default demo alerts
            demo_alert_1 = PriceAlertSubscription(
                id="alert-demo-xm5",
                product_title="Sony WH-1000XM5",
                target_price=24000.0,
                current_price=26990.0,
                currency="INR",
                user_contact="shopper@sentinel.ai",
                channel="email",
                status="ACTIVE"
            )
            demo_alert_2 = PriceAlertSubscription(
                id="alert-demo-m3",
                product_title="Apple MacBook Pro 16 M3 Max",
                target_price=3199.0,
                current_price=3499.0,
                currency="USD",
                user_contact="@deal_sniper_bot",
                channel="telegram",
                status="ACTIVE"
            )
            self._alerts[demo_alert_1.id] = demo_alert_1
            self._alerts[demo_alert_2.id] = demo_alert_2
            self._save()

    def _save(self):
        try:
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump([a.model_dump() for a in self._alerts.values()], f, indent=2)
        except Exception:
            pass

    def subscribe(
        self,
        product_title: str,
        target_price: float,
        current_price: float,
        currency: str = "INR",
        user_contact: str = "user@example.com",
        channel: str = "email"
    ) -> PriceAlertSubscription:
        alert = PriceAlertSubscription(
            product_title=product_title,
            target_price=target_price,
            current_price=current_price,
            currency=currency,
            user_contact=user_contact,
            channel=channel,
            status="ACTIVE"
        )
        self._alerts[alert.id] = alert
        self._save()
        return alert

    def list_alerts(self, user_contact: Optional[str] = None) -> List[PriceAlertSubscription]:
        if user_contact:
            return [a for a in self._alerts.values() if a.user_contact.lower() == user_contact.lower()]
        return list(self._alerts.values())

    def delete_alert(self, alert_id: str) -> bool:
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            self._save()
            return True
        return False

    def check_and_evaluate_price(self, product_title: str, new_price: float, merchant: str = "Amazon") -> List[PriceAlertSubscription]:
        triggered = []
        p_title_low = product_title.lower()
        for alert in self._alerts.values():
            if alert.status == "ACTIVE" and (alert.product_title.lower() in p_title_low or p_title_low in alert.product_title.lower()):
                alert.last_scouted_price = new_price
                if new_price <= alert.target_price:
                    alert.status = "TRIGGERED"
                    alert.triggered_at = time.time()
                    diff = round(alert.current_price - new_price, 2)
                    alert.notification_log = (
                        f"🎯 PRICE DROP ALERT TRIGGERED: '{alert.product_title}' dropped to {alert.currency} {new_price:,.2f} "
                        f"on {merchant} (Save {alert.currency} {diff:,.2f} vs initial price). Dispatched to {alert.channel.upper()}: {alert.user_contact}"
                    )
                    triggered.append(alert)
        if triggered:
            self._save()
        return triggered

    def simulate_price_drop(self, alert_id: str, simulated_price: Optional[float] = None) -> Optional[PriceAlertSubscription]:
        alert = self._alerts.get(alert_id)
        if not alert:
            return None
        target = simulated_price if simulated_price is not None else round(alert.target_price * 0.96, 2)
        alert.last_scouted_price = target
        alert.status = "TRIGGERED"
        alert.triggered_at = time.time()
        diff = round(alert.current_price - target, 2)
        alert.notification_log = (
            f"🎯 [SIMULATED WATCHDOG DISPATCH] '{alert.product_title}' hit flash floor at {alert.currency} {target:,.2f} "
            f"(Target: {alert.currency} {alert.target_price:,.2f} | Net Drop: {alert.currency} {diff:,.2f}). "
            f"Alert dispatched to {alert.channel.upper()} ({alert.user_contact})."
        )
        self._save()
        return alert


watchdog_service = PriceWatchdogService()

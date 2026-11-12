"""
Price Drop Watchdog & Automated Notification Dispatcher for ProductFind Sentinel.
Tracks user target price thresholds across retailers, evaluates flash dips and price projections,
and simulates/dispatches real-time alerts via Email, Telegram, Webhooks, or Browser push.
"""

import json
import logging
import os
import time
import uuid
from typing import Dict, List, Optional, Any, Callable, Awaitable
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)


class PriceAlertSubscription(BaseModel):
    id: str = Field(default_factory=lambda: f"alert-{uuid.uuid4().hex[:8]}")
    product_title: str
    target_price: float
    current_price: float
    currency: str = "INR"
    user_contact: str = "user@example.com"
    channel: str = "email"  # 'email', 'telegram', 'webhook', 'discord', 'slack', 'browser'
    webhook_url: Optional[str] = None
    webhook_status: Optional[str] = None
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
        channel: str = "email",
        webhook_url: Optional[str] = None,
    ) -> PriceAlertSubscription:
        resolved_webhook = webhook_url
        if not resolved_webhook and user_contact and user_contact.startswith(("http://", "https://")):
            resolved_webhook = user_contact
        alert = PriceAlertSubscription(
            product_title=product_title,
            target_price=target_price,
            current_price=current_price,
            currency=currency,
            user_contact=user_contact,
            channel=channel,
            webhook_url=resolved_webhook,
            status="ACTIVE"
        )
        self._alerts[alert.id] = alert
        self._save()
        return alert

    async def dispatch_webhook_async(
        self, alert: PriceAlertSubscription, merchant: str = "Amazon"
    ) -> bool:
        """Dispatch a real Discord/Slack/HTTP JSON webhook notification when a target price triggers."""
        target_url = alert.webhook_url or (
            alert.user_contact if alert.user_contact.startswith(("http://", "https://")) else None
        )
        if not target_url:
            return False

        msg = (
            alert.notification_log
            or f"🎯 ProductFind Sentinel Alert: '{alert.product_title}' reached {alert.currency} {alert.last_scouted_price or alert.target_price:,.2f} on {merchant}"
        )
        payload = {
            "event": "sentinel_price_drop",
            "alert_id": alert.id,
            "product_title": alert.product_title,
            "target_price": alert.target_price,
            "triggered_price": alert.last_scouted_price,
            "currency": alert.currency,
            "merchant": merchant,
            # Discord + Slack standard keys
            "content": msg,
            "text": msg,
        }
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(3.0)) as client:
                resp = await client.post(target_url, json=payload)
            if 200 <= resp.status_code < 300:
                alert.webhook_status = f"DISPATCHED_{resp.status_code}"
                self._save()
                return True
            alert.webhook_status = f"HTTP_{resp.status_code}"
        except Exception as exc:
            logger.debug("Webhook dispatch failed for %s: %s", alert.id, exc)
            alert.webhook_status = "DISPATCH_ERROR"
        self._save()
        return False

    async def evaluate_all_active_alerts(
        self,
        price_lookup_fn: Optional[Callable[[str, str], Awaitable[Optional[Dict[str, Any]]]]] = None,
    ) -> List[PriceAlertSubscription]:
        """Sweep ACTIVE watchlist items and dispatch webhook notifications when threshold is met."""
        active = [a for a in self._alerts.values() if a.status == "ACTIVE"]
        if not active or price_lookup_fn is None:
            return []

        triggered: List[PriceAlertSubscription] = []
        for alert in active:
            try:
                quote = await price_lookup_fn(alert.product_title, alert.currency)
                if not quote or "price" not in quote:
                    continue
                price_val = float(quote["price"])
                merchant = str(quote.get("merchant") or "Scouted Retailer")
                hits = self.check_and_evaluate_price(
                    alert.product_title,
                    price_val,
                    merchant=merchant,
                    currency=str(quote.get("currency") or alert.currency),
                )
                for hit in hits:
                    triggered.append(hit)
                    await self.dispatch_webhook_async(hit, merchant=merchant)
            except Exception as exc:
                logger.debug("Watchdog background sweep error for %s: %s", alert.id, exc)
        return triggered

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

    def check_and_evaluate_price(
        self,
        product_title: str,
        new_price: float,
        merchant: str = "Amazon",
        currency: Optional[str] = None,
    ) -> List[PriceAlertSubscription]:
        triggered = []
        p_title_low = product_title.lower()
        for alert in self._alerts.values():
            if currency and alert.currency.upper() != currency.upper():
                continue
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

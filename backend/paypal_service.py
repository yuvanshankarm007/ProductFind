"""
PayPal Sandbox Service and Protection Engine.
Integrates PayPal Orders v2 API, multi-currency conversion, Pay in 4 calculation,
and Cross-Border Buyer Protection risk analysis.
"""

import os
import base64
import httpx
from typing import Dict, Any, Optional

class PayPalService:
    def __init__(self):
        self.client_id = os.getenv("PAYPAL_CLIENT_ID", "sb-sandbox-client-id-demo")
        self.client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "sb-sandbox-secret-demo")
        self.base_url = "https://api-m.sandbox.paypal.com"
        self._access_token: Optional[str] = None

    async def get_access_token(self) -> str:
        """Fetch OAuth2 token from PayPal Sandbox."""
        if self._access_token:
            return self._access_token

        # If dummy demo keys, return synthetic token
        if "demo" in self.client_id:
            self._access_token = "A21AA_DEMO_SANDBOX_ACCESS_TOKEN"
            return self._access_token

        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        async with httpx.AsyncClient() as client:
            try:
                res = await client.post(
                    f"{self.base_url}/v1/oauth2/token",
                    headers=headers,
                    data={"grant_type": "client_credentials"},
                    timeout=8.0
                )
                if res.status_code == 200:
                    token = res.json().get("access_token")
                    self._access_token = token
                    return token
            except Exception:
                pass
        return "A21AA_DEMO_SANDBOX_ACCESS_TOKEN"

    async def create_order(self, amount: float, item_name: str, currency: str = "USD") -> Dict[str, Any]:
        """Create a PayPal v2 order with multi-currency support."""
        token = await self.get_access_token()
        currency_code = currency.upper()

        # If simulated demo mode
        if "DEMO" in token:
            order_id = f"ORDER-PP-{int(amount*100)}-{currency_code}"
            return {
                "id": order_id,
                "status": "CREATED",
                "links": [
                    {"rel": "approve", "href": f"https://www.sandbox.paypal.com/checkoutnow?token={order_id}"}
                ],
                "details": {
                    "item": item_name,
                    "amount": round(amount, 2),
                    "currency": currency_code,
                    "pay_in_4_biweekly": round(amount / 4.0, 2)
                }
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "description": item_name,
                    "amount": {
                        "currency_code": currency_code,
                        "value": f"{amount:.2f}"
                    }
                }
            ],
            "application_context": {
                "brand_name": "ProductFind Sentinel AI",
                "landing_page": "NO_PREFERENCE",
                "user_action": "PAY_NOW",
                "return_url": "http://localhost:8000/api/paypal/success",
                "cancel_url": "http://localhost:8000/api/paypal/cancel"
            }
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            return res.json()

    async def capture_order(self, order_id: str) -> Dict[str, Any]:
        """Capture the payment after buyer approval."""
        token = await self.get_access_token()
        if "DEMO" in token:
            return {
                "id": order_id,
                "status": "COMPLETED",
                "capture_id": f"CAP-{order_id}",
                "payer": {"email_address": "buyer-sandbox@paypal.com", "payer_id": "PP-BUYER-987"}
            }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers=headers,
                timeout=10.0
            )
            return res.json()

    def evaluate_protection_synergy(
        self,
        base_price: float,
        adp_price: float,
        merchant_trust_score: int,
        return_window_days: int,
        restocking_fee_pct: float,
        is_third_party: bool,
        has_adp: bool,
        is_cross_border: bool = False,
        currency: str = "USD"
    ) -> Dict[str, Any]:
        """
        Dynamically calculates why PayPal Buyer Protection & Pay in 4 are recommended.
        Directly links domestic & cross-border merchant risks to PayPal protections.
        """
        total_bundle = round(base_price + adp_price, 2)
        pay_in_4_rate = round(total_bundle / 4.0, 2)

        mitigated_risks = []
        recommend = True

        if is_cross_border:
            mitigated_risks.append(
                "International Cross-Border Merchant: PayPal Buyer Protection shields your funds against lost overseas cargo, "
                "customs clearance impounds, and provides dispute arbitration without foreign currency conversion loss."
            )

        if merchant_trust_score < 75:
            mitigated_risks.append(
                f"Merchant Trust is Low/Fair ({merchant_trust_score}/100). PayPal Buyer Protection guarantees 180-day refund mediation if order is disputed."
            )
        
        if is_third_party:
            mitigated_risks.append(
                "Marketplace 3rd-party seller. PayPal shields transactions against 'Item Significantly Not As Described' or unauthorized seller debiting."
            )
            
        if restocking_fee_pct > 0:
            mitigated_risks.append(
                f"Merchant charges a punitive {restocking_fee_pct}% restocking fee. PayPal Resolution Center mediates damaged/defective merchandise without merchant restocking deductions."
            )

        if return_window_days <= 14:
            mitigated_risks.append(
                f"Restrictive {return_window_days}-day return window. PayPal provides an extended 180-day window to file claims for defective hardware."
            )

        if not mitigated_risks:
            mitigated_risks.append(
                "Verified authorized merchant: PayPal Pay in 4 provides 0% APR installment financing and secure one-touch checkout."
            )

        tier = "Full Restocking & Defect Shield"
        if is_cross_border:
            tier = "Cross-Border International Shield"
        elif restocking_fee_pct > 0:
            tier = "Restocking & Return Penalty Shield"

        headline = "PayPal 180-Day Buyer Protection Active"
        if is_cross_border:
            headline = "PayPal Cross-Border Protection Shield Activated"
        elif merchant_trust_score < 85:
            headline = "PayPal Buyer Protection Shield Activated"
        else:
            headline = "PayPal Pay Later Financing Recommended"

        return {
            "recommend_paypal": recommend,
            "headline": headline,
            "explanation": " ".join(mitigated_risks),
            "buyer_protection_tier": tier,
            "mitigated_risks": mitigated_risks,
            "pay_later_eligible": total_bundle >= 30.0 and total_bundle <= 2500.0,
            "pay_in_4_biweekly": pay_in_4_rate,
            "total_financed_with_adp": total_bundle,
            "currency": currency
        }

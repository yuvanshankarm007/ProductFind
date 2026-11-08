"""
"My Wallet" Card & Bank Offer Stacker for ProductFind Sentinel.
Allows users to specify credit cards, debit cards, and payment channels they own,
and dynamically stack real-time merchant card offers, instant bank discounts, and 5% cashback.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CardOffer(BaseModel):
    card_id: str
    card_name: str
    issuer: str
    discount_pct: float = 0.0
    discount_flat: float = 0.0
    max_cap: float = 999999.0
    min_order: float = 0.0
    applicable_merchants: List[str] = Field(default_factory=list)
    badge: str
    description: str


SUPPORTED_WALLET_CARDS: Dict[str, CardOffer] = {
    "hdfc_regalia": CardOffer(
        card_id="hdfc_regalia",
        card_name="HDFC Bank Regalia / Millennia",
        issuer="HDFC Bank",
        discount_pct=10.0,
        max_cap=1500.0,
        min_order=5000.0,
        applicable_merchants=["Amazon", "Flipkart", "Croma", "Reliance Digital", "OEM Direct"],
        badge="10% Instant HDFC Discount",
        description="10% Instant discount up to ₹1,500 on electronics & tech orders above ₹5,000."
    ),
    "icici_amazon_pay": CardOffer(
        card_id="icici_amazon_pay",
        card_name="Amazon Pay ICICI Card",
        issuer="ICICI Bank",
        discount_pct=5.0,
        max_cap=10000.0,
        min_order=0.0,
        applicable_merchants=["Amazon", "Amazon.in", "Amazon Global"],
        badge="5% Unlimited Amazon Cashback",
        description="5% Unlimited statement cashback on all Amazon prime merchant transactions."
    ),
    "axis_flipkart": CardOffer(
        card_id="axis_flipkart",
        card_name="Flipkart Axis Bank Credit Card",
        issuer="Axis Bank",
        discount_pct=5.0,
        max_cap=10000.0,
        min_order=0.0,
        applicable_merchants=["Flipkart", "flipkart.com"],
        badge="5% Unlimited Flipkart Cashback",
        description="5% Unlimited cashback credited directly on every Flipkart order."
    ),
    "sbi_cashback": CardOffer(
        card_id="sbi_cashback",
        card_name="SBI Cashback Card",
        issuer="State Bank of India",
        discount_pct=5.0,
        max_cap=5000.0,
        min_order=1000.0,
        applicable_merchants=["Amazon", "Flipkart", "Croma", "Reliance Digital", "OEM Direct", "TataCliq", "Vijay Sales"],
        badge="5% Universal Online Cashback",
        description="5% Universal cashback across all verified Indian eCommerce checkouts."
    ),
    "paypal_pay_later": CardOffer(
        card_id="paypal_pay_later",
        card_name="PayPal Pay in 4 & Buyer Escrow",
        issuer="PayPal",
        discount_pct=0.0,
        discount_flat=500.0,
        min_order=3000.0,
        applicable_merchants=["OEM Direct", "Newegg", "B&H Photo", "Best Buy", "eBay", "Target", "Walmart"],
        badge="PayPal 180-Day Shield + 0% APR Pay in 4",
        description="Split into 4 interest-free bi-weekly installments with full Section 13 protection."
    ),
    "amex_platinum": CardOffer(
        card_id="amex_platinum",
        card_name="American Express Platinum / SmartEarn",
        issuer="American Express",
        discount_pct=0.0,
        discount_flat=2500.0,
        min_order=35000.0,
        applicable_merchants=["OEM Direct", "Apple Store", "Dell", "B&H Photo", "Amazon"],
        badge="₹2,500 Amex Instant Statement Credit",
        description="₹2,500 Instant statement credit on premium tech workstations above ₹35,000."
    )
}


class WalletDiscountCalculation(BaseModel):
    original_price: float
    effective_price: float
    net_savings: float
    best_card_id: Optional[str] = None
    best_card_name: Optional[str] = None
    applied_badge: Optional[str] = None
    pay_in_4_biweekly: Optional[float] = None
    savings_breakdown: str

    @property
    def total_discount(self) -> float:
        return self.net_savings


class WalletStackerService:
    def __init__(self):
        self.cards = SUPPORTED_WALLET_CARDS

    def get_supported_cards(self) -> List[Dict[str, Any]]:
        return [c.model_dump() for c in self.cards.values()]

    list_supported_cards = get_supported_cards

    def calculate_best_wallet_discount(
        self,
        base_price: float = 0.0,
        merchant: str = "",
        user_card_ids: Optional[List[str]] = None,
        currency: str = "INR",
        wallet_card_ids: Optional[List[str]] = None,
        retailer: Optional[str] = None,
        order_amount: Optional[float] = None,
        items: Optional[List[Dict[str, Any]]] = None
    ) -> WalletDiscountCalculation:
        # Flexible kwargs mapping
        effective_base_price = order_amount if order_amount is not None else base_price
        effective_merchant = retailer if retailer is not None else merchant
        effective_card_ids = wallet_card_ids if wallet_card_ids is not None else user_card_ids

        if not effective_card_ids or len(effective_card_ids) == 0:
            # Default to all standard supported cards for public arbitration
            active_cards = list(self.cards.values())
        else:
            active_cards = [self.cards[cid] for cid in effective_card_ids if cid in self.cards]

        merchant_clean = (effective_merchant or "").lower()
        best_savings = 0.0
        best_card: Optional[CardOffer] = None

        for card in active_cards:
            if effective_base_price < card.min_order:
                continue

            # Check merchant match
            matches_merchant = any(m.lower() in merchant_clean or merchant_clean in m.lower() for m in card.applicable_merchants)
            if not matches_merchant and "universal" not in card.badge.lower():
                continue

            savings = 0.0
            if card.discount_flat > 0:
                savings = card.discount_flat
            elif card.discount_pct > 0:
                savings = (effective_base_price * card.discount_pct) / 100.0
                if card.max_cap > 0:
                    savings = min(savings, card.max_cap)

            if savings > best_savings:
                best_savings = savings
                best_card = card

        effective_price = max(0.0, round(effective_base_price - best_savings, 2))
        pay_in_4 = round(effective_price / 4.0, 2)

        if best_card and best_savings > 0:
            badge = f"💳 {best_card.badge} (-{currency} {best_savings:,.2f})"
            breakdown = f"Applied {best_card.card_name}: Saved {currency} {best_savings:,.2f} ({best_card.description})"
            b_id = best_card.card_id
            b_name = best_card.card_name
        else:
            badge = None
            breakdown = "Standard retail pricing (no matching wallet card bonus qualified)."
            b_id = None
            b_name = None

        return WalletDiscountCalculation(
            original_price=base_price,
            effective_price=effective_price,
            net_savings=best_savings,
            best_card_id=b_id,
            best_card_name=b_name,
            applied_badge=badge,
            pay_in_4_biweekly=pay_in_4,
            savings_breakdown=breakdown
        )


wallet_service = WalletStackerService()
wallet_stacker_service = wallet_service

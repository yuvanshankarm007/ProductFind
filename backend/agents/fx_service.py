"""
FX and Cross-Border Duties Engine.
Fetches/computes live FX rates with offline fallback, calculates import customs duties,
and compares standard credit card foreign transaction fees (3.5%) vs PayPal's native currency conversion.
"""

from typing import Dict, Tuple, Optional
import httpx
import time
from ..core.state import CrossBorderFxDutyAnalysis

# Standard baseline exchange rates anchored to USD (1 USD = X Currency)
BASE_RATES_USD: Dict[str, float] = {
    "USD": 1.0,
    "INR": 86.80,
    "EUR": 0.925,
    "GBP": 0.785,
    "CAD": 1.390,
    "JPY": 152.40,
    "AUD": 1.545
}

CURRENCY_SYMBOLS: Dict[str, str] = {
    "USD": "$",
    "INR": "₹",
    "EUR": "€",
    "GBP": "£",
    "CAD": "CA$",
    "JPY": "¥",
    "AUD": "A$"
}

# Standard electronics import duty & tax percentages based on (origin, destination)
IMPORT_DUTY_MATRIX: Dict[Tuple[str, str], float] = {
    ("US", "IN"): 18.5,  # Basic Customs Duty (BCD) + Social Welfare Surcharge (SWS) in India
    ("US", "GB"): 20.0,  # Import VAT in UK (Post-Brexit standard rate)
    ("US", "DE"): 19.0,  # Import VAT (Einfuhrumsatzsteuer) in Germany/EU
    ("US", "CA"): 13.0,  # Harmonized Sales Tax (HST/GST) import into Canada
    ("US", "AU"): 10.0,  # Goods and Services Tax (GST) on low-value imports into Australia
    ("US", "JP"): 10.0,  # Japanese Consumption Tax on imports
    ("IN", "US"): 3.5,   # Section 301 / entry tariff into US
    ("IN", "GB"): 20.0,
    ("IN", "DE"): 19.0,
    ("GB", "US"): 2.5,
    ("GB", "IN"): 18.5,
    ("GB", "DE"): 19.0,  # Post-Brexit EU import VAT
    ("DE", "US"): 2.5,
    ("DE", "IN"): 18.5,
    ("DE", "GB"): 20.0,  # Post-Brexit UK import VAT
    ("CA", "US"): 0.0,   # USMCA duty-free
    ("CA", "IN"): 18.5,
    ("AU", "US"): 0.0,   # AUSFTA duty-free
    ("AU", "IN"): 18.5,
    ("JP", "US"): 2.5,
    ("JP", "IN"): 18.5,
    ("HK", "US"): 5.0,
    ("HK", "IN"): 22.0,
    ("HK", "GB"): 20.0,
    ("HK", "DE"): 19.0,
    ("HK", "CA"): 13.0,
    ("HK", "AU"): 10.0,
    ("HK", "JP"): 10.0,
}

class FXService:
    def __init__(self):
        self._rates = dict(BASE_RATES_USD)
        self._last_fetched = 0.0

    async def refresh_live_rates(self):
        """Asynchronously updates FX rates from public exchange API with resilient fallback."""
        now = time.time()
        # Rate-limit refresh to once every 10 minutes
        if now - self._last_fetched < 600:
            return

        try:
            async with httpx.AsyncClient(timeout=2.5) as client:
                res = await client.get("https://open.er-api.com/v6/latest/USD")
                if res.status_code == 200:
                    data = res.json()
                    rates = data.get("rates", {})
                    for curr in BASE_RATES_USD.keys():
                        if curr in rates and rates[curr] > 0:
                            self._rates[curr] = round(float(rates[curr]), 4)
                    self._last_fetched = now
        except Exception:
            pass  # Retain calibrated BASE_RATES_USD

    async def get_fx_rate(self, from_curr: str, to_curr: str) -> float:
        """Returns the conversion multiplier from from_curr to to_curr."""
        await self.refresh_live_rates()
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        if from_curr == to_curr:
            return 1.0

        usd_to_from = self._rates.get(from_curr, 1.0)
        usd_to_target = self._rates.get(to_curr, 1.0)
        rate = usd_to_target / usd_to_from
        return round(rate, 4)

    def convert_amount(self, amount: float, from_curr: str, to_curr: str) -> float:
        """Synchronously converts amount using cached rates."""
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()
        if from_curr == to_curr:
            return round(amount, 2)
        usd_to_from = self._rates.get(from_curr, 1.0)
        usd_to_target = self._rates.get(to_curr, 1.0)
        rate = usd_to_target / usd_to_from
        return round(amount * rate, 2)

    def format_price(self, amount: float, currency: str) -> str:
        symbol = CURRENCY_SYMBOLS.get(currency.upper(), "$")
        if currency.upper() in ["INR", "JPY"]:
            return f"{symbol}{amount:,.0f}" if currency.upper() == "JPY" else f"{symbol}{amount:,.2f}"
        return f"{symbol}{amount:,.2f}"

    def calculate_cross_border_analysis(
        self,
        base_price: float,
        merchant_country: str,
        destination_country: str,
        original_currency: str,
        target_currency: str,
        shipping_cost: float = 0.0
    ) -> CrossBorderFxDutyAnalysis:
        """
        Calculates cross-border duty impact based on WTO/CIF valuation and statutory de minimis thresholds.
        Compares standard credit card foreign bank surcharge (3.5%) versus PayPal native retail conversion.
        """
        merchant_country = merchant_country.upper()
        dest_country = destination_country.upper()
        orig_curr = original_currency.upper()
        target_curr = target_currency.upper()

        is_cross_border = (merchant_country != dest_country)
        fx_rate = self.convert_amount(1.0, orig_curr, target_curr)
        converted_base = round(base_price * fx_rate, 2)
        converted_shipping = round(shipping_cost * fx_rate, 2)
        cif_target = round(converted_base + converted_shipping, 2)

        if not is_cross_border:
            # Domestic purchase
            return CrossBorderFxDutyAnalysis(
                is_cross_border=False,
                merchant_country=merchant_country,
                destination_country=dest_country,
                original_currency=orig_curr,
                target_currency=target_curr,
                fx_rate=fx_rate,
                converted_base_price=converted_base,
                estimated_import_duty_pct=0.0,
                estimated_import_duty_amount=0.0,
                card_foreign_fee_pct=0.0,
                card_foreign_fee_amount=0.0,
                paypal_conversion_rate=fx_rate,
                paypal_conversion_total=converted_base,
                card_total_estimated=converted_base,
                savings_with_paypal=0.0,
                recommendation=f"Domestic order within {dest_country}. Zero import duties and zero foreign transaction fees."
            )

        # Cross-border purchase: Check statutory De Minimis thresholds
        # CIF in USD for international trade threshold comparison
        cif_usd = self.convert_amount(base_price + shipping_cost, orig_curr, "USD")
        duty_pct = IMPORT_DUTY_MATRIX.get((merchant_country, dest_country), 15.0)
        de_minimis_note = ""

        # US Section 321 De Minimis ($800)
        if dest_country == "US" and cif_usd <= 800.0:
            duty_pct = 0.0
            de_minimis_note = " (Section 321 De Minimis: Duty-Free under $800)"
        # AU Low Value De Minimis (AUD 1,000 threshold for customs tariff; 10% GST applies)
        elif dest_country == "AU":
            cif_aud = self.convert_amount(base_price + shipping_cost, orig_curr, "AUD")
            duty_pct = 10.0 if cif_aud <= 1000.0 else 15.0
            if cif_aud <= 1000.0:
                de_minimis_note = " (Low-Value Threshold: 10% GST, 0% Customs Tariff)"
        # UK £135 De Minimis (0% customs tariff, 20% Import VAT)
        elif dest_country == "GB":
            cif_gbp = self.convert_amount(base_price + shipping_cost, orig_curr, "GBP")
            duty_pct = 20.0 if cif_gbp <= 135.0 else 22.5
            if cif_gbp <= 135.0:
                de_minimis_note = " (Under £135: 0% Tariff + 20% Standard Import VAT)"
        # EU €150 De Minimis (0% customs tariff, 19% Import VAT)
        elif dest_country == "DE":
            cif_eur = self.convert_amount(base_price + shipping_cost, orig_curr, "EUR")
            duty_pct = 19.0 if cif_eur <= 150.0 else 21.5
            if cif_eur <= 150.0:
                de_minimis_note = " (Under €150: 0% Tariff + 19% Import VAT / EUSt)"

        duty_amount = round(cif_target * (duty_pct / 100.0), 2)

        # Credit card charges 3.5% foreign transaction fee on foreign spend
        card_fee_pct = 3.5
        card_fee_amount = round(converted_base * (card_fee_pct / 100.0), 2)
        card_total = round(converted_base + duty_amount + card_fee_amount, 2)

        # PayPal Native Currency Conversion:
        paypal_markup_pct = 3.0
        paypal_rate = round(fx_rate * (1.0 + paypal_markup_pct / 100.0), 4)
        paypal_total = round((base_price * paypal_rate) + duty_amount, 2)

        savings = round(card_total - paypal_total, 2)
        if savings < 0:
            savings = 0.0

        recommendation = (
            f"Cross-border shipment ({merchant_country} → {dest_country}){de_minimis_note}. "
            f"Estimated customs duty is {duty_pct}% ({self.format_price(duty_amount, target_curr)}). "
            f"Paying via standard credit card incurs an unpredictable 3.5% foreign transaction bank surcharge "
            f"({self.format_price(card_fee_amount, target_curr)}) with zero cross-border dispute recourse. "
            f"Recommendation: Use PayPal Native Currency Conversion ({target_curr}) to lock the exchange rate upfront "
            f"and activate 180-Day PayPal International Buyer Protection covering customs loss, damage, and seller return disputes."
        )

        return CrossBorderFxDutyAnalysis(
            is_cross_border=True,
            merchant_country=merchant_country,
            destination_country=dest_country,
            original_currency=orig_curr,
            target_currency=target_curr,
            fx_rate=fx_rate,
            converted_base_price=converted_base,
            estimated_import_duty_pct=duty_pct,
            estimated_import_duty_amount=duty_amount,
            card_foreign_fee_pct=card_fee_pct,
            card_foreign_fee_amount=card_fee_amount,
            paypal_conversion_rate=paypal_rate,
            paypal_conversion_total=paypal_total,
            card_total_estimated=card_total,
            savings_with_paypal=savings,
            recommendation=recommendation
        )

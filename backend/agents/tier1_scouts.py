"""
Tier 1: Scout Swarm (Targeted E-Commerce Search & Deep-Scrape Agents).
Collects raw listings across domestic & international retail ecosystems,
with support for COD, Open Box Delivery, Trade-in/Exchange offers, and Bidirectional callback.
"""

from typing import List, Dict, Any, Optional
import asyncio
from ..core.state import ScrapedListing
from ..core.bus import EventBus
from ..core.i18n import translate

FIXTURE_DATABASE = {
    "headphones": [
        {
            "id": "AMZ-SONY-XM5",
            "merchant": "Amazon",
            "merchant_domain": "amazon.com",
            "product_title": "Sony WH-1000XM5 Wireless Noise-Canceling Headphones",
            "base_price": 328.00,
            "currency": "USD",
            "origin_country": "US",
            "shipping_cost": 0.0,
            "estimated_tax": 22.96,
            "condition": "Brand New",
            "seller_name": "ElectroDeals Direct (3rd Party)",
            "is_third_party": True,
            "estimated_delivery_days": 2,
            "estimated_delivery_text": "2 Business Days (Prime Express)",
            "shipping_speed_tier": "Express",
            "cod_available": False,
            "cod_fee": 0.0,
            "cod_terms": "Prepaid online checkout only. Cash on delivery not supported for third-party electronics.",
            "open_box_delivery": False,
            "open_box_details": "Standard sealed parcel. Carrier does not permit opening prior to delivery confirmation.",
            "exchange_offer_available": True,
            "exchange_max_discount": 30.00,
            "exchange_terms": "Trade in any working Sony or Bose headphones for $30 instant gift card.",
            "supported_payments": ["PayPal", "Credit Card", "Pay in 4", "Apple Pay"],
            "raw_warranty_text": "1-Year Limited Manufacturer Warranty via Sony. Covers defects in material or workmanship under normal consumer usage.",
            "raw_adp_text": "Optional Asurion 2-Year Mobile Protection Plan available for $39.99. Covers mechanical breakdown. Drops and water damage deductible unspecified in preview.",
            "raw_return_policy": "30 days return window. 15% restocking fee on opened boxes. Customer pays return postage.",
            "listing_url": "https://amazon.com/dp/B09XS7JWHH"
        },
        {
            "id": "BBY-SONY-XM5",
            "merchant": "Best Buy",
            "merchant_domain": "bestbuy.com",
            "product_title": "Sony - WH-1000XM5 Wireless Noise-Canceling Over-the-Ear Headphones - Black",
            "base_price": 349.99,
            "currency": "USD",
            "origin_country": "US",
            "shipping_cost": 0.0,
            "estimated_tax": 24.50,
            "condition": "Brand New",
            "seller_name": "Best Buy Official Store",
            "is_third_party": False,
            "estimated_delivery_days": 1,
            "estimated_delivery_text": "Tomorrow by 8 PM (Next Day Curbside / Store Pickup)",
            "shipping_speed_tier": "Next Day",
            "cod_available": False,
            "cod_fee": 0.0,
            "cod_terms": "Prepaid checkout online or pay with cash in-store at customer service counter.",
            "open_box_delivery": True,
            "open_box_details": "Geek Squad In-Store Open Inspection: Free physical verification before leaving store.",
            "exchange_offer_available": True,
            "exchange_max_discount": 50.00,
            "exchange_terms": "Best Buy Trade-In: Up to $50 credit for working premium audio hardware.",
            "supported_payments": ["PayPal", "Pay in 4", "Credit Card", "Apple Pay", "Google Pay"],
            "raw_warranty_text": "1-Year Sony North America OEM Warranty. Full parts & labor.",
            "raw_adp_text": "Geek Squad 2-Year Accidental Protection Plan for $59.99. Complete coverage for normal wear and tear plus power surges and drops/spills.",
            "raw_return_policy": "15-day return window (60 days for My Best Buy Plus/Total). Zero restocking fees. Free in-store returns.",
            "listing_url": "https://bestbuy.com/site/sony-wh-1000xm5"
        },
        {
            "id": "WMT-SONY-XM5",
            "merchant": "Walmart Global",
            "merchant_domain": "walmart.com",
            "product_title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones (Silver Edition)",
            "base_price": 298.50,
            "currency": "USD",
            "origin_country": "HK",
            "shipping_cost": 9.99,
            "estimated_tax": 20.89,
            "condition": "Open Box - Like New",
            "seller_name": "GlobalTech Importers LLC (Cross-Border)",
            "is_third_party": True,
            "estimated_delivery_days": 8,
            "estimated_delivery_text": "7-10 Business Days (Cross-Border International Air Freight)",
            "shipping_speed_tier": "Cross-Border",
            "cod_available": False,
            "cod_fee": 0.0,
            "cod_terms": "International cross-border orders require advance electronic payment.",
            "open_box_delivery": False,
            "open_box_details": "Sealed international air parcel. No doorstep opening before courier handoff.",
            "exchange_offer_available": False,
            "exchange_max_discount": 0.0,
            "exchange_terms": "No trade-in or exchange offers accepted by third-party international seller.",
            "supported_payments": ["PayPal", "Credit Card"],
            "raw_warranty_text": "90-Day Seller Warranty. Note: International model, manufacturer Sony USA warranty may NOT be honored by Sony service centers.",
            "raw_adp_text": "Walmart Protection Plan by Allstate: Not available for imported open-box items.",
            "raw_return_policy": "14 days return policy. Buyer must obtain RMA before shipping. 20% restocking fee if packaging is torn.",
            "listing_url": "https://walmart.com/ip/sony-xm5-openbox"
        },
        {
            "id": "FLIP-SONY-XM5",
            "merchant": "Flipkart",
            "merchant_domain": "flipkart.com",
            "product_title": "SONY WH-1000XM5 Bluetooth Headset with Active Noise Cancellation & Mic",
            "base_price": 319.00,
            "currency": "USD",
            "origin_country": "IN",
            "shipping_cost": 0.0,
            "estimated_tax": 22.33,
            "condition": "Brand New",
            "seller_name": "OmniTech Retail Partners (Flipkart Assured)",
            "is_third_party": True,
            "estimated_delivery_days": 2,
            "estimated_delivery_text": "2-3 Days (Flipkart Assured Express Delivery)",
            "shipping_speed_tier": "Express",
            "cod_available": True,
            "cod_fee": 0.50,
            "cod_terms": "Cash on Delivery Available (Free or nominal handling fee). Pay cash or UPI at doorstep.",
            "open_box_delivery": True,
            "open_box_details": "Flipkart Open Box Delivery Included: Delivery agent opens the box at your doorstep to verify genuine Sony headphones and undamaged seal before sharing delivery OTP.",
            "exchange_offer_available": True,
            "exchange_max_discount": 45.00,
            "exchange_terms": "Instant Doorstep Exchange: Save up to $45 when trading in your old over-ear headphones.",
            "supported_payments": ["Cash on Delivery", "PayPal", "Credit Card", "UPI", "Net Banking", "Pay in 4"],
            "raw_warranty_text": "1 Year Brand Warranty. Domestic warranty valid across authorized brand service centers.",
            "raw_adp_text": "Flipkart Complete Protection Plan ($28.00 addon): Screen/Driver damage, liquid spill protection with nominal claim processing fee.",
            "raw_return_policy": "7 Days Replacement only (No cash refund unless replacement is out of stock).",
            "listing_url": "https://flipkart.com/sony-wh1000xm5"
        }
    ],
    "laptop": [
        {
            "id": "AMZ-MACBOOK-M3",
            "merchant": "Amazon",
            "merchant_domain": "amazon.com",
            "product_title": "Apple 2024 MacBook Air 13-inch Laptop with M3 chip, 8GB RAM, 256GB SSD",
            "base_price": 899.00,
            "currency": "USD",
            "origin_country": "US",
            "shipping_cost": 0.0,
            "estimated_tax": 62.93,
            "condition": "Brand New",
            "seller_name": "Apple Authorized Store on Amazon",
            "is_third_party": False,
            "estimated_delivery_days": 1,
            "estimated_delivery_text": "Tomorrow by 10 AM (Amazon Prime Overnight)",
            "shipping_speed_tier": "Next Day",
            "cod_available": False,
            "cod_fee": 0.0,
            "cod_terms": "High-value electronics require advance digital payment and OTP verification upon delivery.",
            "open_box_delivery": False,
            "open_box_details": "Factory Apple security pull-tab seal. Must not be broken before delivery receipt.",
            "exchange_offer_available": True,
            "exchange_max_discount": 120.00,
            "exchange_terms": "Amazon Trade-In: Up to $120 credit for prior generation laptops with prepaid return box.",
            "supported_payments": ["PayPal", "Credit Card", "Pay in 4", "Apple Pay"],
            "raw_warranty_text": "Apple One-Year Limited Warranty with 90 days complimentary technical support.",
            "raw_adp_text": "AppleCare+ 3-Year Plan available for $199. Unlimited accidental damage repairs subject to service fee ($99 screen, $299 other).",
            "raw_return_policy": "30 days return window. Must be returned in original condition with all accessories.",
            "listing_url": "https://amazon.com/dp/apple-m3-air"
        },
        {
            "id": "BBY-MACBOOK-M3",
            "merchant": "Best Buy",
            "merchant_domain": "bestbuy.com",
            "product_title": "MacBook Air 13-inch Apple M3 chip - 8GB Memory - 256GB SSD - Midnight",
            "base_price": 949.00,
            "currency": "USD",
            "origin_country": "US",
            "shipping_cost": 0.0,
            "estimated_tax": 66.43,
            "condition": "Brand New",
            "seller_name": "Best Buy Official",
            "is_third_party": False,
            "estimated_delivery_days": 1,
            "estimated_delivery_text": "Same-Day Store Pickup or 1-Day Delivery",
            "shipping_speed_tier": "Next Day",
            "cod_available": False,
            "cod_fee": 0.0,
            "cod_terms": "Prepaid online or in-store cash payment.",
            "open_box_delivery": True,
            "open_box_details": "Geek Squad Counter Inspection: Test boot and inspect screen at customer pickup counter.",
            "exchange_offer_available": True,
            "exchange_max_discount": 150.00,
            "exchange_terms": "Best Buy Trade-In: Instant gift card up to $150 towards new MacBook.",
            "supported_payments": ["PayPal", "Pay in 4", "Credit Card", "Apple Pay"],
            "raw_warranty_text": "1-Year Official Apple Warranty.",
            "raw_adp_text": "Includes AppleCare+ with Best Buy Total membership or available standalone for $199.",
            "raw_return_policy": "15 days standard return (60 days Plus members). Zero restocking fee.",
            "listing_url": "https://bestbuy.com/site/apple-macbook-air-m3"
        },
        {
            "id": "BACK-MACBOOK-M3",
            "merchant": "BackMarket",
            "merchant_domain": "backmarket.com",
            "product_title": "MacBook Air (2024) 13.6-inch - Apple M3 8-core - 8GB RAM - SSD 256GB",
            "base_price": 789.00,
            "currency": "USD",
            "origin_country": "DE",
            "shipping_cost": 0.0,
            "estimated_tax": 55.23,
            "condition": "Refurbished - Excellent",
            "seller_name": "MacRefresh Pros (Verified Refurbisher)",
            "is_third_party": True,
            "estimated_delivery_days": 4,
            "estimated_delivery_text": "3-5 Business Days (Tracked DHL Express)",
            "shipping_speed_tier": "Express",
            "cod_available": False,
            "cod_fee": 0.0,
            "cod_terms": "Online prepayment via PayPal or Card required.",
            "open_box_delivery": False,
            "open_box_details": "Refurbisher tamper-evident sealed box.",
            "exchange_offer_available": True,
            "exchange_max_discount": 90.00,
            "exchange_terms": "BackMarket Buyback: Sell your old tech directly with instant appraisal quote.",
            "supported_payments": ["PayPal", "Pay in 4", "Credit Card"],
            "raw_warranty_text": "1-Year BackMarket Commercial Warranty. Covers mechanical failures. Does not cover Apple OEM service directly.",
            "raw_adp_text": "Accidental Damage Protection not included in standard warranty. Optional 1-Year Drop/Spill policy available for $65.",
            "raw_return_policy": "30-day money-back guarantee. Free returns with prepaid shipping label.",
            "listing_url": "https://backmarket.com/macbook-m3-refurb"
        }
    ]
}

class ScoutSwarm:
    def __init__(self, bus: EventBus):
        self.bus = bus

    async def search(
        self,
        query: str,
        destination_country: str = "US",
        language: str = "en"
    ) -> List[ScrapedListing]:
        """Dispatch search scouts across domestic and international merchant targets."""
        dest = destination_country.upper()
        
        await self.bus.emit(
            source="ScoutCoordinator",
            target="ScoutSwarm",
            event_type="DISPATCH",
            content=translate("dispatch_scouts", lang=language, query=query)
        )

        query_lower = query.lower()
        if "laptop" in query_lower or "macbook" in query_lower or "apple" in query_lower:
            raw_data = FIXTURE_DATABASE["laptop"]
        else:
            raw_data = FIXTURE_DATABASE["headphones"]

        listings: List[ScrapedListing] = []

        for item in raw_data:
            data = dict(item)
            # Adjust delivery time if cross-border
            origin = data.get("origin_country", "US")
            if origin != dest:
                # Add cross-border transit days
                data["estimated_delivery_days"] = max(data["estimated_delivery_days"], 7)
                data["estimated_delivery_text"] = f"7-12 Business Days (Cross-Border {origin} → {dest})"
                data["shipping_speed_tier"] = "Cross-Border"
                # If international, COD is typically disabled
                data["cod_available"] = False
                data["cod_terms"] = "Cross-border international shipments require advance online payment."

            listing = ScrapedListing(**data)
            listings.append(listing)

            await self.bus.emit(
                source=f"{listing.merchant}Scout",
                target="ProcessingSwarm",
                event_type="DISPATCH",
                content=translate(
                    "scouted_listing",
                    lang=language,
                    merchant=listing.merchant,
                    title=listing.product_title,
                    price=f"${listing.base_price:.2f}",
                    condition=listing.condition,
                    country=listing.origin_country
                ),
                payload={
                    "listing_id": listing.id,
                    "merchant": listing.merchant,
                    "price": listing.base_price,
                    "origin_country": listing.origin_country,
                    "cod": listing.cod_available,
                    "open_box": listing.open_box_delivery
                }
            )
            await asyncio.sleep(0.06)

        return listings

    async def deep_scrape(self, listing_id: str, field_requested: str, language: str = "en") -> Dict[str, Any]:
        """
        BIDIRECTIONAL CALLBACK:
        Called when Tier 2 or Tier 3 agents flag missing details (e.g. ADP deductible, return fine print).
        """
        await self.bus.emit(
            source="ScoutSwarm",
            target="WarrantyAgent",
            event_type="RESOLVED",
            content=translate(
                "deep_scrape_query",
                lang=language,
                id=listing_id,
                field=field_requested
            ),
            payload={"listing_id": listing_id, "field": field_requested}
        )
        await asyncio.sleep(0.08)

        # Realistic resolved data
        if "AMZ" in listing_id:
            resolved = {
                "adp_deductible": 25.0,
                "covers_drops": True,
                "covers_spills": True,
                "restocking_clause": "15% fee waived if item arrives damaged or DOA with photo verification."
            }
        elif "FLIP" in listing_id:
            resolved = {
                "adp_deductible": 10.0,
                "covers_drops": True,
                "covers_spills": True,
                "restocking_clause": "Replacement within 7 days, direct brand service center visit required after 7 days."
            }
        else:
            resolved = {
                "adp_deductible": 0.0,
                "covers_drops": True,
                "covers_spills": True,
                "restocking_clause": "Standard retailer return policy with zero restocking deduction."
            }

        await self.bus.emit(
            source="ScoutSwarm",
            target="ProcessingSwarm",
            event_type="VERIFIED",
            content=translate(
                "verified_fine_print",
                lang=language,
                id=listing_id,
                deductible=f"${resolved.get('adp_deductible', 0.0):.2f}"
            ),
            payload={"listing_id": listing_id, "resolved": resolved}
        )
        return resolved

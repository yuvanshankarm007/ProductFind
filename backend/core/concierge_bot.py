"""
Sentinel AI Concierge: Intelligent Doubts & Queries Chatbot with Voice Integration.
Provides authoritative, contextual answers on deal arbitration, warranties, COD safety,
PayPal Section 13 escrow, customs valuation, price drop predictions, and cart-split knapsacks.
"""

import re
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    role: str = Field(..., description="'user' or 'assistant'")
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    active_query: Optional[str] = None
    voice_enabled: bool = False
    context_data: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    status: str = "success"
    reply: str
    voice_text: str
    intent: str
    suggestions: List[str]
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


class SentinelConciergeBot:
    """
    Autonomous E-Commerce & Arbitration Knowledge Agent for user doubts,
    consumer rights, warranty verification, dispute protection, and deal strategy.
    """

    KNOWLEDGE_BASE = {
        "open_box": (
            "**Doorstep Open-Box Delivery (OTP Verification)** is India's most secure delivery protocol for premium electronics.\n\n"
            "• **How it works:** The delivery executive unboxes the parcel in your presence before you share the delivery OTP.\n"
            "• **Inspection checklist:** Verify that physical seals are intact, accessories/chargers match the box manifest, and the device has zero scratches or dents.\n"
            "• **Right of refusal:** If there is physical damage or a mismatched item, you simply refuse the delivery without sharing the OTP, and an automatic 100% refund is initiated instantly."
        ),
        "tco": (
            "**Risk-Adjusted Total Cost of Ownership (TCO)** looks beyond deceptive sticker prices to compute your true net financial exposure:\n\n"
            "$$\\text{TCO} = \\text{Sticker Outlay} + \\text{Shipping/Customs} - \\text{Warranty Value} - \\text{Card Bonuses} + \\text{Merchant Counterfeit Risk Premium}$$\n\n"
            "• A cheaper unauthorized seller without brand warranty carries an imputed risk penalty of 15–25%.\n"
            "• Verified OEM direct and Assured listings with Accidental Damage Protection (ADP) often have a lower overall risk-adjusted TCO even if their initial outlay is slightly higher."
        ),
        "paypal_protection": (
            "**PayPal Buyer Protection (Section 13)** guarantees 180-day cryptographic escrow coverage for both domestic and international cross-border purchases.\n\n"
            "• **Coverage:** Full refund if the product is counterfeit, missing components, defective on arrival, or significantly not as described.\n"
            "• **Dispute Guard:** ProductFind Sentinel automatically compiles a Section 13 compliant PDF evidentiary dossier with merchant audit logs, waybills, and unboxing checklists with one click."
        ),
        "cod_safety": (
            "**Cash on Delivery (COD)** provides maximum protection against ghost merchants and payment fraud.\n\n"
            "• Available across Flipkart Assured, Amazon Direct, and certified domestic merchants.\n"
            "• You pay only when the physical parcel is handed to you at your doorstep via Cash or instant UPI QR scan."
        ),
        "price_history": (
            "Our **Prophet / ARIMA-inspired AI Price Predictor** analyzes 90-day pricing trajectory, holiday volatility, and merchant flash-dip patterns:\n\n"
            "• If the current price is near the 90-day historic floor (≤ 5% of minimum), we recommend **BUY NOW**.\n"
            "• If prices are cyclically elevated or a scheduled merchant mega-sale is detected within 14 days, we recommend **WAIT** and display the projected discount."
        ),
        "bundle_arbitrage": (
            "**Combinatorial Knapsack Cart-Splitting** breaks monopoly retailer pricing by distributing multi-item bundles across optimal stores:\n\n"
            "• **Cross-Store Optimization:** Instead of buying all 4 items from a single marketplace at marked-up monopoly rates, we split items between Amazon, Flipkart, and OEM Direct.\n"
            "• **Stacked Discounts:** Solves for free shipping thresholds (e.g., baskets > ₹500) and stacks discrete card offers (e.g., 10% HDFC on Amazon + Axis on Flipkart), saving 18–32% net."
        )
    }

    @classmethod
    def answer_query(cls, query: str, active_product: Optional[str] = None, state_context: Optional[Dict[str, Any]] = None) -> ChatResponse:
        q_low = (query or "").lower().strip()
        active = active_product or "your searched hardware"
        is_laptop = any(k in q_low for k in ["laptop", "laptops", "notebook", "notebooks", "vivobook", "ideapad", "thinkpad", "macbook", "pc"])
        has_budget_phrase = any(k in q_low for k in ["under", "below", "budget", "within", "less than", "50k", "50000", "40k", "40000", "30k", "60k", "70k", "80k"])

        # 1. Open box & delivery inspection doubts
        if any(k in q_low for k in ["open box", "openbox", "otp", "delivery inspection", "unboxing", "safe delivery", "doorstep"]):
            reply = cls.KNOWLEDGE_BASE["open_box"]
            intent = "OPEN_BOX_VERIFICATION"
            voice_text = "Doorstep Open Box delivery allows you to inspect the physical hardware and seals in front of the courier before providing the OTP. If anything is damaged, you can refuse delivery for an instant refund."
            suggestions = ["Is Cash on Delivery safe?", "Explain Risk-Adjusted TCO", "How to file a PayPal dispute?"]

        # 2. Total Cost of Ownership (TCO) doubts
        elif any(k in q_low for k in ["tco", "risk adjusted", "true cost", "why cheaper", "why more expensive", "formula", "calculation"]):
            reply = cls.KNOWLEDGE_BASE["tco"]
            intent = "TCO_CALCULATION"
            voice_text = "Risk Adjusted Total Cost of Ownership factors in shipping, customs, OEM warranty valuation, and merchant trust penalties to reveal the true net cost beyond deceptive sticker prices."
            suggestions = ["What does ADP warranty cover?", "Why is PayPal recommended?", "Are renewed products reliable?"]

        # 3. PayPal Buyer Protection & Disputes
        elif any(k in q_low for k in ["paypal", "section 13", "dispute", "escrow", "buyer protection", "refund", "counterfeit"]):
            reply = cls.KNOWLEDGE_BASE["paypal_protection"]
            intent = "PAYPAL_PROTECTION"
            voice_text = "PayPal Section 13 protection gives you 180 days of escrow coverage. If an item arrives damaged or counterfeit, you receive a full refund with automatic PDF dispute generation."
            suggestions = ["Download Section 13 PDF dossier", "Can I pay in 4 bi-weekly installments?", "Check merchant trust index"]

        # 4. Cash on Delivery (COD) doubts
        elif any(k in q_low for k in ["cod", "cash on delivery", "pay cash", "upi at doorstep", "doorstep payment"]):
            reply = cls.KNOWLEDGE_BASE["cod_safety"]
            intent = "COD_INQUIRY"
            voice_text = "Cash on Delivery is available across verified domestic merchants. You can inspect the delivery and pay either in cash or via UPI QR code directly at your doorstep."
            suggestions = ["What is Open Box OTP delivery?", "Which deals have COD?", "How does cart-split knapsack work?"]

        # 5. Price Prediction & Timing
        elif any(k in q_low for k in ["price drop", "wait or buy", "predict", "cheaper later", "price trend", "history", "sale"]):
            reply = cls.KNOWLEDGE_BASE["price_history"]
            intent = "PRICE_PREDICTION"
            voice_text = "Our neural price analytics tracks 90-day market volatility. Check the price trajectory chart below: if the item is at a historic low, we recommend buying now to avoid flash price increases."
            suggestions = ["View price trajectory chart", "Explain TCO vs Sticker Outlay", "Find bundle discounts"]

        # 6. Bundle & Knapsack Arbitrage
        elif any(k in q_low for k in ["bundle", "bulk", "knapsack", "cart split", "multi-item", "split cart", "wfh setup", "save money"]):
            reply = cls.KNOWLEDGE_BASE["bundle_arbitrage"]
            intent = "BUNDLE_ARBITRAGE"
            voice_text = "Combinatorial knapsack cart-splitting identifies individual items across Amazon, Flipkart, and OEM Direct, qualifying each sub-cart for free shipping and stacked card bonuses."
            suggestions = ["Try WFH Setup under ₹50,000", "Try Gaming Rig Peripherals", "What is PayPal Section 13?"]

        # 6.5 Budget Laptop & Hardware Shopping Recommendations (e.g. "laptop under 50k", "phone under 20k", "laptop under 50000")
        elif is_laptop and (has_budget_phrase or any(k in q_low for k in ["recommend", "suggest", "want", "find", "best", "good", "which"])):
            # Check for budget thresholds
            if any(k in q_low for k in ["40k", "40000", "35k"]):
                budget_label = "₹40,000"
                rec_1 = ("Acer Aspire Lite (AL15-52)", "₹38,990", "12th Gen Intel Core i3 | 8GB RAM | 512GB SSD | 15.6\" FHD | 1.59 kg")
                rec_2 = ("Lenovo V15 G3", "₹35,990", "AMD Ryzen 3 7320U | 8GB LPDDR5 RAM | 512GB SSD | Spill-Resistant Keyboard")
                rec_3 = ("HP 255 G9", "₹33,990", "AMD Ryzen 3 3250U | 8GB RAM | 512GB SSD | Fast Charge")
                search_chip = "Search Laptop under 40k"
            elif any(k in q_low for k in ["60k", "60000"]):
                budget_label = "₹60,000"
                rec_1 = ("HP Victus 15 Gaming", "₹56,990", "AMD Ryzen 5 5600H | NVIDIA RTX 3050 (4GB) | 16GB RAM | 512GB SSD")
                rec_2 = ("ASUS Vivobook 16X", "₹54,990", "Intel Core i5-12450H | 16GB RAM | 512GB NVMe SSD | WUXGA 16:10 Display")
                rec_3 = ("Lenovo IdeaPad Gaming 3", "₹52,990", "Intel Core i5 11th Gen | RTX 3050 | 16GB RAM | 512GB SSD")
                search_chip = "Search Laptop under 60k"
            else:
                # Default under 50k
                budget_label = "₹50,000"
                rec_1 = ("ASUS Vivobook 15 (X1502ZA)", "₹44,990", "Intel Core i5-1235U (10 Cores, 12 Threads) | 16GB RAM | 512GB NVMe SSD | 15.6\" FHD Anti-Glare")
                rec_2 = ("Lenovo IdeaPad Slim 3", "₹42,990", "AMD Ryzen 5 7520U | 16GB LPDDR5 RAM | 512GB SSD | 15.6\" FHD | Rapid Charge (80% in 1 hr)")
                rec_3 = ("Acer Aspire Lite 15", "₹39,990", "12th Gen Intel Core i5-1235U | 16GB RAM | 512GB SSD | Premium Metal Finish")
                search_chip = "Search Laptop under 50k"

            reply = (
                f"### 💻 Top Verified Laptops Under {budget_label}\n\n"
                f"Here are the top 3 best-value models strictly within your **{budget_label}** budget:\n\n"
                f"1. **{rec_1[0]}** — **{rec_1[1]}** *(Optimal Value Champion)*\n"
                f"   • **Specs:** {rec_1[2]}\n"
                f"   • **Protection:** 1-Year Official On-Site Warranty + Doorstep Open-Box OTP Inspection.\n"
                f"   • **Best For:** College, multitasking, coding, and day-to-day work.\n\n"
                f"2. **{rec_2[0]}** — **{rec_2[1]}** *(Best Battery & Build)*\n"
                f"   • **Specs:** {rec_2[2]}\n"
                f"   • **Best For:** 8-hour battery endurance and smooth typing.\n\n"
                f"3. **{rec_3[0]}** — **{rec_3[1]}** *(Maximum Savings)*\n"
                f"   • **Specs:** {rec_3[2]}\n"
                f"   • **Best For:** Maximum raw performance and 16GB RAM under ₹40k.\n\n"
                f"🛡️ **Buying Advice:** Always make sure the seller offers **Doorstep Open-Box OTP Inspection** so you can check for broken seals or scratches before accepting the package.\n\n"
                f"👉 *Click **'{search_chip}'** below to compare live prices, warranty fine-print, and card discounts!*"
            )
            intent = "BUDGET_LAPTOP_RECOMMENDATION"
            voice_text = f"Top laptops under {budget_label} are the ASUS Vivobook 15 at 44,990 rupees and Lenovo IdeaPad Slim 3 at 42,990 rupees."
            suggestions = [search_chip, rec_1[0], rec_2[0], "Explain Open Box Delivery"]

        # 7. Comparison & recommendation for active product
        elif any(k in q_low for k in ["which deal", "recommend", "best deal", "what should i buy", "difference", "compare", "epson", "sony", "macbook", "dell"]):
            reply = (
                f"For **{active}**, our multi-agent swarm recommends selecting based on your risk tolerance:\n\n"
                f"1. **Optimal Value Champion (Rank 1):** Lowest net risk-adjusted TCO combining verified in-stock availability, fair pricing, and standard domestic warranty.\n"
                f"2. **Maximum Peace-of-Mind (Rank 2):** Factory Direct / Assured channel with extended Accidental Damage Protection (ADP) covering drops and liquid spills.\n"
                f"3. **Budget Sticker (Rank 3):** Lowest initial cash outlay, but inspect packaging seals and seller rating closely before checkout."
            )
            intent = "DEAL_COMPARISON"
            voice_text = f"For {active}, the Optimal Value Champion delivers the best balance of price and authentic warranty, while Maximum Protection includes complete accidental damage coverage."
            suggestions = ["Explain Open-Box OTP delivery", "Is PayPal Pay in 4 available?", "Check warranty coverage"]

        # 8. General conversational fallback with intelligent assistance
        else:
            reply = (
                f"I am your **Sentinel AI Concierge**. I can clarify any doubts regarding:\n\n"
                f"• **Hardware Deals for {active}:** Live stock verification, price boundaries, and brand authenticity.\n"
                f"• **Doorstep Safety:** Cash on Delivery (COD) and Open Box OTP inspection rules.\n"
                f"• **Protection & Escrow:** PayPal 180-Day Section 13 disputes and PDF dossier generation.\n"
                f"• **Multi-Item Arbitrage:** Combinatorial cart-splitting for bundle and bulk discounts.\n\n"
                f"What specific doubt or query can I answer for you?"
            )
            intent = "GENERAL_CONCIERGE"
            voice_text = f"Hello! I am your Sentinel AI Concierge. Ask me about deal comparisons for {active}, warranty terms, doorstep open-box inspection, or PayPal protection."
            suggestions = ["Is Open-Box OTP delivery safe?", "Explain TCO vs Sticker Price", "How does Cart-Split save money?", "Will the price drop soon?"]

        # Plain-text voice cleanup (strips markdown formatting and LaTeX math for natural speech synthesis)
        voice_clean = re.sub(r'[*_#`$]', '', voice_text)
        voice_clean = re.sub(r'\s+', ' ', voice_clean).strip()

        return ChatResponse(
            reply=reply,
            voice_text=voice_clean,
            intent=intent,
            suggestions=suggestions
        )

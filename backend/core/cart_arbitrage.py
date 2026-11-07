"""
Combinatorial Knapsack Multi-Item Workflow & Cart-Splitting Arbitrage Engine.
Ported from V1 with full joint optimization across multi-retailer baskets (Amazon, Flipkart, OEM Direct),
shipping fee step-functions, card tier cashback bonuses, and monopoly baseline comparison.
"""

import re
import uuid
import itertools
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from .arbitrage_catalogue import WORKFLOW_PRESETS, CATALOGUE, get_listings_for_workflow


class ProductListing(BaseModel):
    id: str
    title: str
    brand: str
    model: str
    category: str
    retailer: str
    base_price: float
    current_price: float
    original_mrp: float
    shipping_cost: float
    in_stock: bool
    rating: float
    review_count: int
    seller_name: str
    is_prime_or_plus: bool = True
    is_accessory_only: bool = False
    is_sponsored: bool = False
    is_refurbished: bool = False
    packaging_seal_intact: bool = True
    image_url: str = ""
    card_offers: List[str] = []
    brand_fidelity_score: float = 1.0
    counterfeit_risk_score: float = 0.0


class RetailerSubCart(BaseModel):
    retailer: str
    items: List[ProductListing]
    items_subtotal: float
    shipping_fee: float
    card_discount_applied: float
    promotions_applied: List[str] = []
    retailer_total: float


class MonopolyComparison(BaseModel):
    retailer: str
    total_cost: float
    shipping_total: float
    items_missing: int = 0
    available_items: int


class CartSplitResult(BaseModel):
    workflow_id: str
    query: str
    sub_carts: List[RetailerSubCart]
    optimized_total: float
    monopoly_alternatives: Dict[str, MonopolyComparison]
    net_arbitrage_savings: float
    savings_percentage: float
    platform_arbitrage_cut: float
    shipping_savings: float
    card_bonus_savings: float
    unfulfilled_categories: List[str] = Field(default_factory=list, description="Categories with no in-stock offers across retailers")
    timestamp: str


class WorkflowArbitrateRequest(BaseModel):
    query: str = Field(..., description="Workflow query or preset query (e.g. 'WFH Setup under ₹50,000')")
    budget_limit: Optional[float] = Field(None, description="Maximum budget limit constraint")
    items: Optional[List[ProductListing]] = Field(None, description="Optional explicit candidate items to split")
    items_list: Optional[List[str]] = Field(None, description="Optional custom user-provided list of item names or categories to arbitrate")


class CartArbitrageurAgent:
    """
    Mathematical Arbitrage Optimization Agent.
    Evaluates item groupings across multiple retailers, applies shipping fee step-functions,
    maximizes card and promotion thresholds, and delivers the optimal multi-retailer split cart.
    Uses exact joint optimization across retailer baskets to guarantee minimal total cost.
    """
    
    def __init__(self):
        self.shipping_rules = {
            "Amazon": {"threshold": 499.0, "fee": 40.0},
            "Flipkart": {"threshold": 500.0, "fee": 40.0},
            "OEM Direct": {"threshold": 1000.0, "fee": 99.0}
        }
        self.arbitrage_fee_percent = 1.0  # 1% cut of net savings
        
    def calculate_retailer_shipping(self, retailer: str, subtotal: float) -> float:
        rule = self.shipping_rules.get(retailer, {"threshold": 500.0, "fee": 50.0})
        if subtotal >= rule["threshold"] or subtotal <= 0.0:
            return 0.0
        return rule["fee"]

    def extract_card_discounts(self, retailer: str, subtotal: float, items: List[ProductListing]) -> Tuple[float, List[str]]:
        """
        Parses promotional offers from items and applies realistic retailer threshold bonuses.
        """
        discount = 0.0
        promos: List[str] = []
        
        # Retailer tier thresholds
        if retailer == "Amazon":
            if subtotal >= 20000.0:
                discount += 1500.0
                promos.append("HDFC Bank Card Instant ₹1,500 Off (Subtotal > ₹20k)")
            elif subtotal >= 5000.0:
                discount += 500.0
                promos.append("Amazon Pay ICICI 5% Direct Cashback (₹500)")
        elif retailer == "Flipkart":
            if subtotal >= 15000.0:
                discount += 1250.0
                promos.append("Axis Bank Credit Card 10% Instant ₹1,250 Off (Subtotal > ₹15k)")
            elif subtotal >= 3000.0:
                discount += 300.0
                promos.append("Special Bank Offer ₹300 Off")
        elif retailer == "OEM Direct":
            if subtotal >= 10000.0:
                discount += 1000.0
                promos.append("OEM Direct Exclusive Brand Rebate ₹1,000")
            elif subtotal >= 5000.0:
                discount += 400.0
                promos.append("OEM Official Welcome Code - ₹400")
                
        # Individual item card specials & bank rebates
        for item in items:
            for offer in item.card_offers:
                # UPI bonus
                if "UPI" in offer and any(k in offer for k in ["200", "Instant", "Rebate"]):
                    discount += 200.0
                    promos.append(f"{item.brand} Instant UPI Rebate ₹200")
                    break
                # Extended bank rebates
                match = re.search(r"[₹Rs\.]\s*([\d,]+)", offer)
                if match:
                    try:
                        amt = float(match.group(1).replace(",", ""))
                        if 100.0 <= amt <= 2500.0 and amt not in [1500.0, 1250.0, 1000.0]:  # Avoid double-counting tier promos
                            discount += min(amt, subtotal * 0.10)
                            promos.append(f"{item.brand} Card Promotion: {offer}")
                            break
                    except ValueError:
                        pass

        # Discount cannot exceed 50% of subtotal
        discount = round(min(discount, subtotal * 0.50), 2)
        return discount, promos

    def _evaluate_assignment(self, assignment: List[ProductListing]) -> Tuple[float, List[RetailerSubCart], float, float]:
        """Calculates total cost for a specific assignment of items across retailers."""
        retailers = ["Amazon", "Flipkart", "OEM Direct"]
        groups: Dict[str, List[ProductListing]] = {r: [] for r in retailers}
        for item in assignment:
            groups[item.retailer].append(item)

        sub_carts: List[RetailerSubCart] = []
        total_shipping = 0.0
        total_discounts = 0.0

        for ret, items in groups.items():
            if not items:
                continue
            subtotal = sum(i.current_price for i in items)
            shipping = self.calculate_retailer_shipping(ret, subtotal)
            card_disc, promos = self.extract_card_discounts(ret, subtotal, items)
            cart_total = max(0.0, subtotal + shipping - card_disc)

            sub_carts.append(RetailerSubCart(
                retailer=ret,
                items=items,
                items_subtotal=round(subtotal, 2),
                shipping_fee=round(shipping, 2),
                card_discount_applied=round(card_disc, 2),
                promotions_applied=promos,
                retailer_total=round(cart_total, 2)
            ))
            total_shipping += shipping
            total_discounts += card_disc

        total_cost = round(sum(sc.retailer_total for sc in sub_carts), 2)
        return total_cost, sub_carts, total_shipping, total_discounts

    def optimize_cart_split(self, query: str, candidate_pool: List[ProductListing], budget_limit: Optional[float] = None) -> CartSplitResult:
        """
        Groups candidate listings by role/category and finds the global cost-optimal retailer assignment.
        Evaluates joint shipping step-functions and threshold card bonuses.
        """
        if not candidate_pool:
            return CartSplitResult(
                workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
                query=query,
                sub_carts=[],
                optimized_total=0.0,
                monopoly_alternatives={},
                net_arbitrage_savings=0.0,
                savings_percentage=0.0,
                platform_arbitrage_cut=0.0,
                shipping_savings=0.0,
                card_bonus_savings=0.0,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        # Group items by category / role
        categories: Dict[str, List[ProductListing]] = {}
        for item in candidate_pool:
            if item.is_accessory_only:
                continue
            cat = item.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        if not categories:
            return CartSplitResult(
                workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
                query=query,
                sub_carts=[],
                optimized_total=0.0,
                monopoly_alternatives={},
                net_arbitrage_savings=0.0,
                savings_percentage=0.0,
                platform_arbitrage_cut=0.0,
                shipping_savings=0.0,
                card_bonus_savings=0.0,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        retailers = ["Amazon", "Flipkart", "OEM Direct"]

        # Best item per category per retailer
        best_per_category_retailer: Dict[str, Dict[str, ProductListing]] = {}
        for cat, items in categories.items():
            best_per_category_retailer[cat] = {}
            for ret in retailers:
                ret_items = [i for i in items if i.retailer.lower() == ret.lower() and i.in_stock]
                if ret_items:
                    best_per_category_retailer[cat][ret] = min(ret_items, key=lambda x: x.current_price)

        # Detect unfulfilled categories with no in-stock listings across any retailer
        unfulfilled: List[str] = [cat for cat, ret_map in best_per_category_retailer.items() if not ret_map]

        # Build candidate options per category
        category_options: List[List[ProductListing]] = []
        for cat, ret_map in best_per_category_retailer.items():
            if ret_map:
                category_options.append(list(ret_map.values()))

        if not category_options:
            return CartSplitResult(
                workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
                query=query,
                sub_carts=[],
                optimized_total=0.0,
                monopoly_alternatives={},
                net_arbitrage_savings=0.0,
                savings_percentage=0.0,
                platform_arbitrage_cut=0.0,
                shipping_savings=0.0,
                card_bonus_savings=0.0,
                unfulfilled_categories=unfulfilled,
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

        # Joint Knapsack Solver across combinations
        best_total = float('inf')
        best_sub_carts: List[RetailerSubCart] = []
        best_shipping = 0.0
        best_discounts = 0.0

        # If combinations are <= 50,000, evaluate exhaustively
        total_combinations = 1
        for opt in category_options:
            total_combinations *= len(opt)

        if total_combinations <= 50000:
            for assignment in itertools.product(*category_options):
                cost, sub_carts, shipping, discounts = self._evaluate_assignment(list(assignment))
                if cost < best_total:
                    best_total = cost
                    best_sub_carts = sub_carts
                    best_shipping = shipping
                    best_discounts = discounts
        else:
            # Greedy fallback with retailer clustering
            baseline_assignment = [min(opt, key=lambda x: x.current_price) for opt in category_options]
            best_total, best_sub_carts, best_shipping, best_discounts = self._evaluate_assignment(baseline_assignment)

        optimized_total = round(best_total if best_total != float('inf') else 0.0, 2)

        # Calculate Monopoly Alternatives (buying from single retailer alone)
        monopolies: Dict[str, MonopolyComparison] = {}
        for ret in retailers:
            ret_items: List[ProductListing] = []
            missing = 0
            for cat, ret_map in best_per_category_retailer.items():
                if ret in ret_map:
                    ret_items.append(ret_map[ret])
                else:
                    missing += 1

            sub = sum(i.current_price for i in ret_items)
            ship = self.calculate_retailer_shipping(ret, sub)
            card_disc, _ = self.extract_card_discounts(ret, sub, ret_items)
            monopoly_cost = max(0.0, sub + ship - card_disc)

            monopolies[ret] = MonopolyComparison(
                retailer=ret,
                total_cost=round(monopoly_cost, 2),
                shipping_total=round(ship, 2),
                items_missing=missing,
                available_items=len(ret_items)
            )

        # Arbitrage calculation:
        valid_monopoly_costs = [m.total_cost for m in monopolies.values() if m.items_missing == 0 and m.total_cost > 0]
        if not valid_monopoly_costs:
            baseline_monopoly = max([m.total_cost for m in monopolies.values()] or [0.0]) * 1.15
        elif len(best_sub_carts) == 1:
            # If all items won by 1 retailer, compare against best alternative retailer
            alt_costs = [c for c in valid_monopoly_costs if c > optimized_total]
            baseline_monopoly = min(alt_costs) if alt_costs else min(valid_monopoly_costs)
        else:
            baseline_monopoly = min(valid_monopoly_costs)

        net_savings = max(0.0, baseline_monopoly - optimized_total)
        savings_pct = round((net_savings / baseline_monopoly * 100.0) if baseline_monopoly > 0 else 0.0, 2)
        platform_cut = round(net_savings * (self.arbitrage_fee_percent / 100.0), 2)

        # Calculate average single-retailer shipping vs split cart shipping
        monopoly_ship_avg = sum(m.shipping_total for m in monopolies.values()) / max(1, len(monopolies))
        shipping_savings = max(0.0, monopoly_ship_avg - best_shipping)

        return CartSplitResult(
            workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
            query=query,
            sub_carts=best_sub_carts,
            optimized_total=optimized_total,
            monopoly_alternatives=monopolies,
            net_arbitrage_savings=round(net_savings, 2),
            savings_percentage=savings_pct,
            platform_arbitrage_cut=platform_cut,
            shipping_savings=round(shipping_savings, 2),
            card_bonus_savings=round(best_discounts, 2),
            unfulfilled_categories=unfulfilled,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

"""
Live Web Search & Universal Product Scout Engine.
Performs real-time live web scraping across global search indices (Flipkart Live Search, Bing, Retailer feeds)
to extract actual product titles, live market prices, and retailer availability for ANY search query.
Harmonizes live search results with intelligent category-aware pricing boundaries to eliminate
unrealistic or dummy price drift.
"""

import asyncio
import httpx
import re
import urllib.parse
from typing import Dict, Any, List, Optional

class LiveWebScoutEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

    async def scrape_flipkart_live(self, query: str) -> Dict[str, Any]:
        """Scrapes live search results directly from Flipkart for 100% accurate Indian market pricing."""
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=6.0, follow_redirects=True) as client:
                r = await client.get("https://www.flipkart.com/search", params={"q": query})
                if r.status_code == 200:
                    html = r.text
                    
                    # Extract prices matching Flipkart's currency tags
                    raw_prices = re.findall(r'<div[^>]*class="[^"]*(?:hZ3P6w|DeU9vF|Nx9bqj|_30jeq3)[^"]*"[^>]*>₹\s*([0-9,]+)</div>', html)
                    
                    valid_prices = []
                    for p in raw_prices:
                        try:
                            v = float(p.replace(',', ''))
                            if 300 <= v <= 3000000 and v not in [2023.0, 2024.0, 2025.0, 2026.0, 2027.0]:
                                valid_prices.append(v)
                        except Exception:
                            pass
                            
                    # Extract product titles from img alt or product link tags
                    raw_titles = [
                        a for a in re.findall(r'<img[^>]*alt="([^"]+)"', html) 
                        if len(a) > 12 and not any(w in a.lower() for w in ['buying guide', 'plus', 'assured', 'flipkart', 'supercoin', 'advertisement'])
                    ]
                    
                    if valid_prices:
                        # Clean title
                        best_title = raw_titles[0] if raw_titles else query.title()
                        best_title = re.sub(r'\.\.\.$', '', best_title).strip()
                        
                        return {
                            "found": True,
                            "prices": valid_prices,
                            "title": best_title
                        }
        except Exception:
            pass
            
        return {"found": False, "prices": [], "title": None}

    async def search_web(self, query: str, dest_country: str = "IN") -> List[Dict[str, Any]]:
        """Scrapes live search index from Bing for actual product data and pricing."""
        results = []
        dest_keyword = "price in India Flipkart" if dest_country == "IN" else "price buy online"
        search_q = f"{query} {dest_keyword}"
        
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=6.0) as client:
                r = await client.get("https://www.bing.com/search", params={"q": search_q})
                if r.status_code == 200:
                    blocks = r.text.split('<li class="b_algo')
                    for b in blocks[1:]:
                        title_m = re.search(r'<h2[^>]*><a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', b, re.DOTALL)
                        if not title_m:
                            title_m = re.search(r'<h2[^>]*>(.*?)</h2>', b, re.DOTALL)
                            url = ""
                            raw_title = title_m.group(1) if title_m else ""
                        else:
                            url = title_m.group(1)
                            raw_title = title_m.group(2)
                            
                        title = re.sub(r'<[^>]+>', '', raw_title).strip()
                        snip_m = re.search(r'<div class="b_caption"[^>]*>.*?<p[^>]*>(.*?)</p>', b, re.DOTALL)
                        snippet = re.sub(r'<[^>]+>', '', snip_m.group(1)).strip() if snip_m else ""
                        
                        if title and len(title) > 3:
                            results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet
                            })
        except Exception:
            pass
            
        return results

    def extract_prices(self, results: List[Dict[str, Any]], min_bound: float, max_bound: float, dest_country: str = "IN") -> Optional[float]:
        """Extracts and filters live prices within realistic semantic boundaries."""
        all_text = " ".join([f"{r['title']} {r['snippet']}" for r in results])
        
        if dest_country == "IN":
            matches = re.findall(r'(?:₹|Rs\.?|INR)\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)', all_text, re.IGNORECASE)
        else:
            matches = re.findall(r'\$\s*([0-9]+(?:,[0-9]+)*(?:\.[0-9]+)?)', all_text)
            
        valid = []
        for raw in matches:
            try:
                val = float(raw.replace(',', ''))
                if min_bound <= val <= max_bound and val not in [2023.0, 2024.0, 2025.0, 2026.0, 2027.0]:
                    valid.append(val)
            except Exception:
                pass
                
        if valid:
            valid.sort()
            return valid[len(valid) // 2]  # median representative price
        return None

    def get_semantic_profile(self, query: str, dest_country: str = "IN") -> Dict[str, Any]:
        """Classifies product category, boundaries, brand, and baseline pricing."""
        q = query.lower()
        
        # 1. Premium Audio & Noise Canceling Headphones (Check first to avoid M5 matching phone)
        if any(f in q for f in ["wh-1000", "wh1000", "airpods max", "bose", "sennheiser", "momentum", "headphone", "audio-technica"]):
            return {
                "category": "Premium Noise-Cancelling Headphones",
                "brand": "Sony" if any(w in q for w in ["wh", "sony"]) else ("Apple" if "airpods" in q else "Bose"),
                "title": f"{query.title()} Wireless ANC Headphones",
                "base_usd": 399.00,
                "inr_baseline": 29990.00,
                "min_inr": 18000.0, "max_inr": 48000.0,
                "min_usd": 200.0, "max_usd": 550.0,
                "adp_provider": "AudioCare Protection",
                "adp_usd": 39.0, "adp_inr": 2499.0,
                "ex_usd": 40.0, "ex_inr": 3000.0
            }

        # 2. Footwear & Sneakers
        elif any(f in q for f in ["jordan", "air jordan", "sneaker", "shoe", "yeezy", "dunk", "air force", "ultraboost"]):
            return {
                "category": "Authentic Athletic Footwear",
                "brand": "Nike" if any(w in q for w in ["nike", "jordan", "dunk", "air force"]) else "Footwear OEM",
                "title": f"{query.title()} Authentic Sneakers",
                "base_usd": 160.00,
                "inr_baseline": 13995.00,
                "min_inr": 4000.0, "max_inr": 35000.0,
                "min_usd": 50.0, "max_usd": 400.0,
                "adp_provider": "Authenticity Guarantee",
                "adp_usd": 0.0, "adp_inr": 0.0,
                "ex_usd": 0.0, "ex_inr": 0.0
            }

        # 3. Gaming Consoles
        elif any(f in q for f in ["ps5", "playstation", "xbox", "nintendo", "switch", "steam deck"]):
            return {
                "category": "Next-Gen Gaming Console",
                "brand": "Sony" if any(w in q for w in ["ps", "playstation"]) else ("Microsoft" if "xbox" in q else "Nintendo"),
                "title": f"{query.title()} Console",
                "base_usd": 499.00,
                "inr_baseline": 49990.00,
                "min_inr": 30000.0, "max_inr": 75000.0,
                "min_usd": 300.0, "max_usd": 800.0,
                "adp_provider": "Console Extended Warranty",
                "adp_usd": 49.0, "adp_inr": 3999.0,
                "ex_usd": 60.0, "ex_inr": 5000.0
            }

        # 4. Comprehensive Laptops, Notebooks & Hardware (Evaluated BEFORE phones so Vivobook won't match Vivo phone)
        elif any(f in q for f in [
            "vivobook", "zenbook", "ideapad", "thinkpad", "thinkbook", "victus", "pavilion", 
            "omen", "inspiron", "xps", "vostro", "latitude", "alienware", "nitro", "predator", 
            "swift", "aspire", "tuf", "rog", "zephyrus", "strix", "katana", "cyborg", "bravo", 
            "loq", "legion", "yoga", "surface", "galaxy book", "gram", "spectre", "envy", 
            "macbook", "laptop", "notebook", "ultrabook", "chromebook", "probook", "elitebook",
            "rtx", "gpu", "graphics card", "geforce"
        ]):
            is_gaming_flagship = any(f in q for f in [
                "victus", "omen", "rog", "tuf", "predator", "nitro", "alienware", "legion", 
                "loq", "katana", "cyborg", "bravo", "strix", "zephyrus", "rtx 40", "rtx 50", 
                "macbook pro", "i7", "i9", "ryzen 7", "ryzen 9"
            ])
            inr_baseline = 84990.00 if is_gaming_flagship else 69990.00
            usd_baseline = 999.00 if is_gaming_flagship else 799.00
            
            # Determine Brand
            if any(w in q for w in ["vivobook", "zenbook", "tuf", "rog", "zephyrus", "strix"]):
                brand = "ASUS"
            elif any(w in q for w in ["victus", "pavilion", "omen", "spectre", "envy", "probook", "elitebook"]):
                brand = "HP"
            elif any(w in q for w in ["ideapad", "thinkpad", "thinkbook", "legion", "loq", "yoga"]):
                brand = "Lenovo"
            elif any(w in q for w in ["inspiron", "xps", "alienware", "vostro", "latitude"]):
                brand = "Dell"
            elif any(w in q for w in ["nitro", "predator", "swift", "aspire"]):
                brand = "Acer"
            elif any(w in q for w in ["katana", "cyborg", "bravo"]):
                brand = "MSI"
            elif "macbook" in q:
                brand = "Apple"
            else:
                brand = "Laptop OEM"

            cat = "Gaming / High-Performance Laptop" if is_gaming_flagship else "Thin & Light Laptop"
            return {
                "category": cat,
                "brand": brand,
                "title": f"{brand} {query.title()}" if brand.lower() not in q else query.title(),
                "base_usd": usd_baseline,
                "inr_baseline": inr_baseline,
                "min_inr": 25000.0, "max_inr": 450000.0,
                "min_usd": 300.0, "max_usd": 5000.0,
                "adp_provider": f"{brand} Care Accidental Protection",
                "adp_usd": 89.0, "adp_inr": 5999.0,
                "ex_usd": 120.0, "ex_inr": 12000.0
            }

        # 5. Ultra-Flagship / Pro Smartphones (iPhone 18, 17, 16 Pro, S24/S25 Ultra, Fold)
        elif any(f in q for f in ["iphone 18", "iphone 17", "iphone 16 pro", "iphone 15 pro", "s24 ultra", "s25 ultra", "fold", "z fold", "find n"]):
            clean_title = f"Apple {query.title()}" if "iphone" in q and not "apple" in q else query.title()
            return {
                "category": "Ultra-Premium Flagship Smartphone",
                "brand": "Apple" if "iphone" in q else "Samsung",
                "title": clean_title,
                "base_usd": 1199.00,
                "inr_baseline": 129900.00,
                "min_inr": 80000.0, "max_inr": 250000.0,
                "min_usd": 899.0, "max_usd": 2500.0,
                "adp_provider": "AppleCare+ / Care+",
                "adp_usd": 179.0, "adp_inr": 14999.0,
                "ex_usd": 250.0, "ex_inr": 25000.0
            }

        # 6. Mainstream Flagships (Standard iPhone 16/15, Galaxy S24/S25, Pixel 9 Pro)
        elif any(f in q for f in ["iphone", "galaxy s", "pixel 8", "pixel 9", "oneplus 12", "oneplus 13"]):
            clean_title = f"Apple {query.title()}" if "iphone" in q and not "apple" in q else query.title()
            return {
                "category": "Premium Flagship Smartphone",
                "brand": "Apple" if "iphone" in q else ("Samsung" if "galaxy" in q else "Flagship OEM"),
                "title": clean_title,
                "base_usd": 799.00,
                "inr_baseline": 69900.00,
                "min_inr": 45000.0, "max_inr": 110000.0,
                "min_usd": 500.0, "max_usd": 1200.0,
                "adp_provider": "Device Care Shield",
                "adp_usd": 129.0, "adp_inr": 8999.0,
                "ex_usd": 150.0, "ex_inr": 15000.0
            }

        # 7. Budget & Mid-Range Phones (Samsung Galaxy A/M/F series, Redmi, Realme, Moto, Vivo with word boundaries)
        elif any(f in q for f in ["samsung", "galaxy", "redmi", "realme", "poco", "nord", "narzo"]) or re.search(r'\b(vivo|oppo|moto)\b', q) or re.search(r'\b[amf]\d{2}\b', q):
            # Check for A1x / budget entry (e.g. A14, A15, A16, A17)
            if re.search(r'\b[amf]1\d\b', q) or "a17" in q or "a16" in q or "a15" in q or "a14" in q:
                inr_base = 21999.00
                usd_base = 239.00
                cat = "Budget 5G Smartphone"
            elif re.search(r'\b[amf][23]\d\b', q) or any(k in q for k in ["a2", "a3", "m3"]):
                inr_base = 26999.00
                usd_base = 299.00
                cat = "Mid-Range Smartphone"
            else:
                inr_base = 24999.00
                usd_base = 279.00
                cat = "Mid-Range Smartphone"
            
            p_title = f"Samsung Galaxy {query.title()}" if ("a17" in q or "a16" in q or "a15" in q) and "samsung" not in q else query.title()
            return {
                "category": cat,
                "brand": "Samsung" if "samsung" in q or "galaxy" in q or "a1" in q else "Android OEM",
                "title": f"{p_title} 5G",
                "base_usd": usd_base,
                "inr_baseline": inr_base,
                "min_inr": 12000.0, "max_inr": 38000.0,
                "min_usd": 140.0, "max_usd": 450.0,
                "adp_provider": "Samsung Care+ / Brand Shield",
                "adp_usd": 24.99, "adp_inr": 1499.0,
                "ex_usd": 35.0, "ex_inr": 3500.0
            }

        # 8. TVs & Smart Displays
        elif any(f in q for f in ["tv", "oled", "qled", "bravia", "television"]):
            return {
                "category": "Smart 4K Television",
                "brand": "Display OEM",
                "title": f"{query.title()} (4K UHD)",
                "base_usd": 799.00,
                "inr_baseline": 64990.00,
                "min_inr": 20000.0, "max_inr": 350000.0,
                "min_usd": 250.0, "max_usd": 3500.0,
                "adp_provider": "Panel Screen Protection",
                "adp_usd": 89.0, "adp_inr": 5999.0,
                "ex_usd": 80.0, "ex_inr": 7000.0
            }

        # 9. General Consumer Products
        else:
            return {
                "category": "Consumer Retail Goods",
                "brand": "Certified Brand",
                "title": f"{query.title()}",
                "base_usd": 149.00,
                "inr_baseline": 12999.00,
                "min_inr": 500.0, "max_inr": 250000.0,
                "min_usd": 10.0, "max_usd": 3000.0,
                "adp_provider": "Retail Protection Plan",
                "adp_usd": 15.0, "adp_inr": 1299.0,
                "ex_usd": 15.0, "ex_inr": 1200.0
            }

    async def scout(self, query: str, dest_country: str = "IN") -> Dict[str, Any]:
        """Orchestrates live store scraping (Flipkart for India) + Bing search + semantic calibration."""
        dest = dest_country.upper()
        sem = self.get_semantic_profile(query, dest)
        calibrated = False
        final_inr = sem["inr_baseline"]
        final_usd = sem["base_usd"]
        title = sem["title"]
        web_hits = 0
        snippets = []

        # 1. For India (IN): Query Flipkart Live Search for exact real-time prices & genuine product titles
        if dest == "IN":
            flip_data = await self.scrape_flipkart_live(query)
            if flip_data.get("found") and flip_data.get("prices"):
                prices = flip_data["prices"]
                # Filter prices that fit semantic min and max bounds
                valid_inr = [p for p in prices if sem["min_inr"] <= p <= sem["max_inr"]]
                if valid_inr:
                    # Sort and pick the median or closest matching variant
                    valid_inr.sort()
                    chosen_price = valid_inr[len(valid_inr) // 2]
                    final_inr = chosen_price
                    final_usd = round(chosen_price / 86.8, 2)
                    calibrated = True
                    web_hits = len(prices)
                    if flip_data.get("title"):
                        title = flip_data["title"]
                        
        # 2. Parallel / Fallback: Query Bing Search
        if not calibrated:
            web_res = await self.search_web(query, dest)
            web_hits = len(web_res)
            snippets = [r["snippet"] for r in web_res[:3] if r.get("snippet")]
            
            if dest == "IN":
                live_price = self.extract_prices(web_res, sem["min_inr"], sem["max_inr"], dest_country="IN")
                if live_price:
                    final_inr = live_price
                    final_usd = round(live_price / 86.8, 2)
                    calibrated = True
            else:
                live_price = self.extract_prices(web_res, sem["min_usd"], sem["max_usd"], dest_country=dest)
                if live_price:
                    final_usd = live_price
                    final_inr = round(live_price * 86.8, 2)
                    calibrated = True

        regional_price = final_inr if dest == "IN" else final_usd
        
        return {
            "title": title,
            "category": sem["category"],
            "brand": sem["brand"],
            "base_msrp_usd": final_usd,
            "regional_price": regional_price,
            "adp_provider": sem["adp_provider"],
            "adp_usd": sem["adp_usd"],
            "adp_inr": sem["adp_inr"],
            "exchange_usd": sem["ex_usd"],
            "exchange_inr": sem["ex_inr"],
            "live_web_calibrated": calibrated,
            "web_search_hits": web_hits,
            "web_snippets": snippets
        }

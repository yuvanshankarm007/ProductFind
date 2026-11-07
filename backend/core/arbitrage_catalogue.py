"""
Commercial Arbitrage Catalogue, Workflow Presets, and Deterministic Price History Generator.
Seeded with multi-retailer inventory across Amazon, Flipkart, and OEM Direct for
combinatorial knapsack cart-splitting and algorithmic flash-dip detection.
"""

import random
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

WORKFLOW_PRESETS = [
    {
        "id": "wfh-50k",
        "name": "Ultimate WFH Setup under ₹50,000",
        "query": "WFH Setup under ₹50,000",
        "budget": 50000.0,
        "roles": ["Monitor", "Mechanical Keyboard", "Ergonomic Chair", "Webcam"],
        "description": "Ergonomic productivity suite with high-refresh display, tactile mechanical switches, and full lumbar support."
    },
    {
        "id": "podcast-pro",
        "name": "Podcasting & Streaming Studio Kit",
        "query": "Podcasting Kit",
        "budget": 35000.0,
        "roles": ["Studio Microphone", "Audio Interface", "Monitor Headphones", "Boom Arm"],
        "description": "Broadcast-grade cardioid vocal capture and zero-latency audio monitoring setup."
    },
    {
        "id": "gaming-rig",
        "name": "Esports High-FPS Gaming Peripherals",
        "query": "Gaming Rig Peripherals",
        "budget": 28000.0,
        "roles": ["Gaming Monitor", "Wireless Gaming Mouse", "RGB Mechanical Keyboard", "Spatial Audio Headset"],
        "description": "Sub-millisecond latency gaming peripherals with high-DPI optical sensor and rapid trigger keys."
    },
    {
        "id": "dev-dock",
        "name": "MacBook Developer Workstation Essentials",
        "query": "Developer Workstation",
        "budget": 45000.0,
        "roles": ["Thunderbolt 4 Dock", "NVMe 2TB High-Speed SSD", "Vertical Aluminum Stand", "4K Ultra-Clear Hub"],
        "description": "Multi-stream 40Gbps dock architecture, blazing 2800MB/s storage, and thermal cooling chassis."
    }
]

# Raw catalogue with cross-retailer listings, card offers, and verified metrics
CATALOGUE: List[Dict[str, Any]] = [
    # ---------------- MONITOR (WFH) ----------------
    {
        "id": "mon-lg-27-amz",
        "title": "LG 27UP650-W 27 Inch UHD 4K IPS HDR400 Monitor",
        "brand": "LG",
        "model": "27UP650-W",
        "category": "Monitor",
        "retailer": "Amazon",
        "base_price": 25999.0,
        "current_price": 23499.0,
        "original_mrp": 32000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.5,
        "review_count": 1820,
        "seller_name": "Appario Retail Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards", "5% Amazon Pay Cashback"]
    },
    {
        "id": "mon-lg-27-fk",
        "title": "LG 27 inch 4K Ultra HD IPS Monitor (27UP650-W)",
        "brand": "LG",
        "model": "27UP650-W",
        "category": "Monitor",
        "retailer": "Flipkart",
        "base_price": 26500.0,
        "current_price": 24200.0,
        "original_mrp": 32000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.4,
        "review_count": 940,
        "seller_name": "RetailNet Verified",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["10% Instant Discount on Axis Bank CC up to ₹1,250"]
    },
    {
        "id": "mon-lg-27-oem",
        "title": "LG UltraFine 27UP650-W 4K UHD Ergonomic Display",
        "brand": "LG",
        "model": "27UP650-W",
        "category": "Monitor",
        "retailer": "OEM Direct",
        "base_price": 28000.0,
        "current_price": 24999.0,
        "original_mrp": 32000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.7,
        "review_count": 310,
        "seller_name": "LG Electronics India Official",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
    },
    # ---------------- KEYBOARD (WFH) ----------------
    {
        "id": "kb-keychron-k2-amz",
        "title": "Keychron K2 Wireless Mechanical Keyboard (Version 2)",
        "brand": "Keychron",
        "model": "K2-V2",
        "category": "Mechanical Keyboard",
        "retailer": "Amazon",
        "base_price": 8499.0,
        "current_price": 7699.0,
        "original_mrp": 9999.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.6,
        "review_count": 1420,
        "seller_name": "Keychron India Authorised",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹500 Instant Discount with Amazon Pay ICICI"]
    },
    {
        "id": "kb-keychron-k2-fk",
        "title": "Keychron K2 Bluetooth Mechanical Keyboard with Gateron Brown",
        "brand": "Keychron",
        "model": "K2-V2",
        "category": "Mechanical Keyboard",
        "retailer": "Flipkart",
        "base_price": 8999.0,
        "current_price": 7999.0,
        "original_mrp": 9999.0,
        "shipping_cost": 40.0,
        "in_stock": True,
        "rating": 4.5,
        "review_count": 680,
        "seller_name": "TechArena Retail",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Special Bank Offer ₹300 Off"]
    },
    {
        "id": "kb-keychron-k2-oem",
        "title": "Keychron K2 Wireless Mechanical Keyboard - Official White LED",
        "brand": "Keychron",
        "model": "K2-V2",
        "category": "Mechanical Keyboard",
        "retailer": "OEM Direct",
        "base_price": 8199.0,
        "current_price": 7299.0,
        "original_mrp": 9499.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.8,
        "review_count": 520,
        "seller_name": "Keychron Official Direct",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Official Welcome Code - ₹400"]
    },
    # ---------------- ERGONOMIC CHAIR (WFH) ----------------
    {
        "id": "chair-green-amz",
        "title": "Green Soul Monster Ultimate Ergonomic High Back Chair",
        "brand": "Green Soul",
        "model": "Monster-Ultimate",
        "category": "Ergonomic Chair",
        "retailer": "Amazon",
        "base_price": 18490.0,
        "current_price": 16499.0,
        "original_mrp": 24990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.5,
        "review_count": 4200,
        "seller_name": "Green Soul Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1580481077195-c3a821a58875?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards"]
    },
    {
        "id": "chair-green-fk",
        "title": "Green Soul Monster Ultimate Fabric Ergonomic Gaming Chair",
        "brand": "Green Soul",
        "model": "Monster-Ultimate",
        "category": "Ergonomic Chair",
        "retailer": "Flipkart",
        "base_price": 18999.0,
        "current_price": 15999.0,
        "original_mrp": 24990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.6,
        "review_count": 2100,
        "seller_name": "FurnitureKart Retail",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1580481077195-c3a821a58875?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Axis Bank 10% Instant Discount up to ₹1,250"]
    },
    {
        "id": "chair-green-oem",
        "title": "Green Soul Monster Series Executive Pro Ergonomic Chair",
        "brand": "Green Soul",
        "model": "Monster-Ultimate",
        "category": "Ergonomic Chair",
        "retailer": "OEM Direct",
        "base_price": 19999.0,
        "current_price": 16999.0,
        "original_mrp": 25999.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.8,
        "review_count": 890,
        "seller_name": "Green Soul Official Store",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1580481077195-c3a821a58875?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
    },
    # ---------------- WEBCAM (WFH) ----------------
    {
        "id": "cam-logi-c920-amz",
        "title": "Logitech C920 Pro HD 1080p Webcam with Dual Microphones",
        "brand": "Logitech",
        "model": "C920-Pro",
        "category": "Webcam",
        "retailer": "Amazon",
        "base_price": 6495.0,
        "current_price": 4999.0,
        "original_mrp": 8995.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.6,
        "review_count": 8300,
        "seller_name": "Appario Retail Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Instant UPI Rebate ₹200"]
    },
    {
        "id": "cam-logi-c920-fk",
        "title": "Logitech C920 HD Pro USB Autofocus Webcam",
        "brand": "Logitech",
        "model": "C920-Pro",
        "category": "Webcam",
        "retailer": "Flipkart",
        "base_price": 6999.0,
        "current_price": 5299.0,
        "original_mrp": 8995.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.4,
        "review_count": 2800,
        "seller_name": "OmniTech India",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Special Bank Offer ₹300 Off"]
    },
    {
        "id": "cam-logi-c920-oem",
        "title": "Logitech C920 Commercial Certified Conference Webcam",
        "brand": "Logitech",
        "model": "C920-Pro",
        "category": "Webcam",
        "retailer": "OEM Direct",
        "base_price": 7200.0,
        "current_price": 5199.0,
        "original_mrp": 8995.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.7,
        "review_count": 450,
        "seller_name": "Logitech Official India",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Official Welcome Code - ₹400"]
    },
    # ---------------- PODCASTING STUDIO ----------------
    {
        "id": "mic-shure-amz",
        "title": "Shure MV7X XLR Dynamic Broadcast Studio Microphone",
        "brand": "Shure",
        "model": "MV7X",
        "category": "Studio Microphone",
        "retailer": "Amazon",
        "base_price": 19500.0,
        "current_price": 16999.0,
        "original_mrp": 22000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.8,
        "review_count": 1600,
        "seller_name": "Sun Infonet Shure Partner",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards"]
    },
    {
        "id": "mic-shure-fk",
        "title": "Shure MV7X Podcast Dynamic Vocal Microphone",
        "brand": "Shure",
        "model": "MV7X",
        "category": "Studio Microphone",
        "retailer": "Flipkart",
        "base_price": 19800.0,
        "current_price": 17400.0,
        "original_mrp": 22000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.7,
        "review_count": 480,
        "seller_name": "ProAudio India",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["10% Instant Discount on Axis Bank CC up to ₹1,250"]
    },
    {
        "id": "mic-shure-oem",
        "title": "Shure MV7X Professional Podcast Dynamic Microphone",
        "brand": "Shure",
        "model": "MV7X",
        "category": "Studio Microphone",
        "retailer": "OEM Direct",
        "base_price": 20500.0,
        "current_price": 17200.0,
        "original_mrp": 22500.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.9,
        "review_count": 320,
        "seller_name": "Shure Authorized India Store",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1590602847861-f357a9332bbc?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
    },
    {
        "id": "interface-focusrite-amz",
        "title": "Focusrite Scarlett 2i2 4th Gen USB Audio Interface",
        "brand": "Focusrite",
        "model": "Scarlett-2i2-Gen4",
        "category": "Audio Interface",
        "retailer": "Amazon",
        "base_price": 18200.0,
        "current_price": 15499.0,
        "original_mrp": 21990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.7,
        "review_count": 2100,
        "seller_name": "Appario Pro Sound",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards"]
    },
    {
        "id": "interface-focusrite-fk",
        "title": "Focusrite Scarlett 2i2 USB-C 2-In/2-Out Studio Audio Interface",
        "brand": "Focusrite",
        "model": "Scarlett-2i2-Gen4",
        "category": "Audio Interface",
        "retailer": "Flipkart",
        "base_price": 18500.0,
        "current_price": 15999.0,
        "original_mrp": 21990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.6,
        "review_count": 590,
        "seller_name": "SoundHub Retail",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Axis Bank 10% Instant Discount up to ₹1,250"]
    },
    {
        "id": "interface-focusrite-oem",
        "title": "Focusrite Official Scarlett 2i2 4th Generation Audio Interface",
        "brand": "Focusrite",
        "model": "Scarlett-2i2-Gen4",
        "category": "Audio Interface",
        "retailer": "OEM Direct",
        "base_price": 19000.0,
        "current_price": 15800.0,
        "original_mrp": 22000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.8,
        "review_count": 290,
        "seller_name": "Focusrite India Direct",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
    },
    # ---------------- HEADPHONES (MONITOR & SONY) ----------------
    {
        "id": "sony-xm5-amz",
        "title": "Sony WH-1000XM5 Wireless Industry Leading Noise Canceling Headphones",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "category": "Monitor Headphones",
        "retailer": "Amazon",
        "base_price": 31990.0,
        "current_price": 26990.0,
        "original_mrp": 34990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.6,
        "review_count": 5200,
        "seller_name": "Appario Retail Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards", "5% Amazon Pay Cashback"]
    },
    {
        "id": "sony-xm5-fk",
        "title": "Sony WH-1000XM5 Bluetooth Headset with Mic & Auto NC Optimizer",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "category": "Monitor Headphones",
        "retailer": "Flipkart",
        "base_price": 32990.0,
        "current_price": 27490.0,
        "original_mrp": 34990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.5,
        "review_count": 3100,
        "seller_name": "RetailNet Verified",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["10% Instant Discount on Axis Bank CC up to ₹1,250"]
    },
    {
        "id": "sony-xm5-oem",
        "title": "Sony Center Flagship WH-1000XM5 Wireless Noise Cancelling Headphones",
        "brand": "Sony",
        "model": "WH-1000XM5",
        "category": "Monitor Headphones",
        "retailer": "OEM Direct",
        "base_price": 34990.0,
        "current_price": 28990.0,
        "original_mrp": 34990.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.9,
        "review_count": 820,
        "seller_name": "Sony Center Official India",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
    },
    # ---------------- GAMING RIG ----------------
    {
        "id": "gaming-mon-acer-amz",
        "title": "Acer Nitro VG270 S 27 Inch Full HD 165Hz Fast IPS Gaming Monitor",
        "brand": "Acer",
        "model": "Nitro-VG270S",
        "category": "Gaming Monitor",
        "retailer": "Amazon",
        "base_price": 14999.0,
        "current_price": 11999.0,
        "original_mrp": 18500.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.4,
        "review_count": 3400,
        "seller_name": "Appario Retail Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹500 Instant Discount on Bank Cards"]
    },
    {
        "id": "gaming-mon-acer-fk",
        "title": "Acer Nitro 27 inch Full HD IPS 165Hz Gaming Monitor",
        "brand": "Acer",
        "model": "Nitro-VG270S",
        "category": "Gaming Monitor",
        "retailer": "Flipkart",
        "base_price": 15500.0,
        "current_price": 12499.0,
        "original_mrp": 18500.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.3,
        "review_count": 1800,
        "seller_name": "SuperComNet",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Special Bank Offer ₹300 Off"]
    },
    {
        "id": "gaming-mouse-logi-amz",
        "title": "Logitech G304 Lightspeed Wireless Optical Gaming Mouse",
        "brand": "Logitech",
        "model": "G304-Lightspeed",
        "category": "Wireless Gaming Mouse",
        "retailer": "Amazon",
        "base_price": 3295.0,
        "current_price": 2495.0,
        "original_mrp": 3795.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.5,
        "review_count": 9400,
        "seller_name": "Appario Retail Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Instant UPI Rebate ₹200"]
    },
    {
        "id": "gaming-mouse-logi-fk",
        "title": "Logitech G304 Wireless Gaming Mouse HERO Sensor",
        "brand": "Logitech",
        "model": "G304-Lightspeed",
        "category": "Wireless Gaming Mouse",
        "retailer": "Flipkart",
        "base_price": 3400.0,
        "current_price": 2595.0,
        "original_mrp": 3795.0,
        "shipping_cost": 40.0,
        "in_stock": True,
        "rating": 4.4,
        "review_count": 4200,
        "seller_name": "RetailNet Verified",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Special Bank Offer ₹300 Off"]
    },
    # ---------------- DEVELOPER WORKSTATION ----------------
    {
        "id": "dock-caldigit-amz",
        "title": "CalDigit TS4 Thunderbolt 4 Dock 18-in-1 Power Delivery 98W",
        "brand": "CalDigit",
        "model": "TS4-TB4",
        "category": "Thunderbolt 4 Dock",
        "retailer": "Amazon",
        "base_price": 42000.0,
        "current_price": 36990.0,
        "original_mrp": 46000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.7,
        "review_count": 920,
        "seller_name": "CalDigit Authorized Partner",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards"]
    },
    {
        "id": "dock-caldigit-oem",
        "title": "CalDigit TS4 Thunderbolt 4 Station - 18 Ports 8K Display",
        "brand": "CalDigit",
        "model": "TS4-TB4",
        "category": "Thunderbolt 4 Dock",
        "retailer": "OEM Direct",
        "base_price": 44000.0,
        "current_price": 37500.0,
        "original_mrp": 46000.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.9,
        "review_count": 180,
        "seller_name": "CalDigit Official Direct",
        "is_prime_or_plus": False,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1544652478-6653e09f18a2?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
    },
    {
        "id": "ssd-samsung-990-amz",
        "title": "Samsung 990 PRO 2TB PCIe 4.0 M.2 NVMe Internal SSD",
        "brand": "Samsung",
        "model": "990-PRO-2TB",
        "category": "NVMe 2TB High-Speed SSD",
        "retailer": "Amazon",
        "base_price": 19999.0,
        "current_price": 16499.0,
        "original_mrp": 24999.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.8,
        "review_count": 7800,
        "seller_name": "Appario Retail Direct",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["₹1,500 Instant Discount on HDFC Cards"]
    },
    {
        "id": "ssd-samsung-990-fk",
        "title": "Samsung 990 Pro 2 TB NVMe M.2 Internal Solid State Drive",
        "brand": "Samsung",
        "model": "990-PRO-2TB",
        "category": "NVMe 2TB High-Speed SSD",
        "retailer": "Flipkart",
        "base_price": 20500.0,
        "current_price": 16999.0,
        "original_mrp": 24999.0,
        "shipping_cost": 0.0,
        "in_stock": True,
        "rating": 4.7,
        "review_count": 2200,
        "seller_name": "RetailNet Verified",
        "is_prime_or_plus": True,
        "is_accessory_only": False,
        "is_sponsored": False,
        "is_refurbished": False,
        "packaging_seal_intact": True,
        "image_url": "https://images.unsplash.com/photo-1597872200969-2b65d56bd16b?w=500&auto=format&fit=crop&q=60",
        "card_offers": ["Axis Bank 10% Instant Discount up to ₹1,250"]
    }
]

class PricePoint(BaseModel):
    timestamp: str
    price: float
    retailer: str
    event_label: Optional[str] = None


def get_listings_for_workflow(query: str, items_list: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Return matching listings for a query or custom items list from our seeded catalogue,
    or dynamically synthesize high-fidelity multi-retailer listings for custom bundle items.
    """
    # 0. Check if explicit items_list provided or comma-separated query
    explicit_items = []
    if items_list:
        explicit_items = [it.strip() for it in items_list if it and it.strip()]
    elif query and "," in query:
        parts = [s.strip() for s in query.split(",") if s.strip()]
        if len(parts) >= 2:
            explicit_items = parts

    if explicit_items:
        collected: List[Dict[str, Any]] = []
        for idx, item_name in enumerate(explicit_items):
            item_q = item_name.lower().strip()
            # Try to find matching listings in CATALOGUE by category or keyword
            matched_for_item = []
            
            # Category keyword aliases
            category_aliases = {
                "gaming monitor": "Gaming Monitor",
                "monitor": "Monitor",
                "display": "Monitor",
                "screen": "Monitor",
                "keyboard": "Mechanical Keyboard",
                "chair": "Ergonomic Chair",
                "webcam": "Webcam",
                "camera": "Webcam",
                "mic": "Studio Microphone",
                "microphone": "Studio Microphone",
                "interface": "Audio Interface",
                "headphone": "Monitor Headphones",
                "headphones": "Monitor Headphones",
                "headset": "Monitor Headphones",
                "mouse": "Wireless Gaming Mouse",
                "dock": "Thunderbolt 4 Dock",
                "hub": "Thunderbolt 4 Dock",
                "ssd": "NVMe 2TB High-Speed SSD",
                "nvme": "NVMe 2TB High-Speed SSD",
                "storage": "NVMe 2TB High-Speed SSD"
            }
            
            best_cat = None
            for alias_key, cat_name in category_aliases.items():
                if alias_key in item_q:
                    best_cat = cat_name
                    break

            if best_cat:
                matched_for_item = [item for item in CATALOGUE if item["category"].lower() == best_cat.lower()]

            if not matched_for_item:
                # Direct match in catalogue
                matched_for_item = [
                    item for item in CATALOGUE
                    if (item_q in item["title"].lower() or
                        item_q in item["category"].lower() or
                        any(word in item["title"].lower() for word in item_q.split() if len(word) > 2))
                ]

            if matched_for_item:
                # Map listings to this slot using item_name as category
                for base_item in matched_for_item:
                    c = dict(base_item)
                    c["category"] = item_name
                    c["id"] = f"{base_item['id']}-{idx}-{hashlib.md5(item_name.encode()).hexdigest()[:4]}"
                    collected.append(c)
            else:
                # Dynamically synthesize 3 verified listings (Amazon, Flipkart, OEM Direct)
                slug = hashlib.md5(item_name.encode()).hexdigest()[:6]
                est_price = 3500.0
                if any(k in item_q for k in ["monitor", "display", "screen", "desk", "table"]):
                    est_price = 18000.0
                elif any(k in item_q for k in ["chair", "ergonomic", "seat"]):
                    est_price = 14000.0
                elif any(k in item_q for k in ["keyboard", "dock", "mic", "microphone", "headphone"]):
                    est_price = 6500.0
                elif any(k in item_q for k in ["webcam", "camera", "cam", "mouse", "light", "lamp"]):
                    est_price = 3200.0
                elif any(k in item_q for k in ["mat", "pad", "stand", "cable", "hub", "arm", "holder"]):
                    est_price = 1499.0

                synth_listings = [
                    {
                        "id": f"syn-{slug}-amz",
                        "title": f"Verified {item_name} (High Durability Edition)",
                        "brand": "ProEcosystem",
                        "model": f"{item_name} Edition",
                        "category": item_name,
                        "retailer": "Amazon",
                        "base_price": round(est_price * 1.05, 2),
                        "current_price": round(est_price * 0.94, 2),
                        "original_mrp": round(est_price * 1.30, 2),
                        "shipping_cost": 0.0,
                        "in_stock": True,
                        "rating": 4.6,
                        "review_count": 640,
                        "seller_name": "Appario Retail Direct",
                        "is_prime_or_plus": True,
                        "is_accessory_only": False,
                        "is_sponsored": False,
                        "is_refurbished": False,
                        "packaging_seal_intact": True,
                        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
                        "card_offers": ["₹1,500 Instant Discount on HDFC Cards", "5% Amazon Pay Cashback"]
                    },
                    {
                        "id": f"syn-{slug}-fk",
                        "title": f"Official {item_name} (Certified Fast-Delivery)",
                        "brand": "ProEcosystem",
                        "model": f"{item_name} Edition",
                        "category": item_name,
                        "retailer": "Flipkart",
                        "base_price": round(est_price * 1.08, 2),
                        "current_price": round(est_price * 0.92, 2),
                        "original_mrp": round(est_price * 1.30, 2),
                        "shipping_cost": 0.0,
                        "in_stock": True,
                        "rating": 4.5,
                        "review_count": 510,
                        "seller_name": "RetailNet Verified",
                        "is_prime_or_plus": True,
                        "is_accessory_only": False,
                        "is_sponsored": False,
                        "is_refurbished": False,
                        "packaging_seal_intact": True,
                        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
                        "card_offers": ["10% Instant Discount on Axis Bank CC up to ₹1,250"]
                    },
                    {
                        "id": f"syn-{slug}-oem",
                        "title": f"Factory Direct {item_name} (OEM Genuine)",
                        "brand": "ProEcosystem",
                        "model": f"{item_name} Edition",
                        "category": item_name,
                        "retailer": "OEM Direct",
                        "base_price": round(est_price * 1.15, 2),
                        "current_price": round(est_price * 0.96, 2),
                        "original_mrp": round(est_price * 1.30, 2),
                        "shipping_cost": 0.0,
                        "in_stock": True,
                        "rating": 4.8,
                        "review_count": 280,
                        "seller_name": "ProEcosystem Official Direct",
                        "is_prime_or_plus": False,
                        "is_accessory_only": False,
                        "is_sponsored": False,
                        "is_refurbished": False,
                        "packaging_seal_intact": True,
                        "image_url": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop&q=60",
                        "card_offers": ["OEM Direct Exclusive Brand Rebate ₹1,000"]
                    }
                ]
                collected.extend(synth_listings)

        if collected:
            return collected

    q = query.lower().strip()
    q_norm = q.replace("₹", "").replace("rs.", "").replace("rs", "").replace("inr", "").replace(",", "").strip()
    
    # 1. Exact preset matching (by preset ID, query string, or explicit workflow keywords)
    is_workflow_query = any(w in q for w in ["setup", "kit", "rig", "essentials", "workflow", "workstation", "studio", "peripherals", "wfh", "bundle", "bulk"])
    if is_workflow_query:
        if "wfh" in q or "work from home" in q:
            return [item for item in CATALOGUE if item["category"] in WORKFLOW_PRESETS[0]["roles"]]
        if "podcast" in q or "streaming" in q:
            return [item for item in CATALOGUE if item["category"] in WORKFLOW_PRESETS[1]["roles"]]
        if "gaming" in q or "esports" in q or "fps" in q:
            return [item for item in CATALOGUE if item["category"] in WORKFLOW_PRESETS[2]["roles"]]
        if "macbook" in q or "developer" in q or "workstation" in q or "dock" in q:
            return [item for item in CATALOGUE if item["category"] in WORKFLOW_PRESETS[3]["roles"]]

        for preset in WORKFLOW_PRESETS:
            p_q = preset["query"].lower().replace("₹", "").replace(",", "").strip()
            p_n = preset["name"].lower().replace("₹", "").replace(",", "").strip()
            if (preset["id"] in q or 
                p_q in q_norm or 
                p_n in q_norm or
                all(word in q for word in preset["name"].lower().split() if len(word) > 4)):
                results = [item for item in CATALOGUE if item["category"] in preset["roles"]]
                if results:
                    return results

    # 2. Check if the user query is explicitly targeting one known category/role
    category_matches = [item for item in CATALOGUE if item["category"].lower() == q or q in item["category"].lower()]
    if category_matches:
        return category_matches

    # 3. Direct keyword search across title, brand, model, category
    matched = []
    for item in CATALOGUE:
        if (q in item["title"].lower() or 
            q in item["brand"].lower() or 
            q in item["model"].lower() or 
            q in item["category"].lower() or
            any(word in item["title"].lower() for word in q.split() if len(word) > 2)):
            matched.append(item)
            
    if not matched:
        # Fallback to WFH items to never leave user with an empty screen
        return [item for item in CATALOGUE if item["category"] in ["Monitor", "Mechanical Keyboard", "Ergonomic Chair", "Webcam"]]
        
    return matched


def generate_mock_price_history(item_id: str, base_price: float, retailer: str) -> List[PricePoint]:
    """Generates a realistic, deterministic 30-day temporal price curve with algorithmic flash dips."""
    history: List[PricePoint] = []
    now = datetime.now()
    
    # Deterministic seed based on item_id and retailer
    seed_str = f"{item_id}:{retailer}"
    seed_val = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed_val)
    
    # 30 days of data points
    current = base_price * 1.04
    for day in range(30, 0, -1):
        point_time = now - timedelta(days=day)
        fluctuation = rng.uniform(-0.035, 0.035)
        current = max(base_price * 0.75, current * (1.0 + fluctuation))
        
        # Inject an algorithmic flash dip 2 days ago for certain items
        event = None
        if day == 2 and any(k in item_id for k in ["sony", "mon-lg", "caldigit", "acer", "mouse-logi"]):
            current = base_price * 0.82  # 18% flash dip
            event = "Algorithmic Pricing Dip (Triggered)"
        elif day == 15 and rng.random() > 0.45:
            current = base_price * 0.89
            event = "Weekend Flash Sale"
            
        history.append(PricePoint(
            timestamp=point_time.strftime("%Y-%m-%d %H:%M"),
            price=round(current, 2),
            retailer=retailer,
            event_label=event
        ))
        
    # Append current latest
    history.append(PricePoint(
        timestamp=now.strftime("%Y-%m-%d %H:%M"),
        price=round(base_price, 2),
        retailer=retailer,
        event_label="Current Active Price"
    ))
    return history

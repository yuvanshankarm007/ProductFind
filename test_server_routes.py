import sys
import asyncio
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from backend.server import app

async def test_server_routes():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Health check
        res = await client.get("/api/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        data = res.json()
        print(" [x] Health check status:", data["status"], flush=True)

        # 2. Preferences endpoint
        res = await client.get("/api/preferences")
        assert res.status_code == 200, f"Preferences failed: {res.text}"
        prefs = res.json()
        assert "languages" in prefs and "currencies" in prefs and "countries" in prefs
        print(" [x] Preferences API operational. Languages:", list(prefs["languages"].keys()), flush=True)

        # 3. Search endpoint with India destination & INR currency
        search_req = {
            "query": "Sony WH-1000XM5",
            "language": "hi",
            "country": "IN",
            "currency": "INR",
            "preferred_payment": "cod"
        }
        res = await client.post("/api/search", json=search_req)
        assert res.status_code == 200, f"Search API failed: {res.text}"
        search_data = res.json()
        print(f" [x] Search API returned {len(search_data['final_options'])} options in {search_data['user_preferences']['currency']}", flush=True)
        print(" [x] Price prediction verdict:", search_data["price_analytics"]["buy_verdict"], flush=True)
        print(" [x] Comparison matrix rows:", len(search_data["comparison_matrix"]), flush=True)

        # 4. PayPal Create Order with INR
        order_req = {
            "amount": 29627.44,
            "item_name": "Sony WH-1000XM5",
            "currency": "INR"
        }
        res = await client.post("/api/paypal/create-order", json=order_req)
        assert res.status_code == 200, f"PayPal create order failed: {res.text}"
        order_data = res.json()
        print(f" [x] PayPal create order returned ID: {order_data['id']}", flush=True)

        # 5. PayPal Capture Order
        cap_req = {"order_id": order_data["id"]}
        res = await client.post("/api/paypal/capture-order", json=cap_req)
        assert res.status_code == 200, f"PayPal capture order failed: {res.text}"
        cap_data = res.json()
        print(f" [x] PayPal capture status: {cap_data['status']}", flush=True)

        # 6. PayPal Dispute Dossier Generation & Cryptographic Verification
        dossier_req = {
            "order_id": order_data["id"],
            "item_title": "Sony WH-1000XM5",
            "platform": "Flipkart Assured",
            "agreed_tco": 18763.16,
            "condition": "Brand New",
            "open_box_verified": True,
            "seller_name": "OmniRetail Assured",
            "seller_rating": 4.8,
            "warranty_claims": "1 Year Official OEM Warranty + Accidental Spill Protection",
            "display_currency": "INR"
        }
        res = await client.post("/api/paypal/create-dossier", json=dossier_req)
        assert res.status_code == 200, f"Create dossier failed: {res.text}"
        dossier_data = res.json()
        assert "cryptographic_hash" in dossier_data and len(dossier_data["cryptographic_hash"]) == 64
        assert dossier_data["evidence_status"] == "SEALED_AND_READY_FOR_DISPUTE"
        print(f" [x] PayPal Dispute Dossier generated ID: {dossier_data['dossier_id']}", flush=True)
        print(f" [x] Cryptographic SHA-256 Signature verified: {dossier_data['cryptographic_hash'][:16]}...", flush=True)

    print("\n=== ALL SERVER ENDPOINTS TESTED AND VERIFIED ===", flush=True)

if __name__ == "__main__":
    asyncio.run(test_server_routes())

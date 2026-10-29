"""
FastAPI Server & WebSocket Streaming Gateway for ProductFind / PayPal Sentinel AI.
Hosts the agent orchestration, PayPal developer API endpoints, multi-currency FX service,
and real-time event bus.
"""

import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any

from .core.bus import EventBus
from .coordinator import SentinelCoordinator
from .paypal_service import PayPalService
from .agents.fx_service import BASE_RATES_USD, CURRENCY_SYMBOLS
from .core.i18n import SUPPORTED_LANGUAGES

app = FastAPI(
    title="ProductFind AI",
    description="Bidirectional Multi-Agent Commerce Agent with PayPal Buyer Protection & Pay Later Integration",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import FileResponse, Response

# Global instances
global_bus = EventBus()
coordinator = SentinelCoordinator(global_bus)
paypal_svc = PayPalService()

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "public", "favicon.svg")
    if os.path.exists(fav_path):
        return FileResponse(fav_path, media_type="image/svg+xml")
    return Response(status_code=204)

class SearchRequest(BaseModel):
    query: str
    language: Optional[str] = "en"
    country: Optional[str] = "US"
    currency: Optional[str] = "USD"
    preferred_payment: Optional[str] = "all"
    session_id: Optional[str] = "web-sess"

class CreateOrderRequest(BaseModel):
    amount: float
    item_name: str
    currency: Optional[str] = "USD"

class CaptureOrderRequest(BaseModel):
    order_id: str

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ProductFind Sentinel Multi-Agent Swarm",
        "paypal_mode": "Sandbox" if "demo" in paypal_svc.client_id else "Live Sandbox API",
        "features": [
            "Bidirectional Agent Graph",
            "Multi-Language i18n",
            "Cross-Border FX & Import Duty Inspector",
            "Cash on Delivery & Open Box Delivery Verifier",
            "Exchange Offer Evaluator",
            "Price History & 14-Day Prediction Engine",
            "Side-by-Side Comparison Matrix",
            "PayPal Buyer Protection & Pay Later"
        ]
    }

@app.get("/api/preferences")
async def get_preferences():
    """Returns available localized preferences."""
    return {
        "languages": SUPPORTED_LANGUAGES,
        "countries": {
            "US": "United States 🇺🇸",
            "IN": "India 🇮🇳",
            "GB": "United Kingdom 🇬🇧",
            "DE": "Germany 🇩🇪",
            "CA": "Canada 🇨🇦",
            "JP": "Japan 🇯🇵",
            "AU": "Australia 🇦🇺"
        },
        "currencies": {
            curr: {"symbol": sym, "rate_to_usd": BASE_RATES_USD.get(curr, 1.0)}
            for curr, sym in CURRENCY_SYMBOLS.items()
        },
        "payment_methods": {
            "all": "All Payment Methods",
            "paypal": "PayPal & Pay Later (Pay in 4)",
            "cod": "Cash on Delivery (COD)",
            "card": "Credit / Debit Card",
            "upi": "UPI / Net Banking"
        }
    }

@app.post("/api/search")
async def api_search(req: SearchRequest):
    """Trigger agent swarm search via HTTP."""
    global_bus.clear()
    state = await coordinator.execute_search(
        query=req.query,
        language=req.language or "en",
        country=req.country or "US",
        currency=req.currency or "USD",
        preferred_payment=req.preferred_payment or "all",
        session_id=req.session_id or "web-sess"
    )
    return state.model_dump()

@app.post("/api/paypal/create-order")
async def api_create_order(req: CreateOrderRequest):
    """Generate PayPal v2 Order in requested currency."""
    try:
        order = await paypal_svc.create_order(
            amount=req.amount,
            item_name=req.item_name,
            currency=req.currency or "USD"
        )
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paypal/capture-order")
async def api_capture_order(req: CaptureOrderRequest):
    """Capture PayPal Order."""
    try:
        capture = await paypal_svc.capture_order(order_id=req.order_id)
        return capture
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/negotiate")
async def websocket_endpoint(websocket: WebSocket):
    """Full-duplex WebSocket for streaming live inter-agent negotiations."""
    await websocket.accept()
    q = global_bus.subscribe()

    consumer_task = None

    async def event_forwarder():
        try:
            while True:
                event = await q.get()
                await websocket.send_text(json.dumps({
                    "type": "AGENT_EVENT",
                    "event": event.model_dump()
                }))
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    consumer_task = asyncio.create_task(event_forwarder())

    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            action = data.get("action")

            if action == "search":
                query = data.get("query", "Sony WH-1000XM5")
                language = data.get("language", "en")
                country = data.get("country", "US")
                currency = data.get("currency", "USD")
                preferred_payment = data.get("preferred_payment", "all")
                session_id = data.get("session_id", "ws-session")
                
                # Execute swarm in background and stream results
                async def run_swarm():
                    global_bus.clear()
                    state = await coordinator.execute_search(
                        query=query,
                        language=language,
                        country=country,
                        currency=currency,
                        preferred_payment=preferred_payment,
                        session_id=session_id
                    )
                    await websocket.send_text(json.dumps({
                        "type": "FINAL_RESULT",
                        "state": state.model_dump()
                    }))

                asyncio.create_task(run_swarm())

    except WebSocketDisconnect:
        pass
    finally:
        if consumer_task:
            consumer_task.cancel()
        global_bus.unsubscribe(q)

# Mount frontend build or public assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "public")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)


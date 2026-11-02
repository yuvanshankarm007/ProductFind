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
from .paypal_service import PayPalService, PayPalEvidenceSentinel
from .agents.fx_service import BASE_RATES_USD, CURRENCY_SYMBOLS
from .core.i18n import SUPPORTED_LANGUAGES
from .schemas import RiskPreferences, DisputeDossier
from .agents.adaptive_skill_learner import AdaptiveSkillLearner, SkillVault, AdaptiveSkill
from .core.gcp_db import gcp_db_service

import socket
import threading
from contextlib import asynccontextmanager

_relay_started = False
_relay_lock = threading.Lock()

def start_ipv6_loopback_relay(port: int = 8000) -> None:
    """
    Seamless IPv6 loopback relay listening on [::1]:port that proxies to 127.0.0.1:port.
    Resolves the Windows Chromium/Brave localhost binding issue where Chrome/Brave queries [::1] first
    and raises ERR_CONNECTION_REFUSED when Uvicorn is bound to IPv4 0.0.0.0.
    """
    global _relay_started
    with _relay_lock:
        if _relay_started:
            return
        _relay_started = True

    def handle_client(client_sock: socket.socket):
        target = None
        try:
            target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target.settimeout(5.0)
            target.connect(('127.0.0.1', port))
            target.settimeout(None)
            client_sock.settimeout(None)

            def pipe(src, dst):
                try:
                    while True:
                        d = src.recv(16384)
                        if not d:
                            break
                        dst.sendall(d)
                except Exception:
                    pass
                finally:
                    try:
                        dst.shutdown(socket.SHUT_WR)
                    except Exception:
                        pass

            t1 = threading.Thread(target=pipe, args=(client_sock, target), daemon=True)
            t2 = threading.Thread(target=pipe, args=(target, client_sock), daemon=True)
            t1.start()
            t2.start()

            def cleanup():
                t1.join(timeout=30)
                t2.join(timeout=30)
                try: client_sock.close()
                except Exception: pass
                if target:
                    try: target.close()
                    except Exception: pass

            threading.Thread(target=cleanup, daemon=True).start()
        except Exception:
            try: client_sock.close()
            except Exception: pass
            if target:
                try: target.close()
                except Exception: pass

    def server_loop():
        try:
            srv = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(('::1', port))
            srv.listen(100)
            print(f"[IPv6 Relay] Seamless loopback relay active: [::1]:{port} -> 127.0.0.1:{port}")
            while True:
                client_sock, _ = srv.accept()
                threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
        except Exception as e:
            print(f"[IPv6 Relay] Info: {e}")

    threading.Thread(target=server_loop, daemon=True).start()

@asynccontextmanager
async def lifespan(app: FastAPI):
    port = int(os.getenv("PORT", 8000))
    start_ipv6_loopback_relay(port)
    yield

app = FastAPI(
    title="ProductFind AI",
    description="Bidirectional Multi-Agent Commerce Agent with PayPal Buyer Protection & Pay Later Integration",
    version="2.0.0",
    lifespan=lifespan
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
skill_vault = SkillVault()
skill_learner = AdaptiveSkillLearner(skill_vault)

class LearnSkillRequest(BaseModel):
    domain: str
    content: Optional[str] = ""
    country: Optional[str] = "US"
    currency: Optional[str] = "USD"

@app.get("/api/skills")
async def list_skills():
    """Lists all autonomously acquired merchant and policy evaluation skills."""
    skills = skill_vault.list_skills()
    return {
        "count": len(skills),
        "skills": [s.model_dump() for s in skills]
    }

@app.get("/api/skills/{domain}")
async def get_skill(domain: str):
    """Retrieves an autonomous skill by merchant domain."""
    skill = skill_vault.get_skill(domain)
    if not skill:
        raise HTTPException(status_code=404, detail=f"No skill acquired for domain '{domain}'")
    return skill.model_dump()

@app.post("/api/skills/learn")
async def learn_skill(req: LearnSkillRequest):
    """
    On-demand autonomous skill acquisition for any novel e-commerce merchant.
    """
    skill = skill_learner.discover_and_learn_merchant(
        domain=req.domain,
        page_html_or_text=req.content or f"{req.domain} online store return policy 14 days warranty",
        country=req.country,
        currency=req.currency
    )
    return {
        "status": "success",
        "message": f"Autonomously synthesized and verified skill for '{skill.merchant_name}'",
        "skill": skill.model_dump()
    }

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
    warranty_priority: Optional[float] = 0.5
    speed_priority: Optional[float] = 0.5
    trust_tolerance: Optional[float] = 0.7

class CreateOrderRequest(BaseModel):
    amount: float
    item_name: str
    currency: Optional[str] = "USD"

class CaptureOrderRequest(BaseModel):
    order_id: str

class CreateDossierRequest(BaseModel):
    order_id: str
    item_title: str
    platform: str
    agreed_tco: float
    condition: Optional[str] = "Brand New"
    open_box_verified: Optional[bool] = False
    seller_name: Optional[str] = "Authorized Partner"
    seller_rating: Optional[float] = 4.5
    warranty_claims: Optional[str] = "1-Year OEM Coverage"
    display_currency: Optional[str] = "USD"

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ProductFind Sentinel Multi-Agent Swarm",
        "paypal_mode": "Sandbox" if "demo" in paypal_svc.client_id else "Live Sandbox API",
        "database": gcp_db_service.get_status(),
        "features": [
            "Bidirectional Agent Graph",
            "Multi-Language i18n",
            "Cross-Border FX & Import Duty Inspector",
            "Cash on Delivery & Open Box Delivery Verifier",
            "Exchange Offer Evaluator",
            "Price History & 14-Day Prediction Engine",
            "Side-by-Side Comparison Matrix",
            "PayPal Buyer Protection & Pay Later",
            "Google Cloud Firestore Native Persistence",
            "Memorystore Low-Latency Trajectory Cache"
        ]
    }

@app.get("/api/database/status")
async def get_db_status():
    """Returns cloud database and cache connectivity and telemetry."""
    return gcp_db_service.get_status()

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
    """Trigger agent swarm search via HTTP with dynamic risk preferences."""
    risk_prefs = RiskPreferences(
        warranty_priority=req.warranty_priority if req.warranty_priority is not None else 0.5,
        speed_priority=req.speed_priority if req.speed_priority is not None else 0.5,
        trust_tolerance=req.trust_tolerance if req.trust_tolerance is not None else 0.7,
    )
    state = await coordinator.execute_search(
        query=req.query,
        language=req.language or "en",
        country=req.country or "US",
        currency=req.currency or "USD",
        preferred_payment=req.preferred_payment or "all",
        session_id=req.session_id or "web-sess",
        risk_prefs=risk_prefs
    )
    return state.model_dump()

@app.post("/api/paypal/create-dossier")
async def api_create_dossier(req: CreateDossierRequest):
    """Generate cryptographic dispute evidence dossier for PayPal Buyer Protection Section 13."""
    dossier = PayPalEvidenceSentinel.create_dispute_dossier(
        order_id=req.order_id,
        item_title=req.item_title,
        platform=req.platform,
        agreed_tco=req.agreed_tco,
        condition=req.condition or "Brand New",
        open_box_verified=bool(req.open_box_verified),
        seller_name=req.seller_name or "Authorized Partner",
        seller_rating=float(req.seller_rating or 4.5),
        warranty_claims=req.warranty_claims or "1-Year OEM Coverage",
        display_currency=req.display_currency or "USD",
    )
    dossier_data = dossier.model_dump()
    gcp_db_service.save_dossier(req.order_id, dossier_data)
    return dossier_data

@app.get("/api/paypal/dossiers")
async def list_dispute_dossiers(limit: int = 50):
    """Lists all cryptographic dispute dossiers stored in Google Cloud Firestore."""
    dossiers = gcp_db_service.list_dossiers(limit=limit)
    return {
        "count": len(dossiers),
        "dossiers": dossiers
    }

@app.get("/api/paypal/dossiers/{order_id}")
async def get_dispute_dossier(order_id: str):
    """Retrieves an evidentiary cryptographic dispute dossier by PayPal Order ID."""
    dossier = gcp_db_service.get_dossier(order_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"No dispute dossier found for order '{order_id}'")
    return dossier

@app.post("/api/paypal/create-order")
async def api_create_order(req: CreateOrderRequest):
    """Generate PayPal v2 Order in requested currency."""
    try:
        order = await paypal_svc.create_order(
            amount=req.amount,
            item_name=req.item_name,
            currency=req.currency or "USD"
        )
        if isinstance(order, dict) and "id" in order:
            gcp_db_service.save_order(order["id"], order)
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/paypal/capture-order")
async def api_capture_order(req: CaptureOrderRequest):
    """Capture PayPal Order."""
    try:
        capture = await paypal_svc.capture_order(order_id=req.order_id)
        if isinstance(capture, dict):
            existing_order = gcp_db_service.get_order(req.order_id) or {}
            existing_order.update({"capture_details": capture, "status": "COMPLETED"})
            gcp_db_service.save_order(req.order_id, existing_order)
        return capture
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/negotiate")
async def websocket_endpoint(websocket: WebSocket):
    """Full-duplex WebSocket for streaming live inter-agent negotiations with task shielding."""
    await websocket.accept()
    q = global_bus.subscribe()

    active_tasks = set()
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
    active_tasks.add(consumer_task)

    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
            except (json.JSONDecodeError, TypeError):
                continue
            action = data.get("action")

            if action == "search":
                query = data.get("query", "Sony WH-1000XM5")
                language = data.get("language", "en")
                country = data.get("country", "US")
                currency = data.get("currency", "USD")
                preferred_payment = data.get("preferred_payment", "all")
                session_id = data.get("session_id", "ws-session")
                risk_prefs = RiskPreferences(
                    warranty_priority=float(data.get("warranty_priority", 0.5)),
                    speed_priority=float(data.get("speed_priority", 0.5)),
                    trust_tolerance=float(data.get("trust_tolerance", 0.7)),
                )

                # Execute swarm in background and stream results
                async def run_swarm():
                    try:
                        state = await coordinator.execute_search(
                            query=query,
                            language=language,
                            country=country,
                            currency=currency,
                            preferred_payment=preferred_payment,
                            session_id=session_id,
                            risk_prefs=risk_prefs
                        )
                        await websocket.send_text(json.dumps({
                            "type": "FINAL_RESULT",
                            "state": state.model_dump()
                        }))
                    except asyncio.CancelledError:
                        pass
                    except Exception as err:
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "ERROR",
                                "message": str(err)
                            }))
                        except Exception:
                            pass

                swarm_task = asyncio.create_task(run_swarm())
                active_tasks.add(swarm_task)
                swarm_task.add_done_callback(active_tasks.discard)

            elif action == "re_rank":
                risk_prefs = RiskPreferences(
                    warranty_priority=float(data.get("warranty_priority", 0.5)),
                    speed_priority=float(data.get("speed_priority", 0.5)),
                    trust_tolerance=float(data.get("trust_tolerance", 0.7)),
                )
                updated_state = await coordinator.re_rank_current_state(risk_prefs)
                if updated_state:
                    await websocket.send_text(json.dumps({
                        "type": "FINAL_RESULT",
                        "state": updated_state.model_dump()
                    }))

            elif action == "challenge_listing":
                listing_id = data.get("listing_id")
                challenge_type = data.get("challenge_type", "VERIFY_STOCK")
                updated_state = await coordinator.challenge_listing(listing_id, challenge_type)
                if updated_state:
                    await websocket.send_text(json.dumps({
                        "type": "CHALLENGE_RESOLVED",
                        "listing_id": listing_id,
                        "challenge_type": challenge_type,
                        "state": updated_state.model_dump()
                    }))

    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    finally:
        for t in list(active_tasks):
            t.cancel()
        active_tasks.clear()
        global_bus.unsubscribe(q)

# Mount frontend build or public assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "public")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)


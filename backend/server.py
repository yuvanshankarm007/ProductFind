"""
FastAPI Server & WebSocket Streaming Gateway for ProductFind / PayPal Sentinel AI.
Hosts agent orchestration, PayPal developer API endpoints, multi-currency FX service,
and real-time session-isolated event streaming.
"""

import os
import sys
import json
import asyncio

if sys.platform == "win32":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:
        pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from .core.bus import EventBus
from .coordinator import SentinelCoordinator
from .paypal_service import PayPalService, PayPalEvidenceSentinel
from .agents.fx_service import BASE_RATES_USD, CURRENCY_SYMBOLS
from .core.i18n import SUPPORTED_LANGUAGES
from .schemas import RiskPreferences, DisputeDossier
from .agents.adaptive_skill_learner import AdaptiveSkillLearner, SkillVault, AdaptiveSkill
from .agents.autonomous_self_healer import autonomous_healer
from .core.gcp_db import gcp_db_service
from .core.instincts import commerce_instincts
from .core.prompt_learner import PromptLearnerEngine

_relay_server = None

async def run_ipv6_relay(port: int = 8000):
    """
    Asynchronous IPv6 loopback relay: listens on [::1]:port and forwards to 127.0.0.1:port.
    Handles Chromium/Brave IPv6 preference on Windows without unbounded thread spawning.
    """
    async def handle_relay(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            target_reader, target_writer = await asyncio.open_connection("127.0.0.1", port)
            async def forward(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
                try:
                    while data := await src.read(16384):
                        dst.write(data)
                        await dst.drain()
                except Exception:
                    pass
                finally:
                    try:
                        if hasattr(dst, "can_write_eof") and dst.can_write_eof():
                            dst.write_eof()
                    except Exception:
                        pass

            await asyncio.gather(
                forward(reader, target_writer),
                forward(target_reader, writer),
                return_exceptions=True
            )
        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            try:
                target_writer.close()
                await target_writer.wait_closed()
            except Exception:
                pass

    try:
        server = await asyncio.start_server(handle_relay, "::1", port)
        print(f"[IPv6 Relay] Bound loopback server on [::1]:{port} -> 127.0.0.1:{port}")
        return server
    except Exception as e:
        print(f"[IPv6 Relay] Status / Note: {e}")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _relay_server
    port = int(os.getenv("PORT", 8000))
    _relay_server = await run_ipv6_relay(port)
    yield
    if _relay_server:
        try:
            _relay_server.close()
            await _relay_server.wait_closed()
            print("[IPv6 Relay] Cleanly shut down.")
        except Exception:
            pass


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

# Global instances
global_bus = EventBus()
coordinator = SentinelCoordinator(global_bus)
paypal_svc = PayPalService()
skill_vault = SkillVault()
skill_learner = AdaptiveSkillLearner(skill_vault)


# Request schemas
class LearnSkillRequest(BaseModel):
    domain: str
    content: Optional[str] = ""
    country: Optional[str] = "US"
    currency: Optional[str] = "USD"


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


class SelfLearnRequest(BaseModel):
    domains: Optional[List[str]] = None


class LearnInstinctRequest(BaseModel):
    pattern: str
    reason: str
    replacement_target: Optional[str] = None


class LearnFromPromptRequest(BaseModel):
    prompt: str


class QuarantineItemRequest(BaseModel):
    merchant: str
    merchant_domain: Optional[str] = None
    listing_id: Optional[str] = None
    reason: str = "User Reported Scam / Dead Link / Out of Stock"


# Endpoints
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    fav_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "public", "favicon.svg")
    if os.path.exists(fav_path):
        return FileResponse(fav_path, media_type="image/svg+xml")
    return Response(status_code=204)


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
    return gcp_db_service.get_status()


@app.get("/api/preferences")
async def get_preferences():
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
    """Trigger agent swarm search via HTTP with dynamic risk preferences and session isolation."""
    risk_prefs = RiskPreferences(
        warranty_priority=req.warranty_priority if req.warranty_priority is not None else 0.5,
        speed_priority=req.speed_priority if req.speed_priority is not None else 0.5,
        trust_tolerance=req.trust_tolerance if req.trust_tolerance is not None else 0.7,
    )
    # Session-isolated clear: does NOT wipe other concurrent active sessions!
    global_bus.clear(session_id=req.session_id)

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


@app.get("/api/skills")
async def list_skills():
    skills = skill_vault.list_skills()
    return {
        "count": len(skills),
        "skills": [s.model_dump() for s in skills]
    }


@app.get("/api/skills/{domain}")
async def get_skill(domain: str):
    skill = skill_vault.get_skill(domain)
    if not skill:
        raise HTTPException(status_code=404, detail=f"No skill acquired for domain '{domain}'")
    return skill.model_dump()


@app.post("/api/skills/learn")
@app.post("/api/skills/teach")
async def learn_skill(req: LearnSkillRequest):
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


@app.get("/api/system/health")
async def get_system_health():
    report = await autonomous_healer.tester.get_or_run_diagnostic(max_age_seconds=60.0)
    report.recent_repairs = autonomous_healer.fixer.fix_history[-10:]
    return report.model_dump()


@app.post("/api/system/self-test")
async def trigger_self_test():
    report = await autonomous_healer.tester.run_full_diagnostic()
    report.recent_repairs = autonomous_healer.fixer.fix_history[-10:]
    return {
        "status": "success",
        "report": report.model_dump()
    }


@app.post("/api/system/self-fix")
async def trigger_self_fix():
    report = await autonomous_healer.run_comprehensive_audit_and_heal()
    return {
        "status": "success",
        "report": report.model_dump(),
        "repairs_applied": [r.model_dump() for r in report.recent_repairs]
    }


@app.post("/api/system/self-learn")
async def trigger_self_learn(req: Optional[SelfLearnRequest] = None):
    domains = req.domains if req else None
    learned = await autonomous_healer.learner.run_discovery_cycle(domains)
    return {
        "status": "success",
        "skills_acquired": [s.model_dump() for s in learned],
        "total_skills_in_vault": len(autonomous_healer.learner.skill_learner.vault.list_skills())
    }


@app.get("/api/system/repairs")
async def get_repair_history():
    return [r.model_dump() for r in autonomous_healer.fixer.fix_history]


@app.get("/api/system/instincts")
async def get_system_instincts():
    instincts = commerce_instincts.list_instincts()
    return {
        "status": "success",
        "total_instincts": len(instincts),
        "instincts": [inst.model_dump() for inst in instincts]
    }


@app.post("/api/system/instincts/learn")
async def add_system_instinct(req: LearnInstinctRequest):
    inst = commerce_instincts.record_dead_link_instinct(
        pattern=req.pattern,
        reason=req.reason,
        replacement_url=req.replacement_target
    )
    return {"status": "success", "instinct": inst.model_dump()}


@app.post("/api/system/instincts/learn-from-prompt")
async def api_learn_from_prompt(req: LearnFromPromptRequest):
    """
    Ingests natural language user feedback or search directives, extracts negative constraints,
    and dynamically compiles new operational reflex instincts.
    """
    clean_query, constraints, newly_learned = PromptLearnerEngine.parse_and_learn_from_prompt(
        raw_prompt=req.prompt,
        instincts_vault=commerce_instincts
    )
    all_instincts = commerce_instincts.list_instincts()
    return {
        "status": "success",
        "raw_prompt": req.prompt,
        "clean_query": clean_query,
        "constraints": constraints.model_dump(),
        "newly_learned_count": len(newly_learned),
        "newly_learned": newly_learned,
        "total_active_instincts": len(all_instincts)
    }


@app.post("/api/system/quarantine-item")
async def api_quarantine_item(req: QuarantineItemRequest):
    """
    1-Click user feedback endpoint: flags and permanently blacklists or quarantines
    a scam merchant, 404 dead link, or out-of-stock product.
    """
    target = req.merchant_domain or req.merchant
    inst = commerce_instincts.record_prompt_instinct(
        prompt_text=f"User Flagged: {req.reason}",
        category="USER_QUARANTINE_MERCHANT",
        pattern=target,
        reason=f"User Flagged: {req.reason} on merchant '{req.merchant}' (listing '{req.listing_id or ''}')"
    )
    return {
        "status": "success",
        "message": f"Merchant '{req.merchant}' successfully quarantined and registered in reflex memory.",
        "rule_id": inst.rule_id,
        "category": inst.category
    }


@app.post("/api/paypal/create-dossier")
async def api_create_dossier(req: CreateDossierRequest):
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
    dossiers = gcp_db_service.list_dossiers(limit=limit)
    return {
        "count": len(dossiers),
        "dossiers": dossiers
    }


@app.get("/api/paypal/dossiers/{order_id}")
async def get_dispute_dossier(order_id: str):
    dossier = gcp_db_service.get_dossier(order_id)
    if not dossier:
        raise HTTPException(status_code=404, detail=f"No dispute dossier found for order '{order_id}'")
    return dossier


@app.post("/api/paypal/create-order")
async def api_create_order(req: CreateOrderRequest):
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
async def websocket_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """Full-duplex WebSocket for streaming live inter-agent negotiations with session routing."""
    await websocket.accept()

    current_session = session_id or "ws-session"
    q = global_bus.subscribe(session_id=current_session)
    active_tasks = set()

    async def event_forwarder():
        nonlocal q
        try:
            while True:
                event = await q.get()
                await websocket.send_text(json.dumps({
                    "type": "AGENT_EVENT",
                    "event": event.model_dump()
                }))
        except (asyncio.CancelledError, WebSocketDisconnect):
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
            except (json.JSONDecodeError, TypeError, Exception):
                continue

            action = data.get("action")

            if action == "search":
                query = data.get("query", "Sony WH-1000XM5")
                language = data.get("language", "en")
                country = data.get("country", "US")
                currency = data.get("currency", "USD")
                preferred_payment = data.get("preferred_payment", "all")
                requested_session = data.get("session_id", current_session)

                if requested_session != current_session:
                    global_bus.unsubscribe(q, session_id=current_session)
                    current_session = requested_session
                    q = global_bus.subscribe(session_id=current_session)

                risk_prefs = RiskPreferences(
                    warranty_priority=float(data.get("warranty_priority", 0.5)),
                    speed_priority=float(data.get("speed_priority", 0.5)),
                    trust_tolerance=float(data.get("trust_tolerance", 0.7)),
                )

                async def run_swarm():
                    try:
                        state = await coordinator.execute_search(
                            query=query,
                            language=language,
                            country=country,
                            currency=currency,
                            preferred_payment=preferred_payment,
                            session_id=current_session,
                            risk_prefs=risk_prefs
                        )
                        await websocket.send_text(json.dumps({
                            "type": "FINAL_RESULT",
                            "state": state.model_dump()
                        }))
                    except (asyncio.CancelledError, WebSocketDisconnect):
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
                requested_session = data.get("session_id", current_session)
                risk_prefs = RiskPreferences(
                    warranty_priority=float(data.get("warranty_priority", 0.5)),
                    speed_priority=float(data.get("speed_priority", 0.5)),
                    trust_tolerance=float(data.get("trust_tolerance", 0.7)),
                )
                updated_state = await coordinator.re_rank_current_state(risk_prefs, session_id=requested_session)
                if updated_state:
                    await websocket.send_text(json.dumps({
                        "type": "FINAL_RESULT",
                        "state": updated_state.model_dump()
                    }))

            elif action == "challenge_listing":
                requested_session = data.get("session_id", current_session)
                listing_id = data.get("listing_id")
                challenge_type = data.get("challenge_type", "VERIFY_STOCK")
                updated_state = await coordinator.challenge_listing(listing_id, challenge_type, session_id=requested_session)
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
        global_bus.unsubscribe(q, session_id=current_session)


# Mount frontend assets
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "public")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("backend.server:app", host="0.0.0.0", port=port, reload=True)

"""
Model Context Protocol (MCP) JSON-RPC 2.0 Agent-Commerce Endpoint for ProductFind Sentinel.
Allows external AI agents (Claude Desktop, Cursor, Antigravity, LangGraph, OpenAI Agents)
to invoke Sentinel arbitration, consumer proof auditing, link safety verification, and Section 13 dispute filing.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from backend.core.reddit_consensus import reddit_consensus_engine
from backend.core.bifl_index import bifl_index_engine
from backend.core.review_authenticity import review_authenticity_engine
from backend.core.link_verifier import verify_url_live
from backend.core.dispute_assistant import DisputeFilingRequest, dispute_service

MCP_PROTOCOL_VERSION = "2024-11-05"

MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "arbitrate_deal",
        "description": (
            "Run ProductFind Sentinel's multi-agent deal arbitration to compare retailers, calculate "
            "Risk-Adjusted Total Cost of Ownership (TCO), check customs/FX, and rank the optimal merchant."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Product name or SKU to arbitrate"},
                "country": {"type": "string", "default": "US", "description": "Buyer country code (US, IN, GB, DE, CA, JP, AU)"},
                "currency": {"type": "string", "default": "USD", "description": "Target currency (USD, INR, EUR, GBP, etc.)"},
                "warranty_weight": {"type": "number", "default": 0.5},
                "speed_weight": {"type": "number", "default": 0.3},
                "trust_weight": {"type": "number", "default": 0.8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "audit_consumer_proof",
        "description": (
            "Audit community consensus (live Reddit/HN discussions), iFixit repairability / BIFL longevity score, "
            "and fake-review authenticity grade for any product."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Product name to audit"},
                "store": {"type": "string", "default": "Amazon", "description": "Merchant store context"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "verify_listing_safety",
        "description": "Perform live SSRF-safe HTTP pre-click link verification and HTTPS status telemetry check on a product URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Public merchant product URL to verify"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "compile_dispute_dossier",
        "description": (
            "Compile a tamper-evident PayPal Section 13 / card chargeback legal PDF dossier with "
            "a cryptographic point-in-time checkout snapshot SHA-256."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "merchant": {"type": "string"},
                "product_title": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string", "default": "USD"},
                "issue_type": {"type": "string", "default": "OPEN_BOX_VIOLATION"},
                "incident_description": {"type": "string"},
                "merchant_url": {"type": "string"},
            },
            "required": ["order_id", "merchant", "product_title", "amount", "incident_description"],
        },
    },
]


def get_mcp_manifest(base_url: str = "http://127.0.0.1:8000") -> Dict[str, Any]:
    return {
        "name": "productfind-sentinel",
        "version": "2.0.0",
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "endpoint": f"{base_url.rstrip('/')}/mcp",
        "transport": "streamable-http-jsonrpc",
        "tools": MCP_TOOLS,
    }


async def _call_tool_async(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "arbitrate_deal":
        from backend.coordinator import SentinelCoordinator
        from backend.core.bus import EventBus
        from backend.schemas import RiskPreferences

        query = str(arguments.get("query") or "").strip()
        if not query:
            raise ValueError("Missing required argument 'query'")
        risk_prefs = RiskPreferences(
            warranty_priority=max(0.0, min(1.0, float(arguments.get("warranty_weight", 0.5)))),
            speed_priority=max(0.0, min(1.0, float(arguments.get("speed_weight", 0.3)))),
            trust_tolerance=max(0.0, min(1.0, float(arguments.get("trust_weight", 0.8)))),
        )
        coordinator = SentinelCoordinator(EventBus())
        state = await coordinator.execute_search(
            query=query,
            country=str(arguments.get("country") or "US").upper(),
            currency=str(arguments.get("currency") or "USD").upper(),
            risk_prefs=risk_prefs,
        )
        top_options = [
            {
                "rank": opt.rank,
                "merchant": opt.listing.merchant,
                "product_title": opt.listing.product_title,
                "display_currency": opt.display_currency,
                "cash_outlay": opt.converted_cash_outlay,
                "risk_adjusted_tco": opt.risk_adjusted_tco,
                "recommendation_tier": opt.recommendation_tier,
                "url": opt.listing.listing_url,
                "url_verified": opt.url_verified,
            }
            for opt in (state.final_options or [])[:5]
        ]
        return {
            "query": state.clean_query or state.search_query,
            "options_count": len(state.final_options),
            "winner": top_options[0] if top_options else None,
            "top_options": top_options,
        }

    if name == "audit_consumer_proof":
        query = str(arguments.get("query") or "").strip()
        store = str(arguments.get("store") or "Amazon").strip()
        if not query:
            raise ValueError("Missing required argument 'query'")
        consensus, bifl = await asyncio.gather(
            reddit_consensus_engine.analyze_community_consensus_async(query),
            bifl_index_engine.evaluate_longevity_async(query),
        )
        review_audit = review_authenticity_engine.audit_reviews(query, store=store)
        return {
            "query": query,
            "reddit_consensus": consensus.model_dump(),
            "review_authenticity": review_audit.model_dump(),
            "bifl_metrics": bifl.model_dump(),
        }

    if name == "verify_listing_safety":
        url = str(arguments.get("url") or "").strip()
        if not url:
            raise ValueError("Missing required argument 'url'")
        return await verify_url_live(url)

    if name == "compile_dispute_dossier":
        req = DisputeFilingRequest(
            order_id=str(arguments["order_id"]),
            merchant=str(arguments["merchant"]),
            product_title=str(arguments["product_title"]),
            amount=float(arguments["amount"]),
            currency=str(arguments.get("currency") or "USD"),
            issue_type=str(arguments.get("issue_type") or "OPEN_BOX_VIOLATION"),
            incident_description=str(arguments["incident_description"]),
            merchant_url=arguments.get("merchant_url"),
        )
        case = dispute_service.file_dispute(req)
        return case.model_dump()

    raise KeyError(f"Unknown MCP tool: {name}")


async def handle_mcp_jsonrpc(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Process a standard MCP JSON-RPC 2.0 request envelope and return a JSON-RPC 2.0 response."""
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "productfind-sentinel", "version": "2.0.0"},
            },
        }

    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": MCP_TOOLS}}

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            structured = await _call_tool_async(str(tool_name), dict(arguments))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(structured, indent=2)}],
                    "structuredContent": structured,
                    "isError": False,
                },
            }
        except KeyError as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": str(exc)},
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error executing {tool_name}: {exc}"}],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }

"""
Verified Savings & Risk Avoidance Ledger for ProductFind Sentinel.
Persists real cumulative consumer value generated across search arbitrations:
- Cash arbitrage spread saved vs highest/sticker offer
- Cross-border customs/FX traps flagged
- Low-trust / dead listings filtered or warned
- Forensic dispute dossiers compiled
"""

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.core.state import BlackboardState

DEFAULT_LEDGER_PATH = Path(__file__).resolve().parent.parent / "data" / "savings_ledger.json"

FX_TO_USD = {
    "USD": 1.0,
    "INR": 1.0 / 84.5,
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.72,
    "JPY": 1.0 / 153.0,
    "AUD": 0.65,
}


def _to_usd(amount: float, currency: str) -> float:
    rate = FX_TO_USD.get((currency or "USD").upper(), 1.0)
    return max(0.0, float(amount or 0.0) * rate)


class SavingsLedger:
    """Thread-safe JSON-backed ledger quantifying Sentinel consumer savings and risk mitigation."""

    def __init__(self, ledger_path: Optional[Path] = None):
        self.ledger_path = Path(ledger_path) if ledger_path else DEFAULT_LEDGER_PATH
        self._lock = threading.Lock()
        self._ensure_initialized()

    def _default_data(self) -> Dict[str, Any]:
        return {
            "total_arbitrages_completed": 0,
            "total_arbitrage_saved_usd": 0.0,
            "total_customs_risks_flagged": 0,
            "total_low_trust_filtered": 0,
            "total_disputes_compiled": 0,
            "total_links_verified": 0,
            "recent_entries": [],
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    def _ensure_initialized(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self._write_locked(self._default_data())

    def _read_locked(self) -> Dict[str, Any]:
        try:
            with open(self.ledger_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                merged = self._default_data()
                merged.update(data)
                return merged
        except Exception:
            pass
        return self._default_data()

    def _write_locked(self, data: Dict[str, Any]) -> None:
        data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        tmp = self.ledger_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, self.ledger_path)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            data = self._read_locked()
        usd = round(float(data.get("total_arbitrage_saved_usd", 0.0)), 2)
        return {
            **data,
            "total_arbitrage_saved_usd": usd,
            "total_arbitrage_saved_inr": round(usd * 84.5, 2),
        }

    def record_search(self, state: BlackboardState) -> Dict[str, Any]:
        """Compute verified spread & risk flags from a completed BlackboardState and persist."""
        spread_usd = 0.0
        winner_merchant = "None"
        verified_links = 0

        if state.final_options:
            best_opt = state.final_options[0]
            winner_merchant = best_opt.listing.merchant
            verified_links = sum(1 for opt in state.final_options if getattr(opt, "url_verified", False))

            # Compare highest converted cash outlay vs winner's cash outlay
            outlays_usd = [
                _to_usd(
                    opt.converted_cash_outlay if opt.converted_cash_outlay > 0 else opt.total_cash_outlay,
                    opt.display_currency if opt.converted_cash_outlay > 0 else opt.original_currency,
                )
                for opt in state.final_options
                if (opt.converted_cash_outlay or opt.total_cash_outlay) > 0
            ]
            if len(outlays_usd) >= 2:
                spread_usd = round(max(0.0, max(outlays_usd) - min(outlays_usd)), 2)

        customs_flagged = sum(
            1
            for cb in (state.cross_border_analyses or {}).values()
            if getattr(cb, "is_cross_border", False) or getattr(cb, "estimated_import_duty_amount", 0.0) > 0
        )

        low_trust_flagged = sum(
            1
            for opt in (state.final_options or [])
            if getattr(opt.trust, "dispute_risk_factor", "") in ("High", "Critical")
            or getattr(opt.listing, "condition", "") == "Grey Market"
        ) + sum(
            1
            for raw in (state.raw_listings or [])
            if getattr(raw, "is_dead_link", False)
        )

        entry = {
            "query": state.clean_query or state.search_query,
            "winner_merchant": winner_merchant,
            "spread_saved_usd": spread_usd,
            "customs_flagged": customs_flagged,
            "low_trust_flagged": low_trust_flagged,
            "options_audited": len(state.final_options or []),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        with self._lock:
            data = self._read_locked()
            data["total_arbitrages_completed"] = int(data.get("total_arbitrages_completed", 0)) + 1
            data["total_arbitrage_saved_usd"] = round(float(data.get("total_arbitrage_saved_usd", 0.0)) + spread_usd, 2)
            data["total_customs_risks_flagged"] = int(data.get("total_customs_risks_flagged", 0)) + customs_flagged
            data["total_low_trust_filtered"] = int(data.get("total_low_trust_filtered", 0)) + low_trust_flagged
            data["total_links_verified"] = int(data.get("total_links_verified", 0)) + verified_links
            recent: List[Dict[str, Any]] = list(data.get("recent_entries") or [])
            recent.insert(0, entry)
            data["recent_entries"] = recent[:15]
            self._write_locked(data)

        return self.get_stats()

    def record_dispute_compiled(self) -> Dict[str, Any]:
        with self._lock:
            data = self._read_locked()
            data["total_disputes_compiled"] = int(data.get("total_disputes_compiled", 0)) + 1
            self._write_locked(data)
        return self.get_stats()


savings_ledger = SavingsLedger()

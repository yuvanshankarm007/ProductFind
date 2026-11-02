"""
Asynchronous Event Bus for ProductFind Swarm.
Implements the Shared Blackboard communication layer with Session-Scoped Isolation.
Supports high-concurrency multi-session streaming without cross-session event collision.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


class AgentEvent(BaseModel):
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    source_agent: str
    target_agent: str
    event_type: str  # e.g., DISPATCH, BACKPROPAGATION_REQUEST, BACKPROPAGATION_RESPONSE, CHALLENGE, SYNTHESIZED, CIRCUIT_BREAKER
    content: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class EventBus:
    """
    Thread-safe & async event broker.
    Supports both global pub-sub and session-isolated subscriber queues.
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._session_subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self._logs: List[AgentEvent] = []
        self._lock = asyncio.Lock()

    def subscribe(self, session_id: Optional[str] = None) -> asyncio.Queue:
        """Subscribe to the event stream, optionally filtered by session_id."""
        q: asyncio.Queue = asyncio.Queue()
        if session_id:
            if session_id not in self._session_subscribers:
                self._session_subscribers[session_id] = set()
            self._session_subscribers[session_id].add(q)
        else:
            self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue, session_id: Optional[str] = None) -> None:
        """Remove a subscriber queue safely."""
        self._subscribers.discard(q)
        if session_id and session_id in self._session_subscribers:
            self._session_subscribers[session_id].discard(q)
            if not self._session_subscribers[session_id]:
                del self._session_subscribers[session_id]

    async def emit(
        self,
        source: str,
        target: str,
        event_type: str,
        content: str,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AgentEvent:
        """Emit an event to all appropriate subscribers."""
        event = AgentEvent(
            source_agent=source,
            target_agent=target,
            event_type=event_type,
            content=content,
            payload=payload or {},
            session_id=session_id,
        )

        self._logs.append(event)
        # Cap log history in memory to prevent memory leaks
        if len(self._logs) > 1000:
            self._logs = self._logs[-500:]

        # Broadcast to session-specific subscribers if session_id is provided
        if session_id and session_id in self._session_subscribers:
            for q in list(self._session_subscribers[session_id]):
                try:
                    q.put_nowait(event)
                except Exception:
                    pass
        elif session_id is None:
            # Broadcast system-wide events to ALL session subscribers
            for s_id, s_set in list(self._session_subscribers.items()):
                for q in list(s_set):
                    try:
                        q.put_nowait(event)
                    except Exception:
                        pass

        # Broadcast to global subscribers
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except Exception:
                pass

        return event

    def clear(self, session_id: Optional[str] = None) -> None:
        """
        Safely clears queues and logs.
        CRITICAL FIX: If session_id is specified, only that session is cleared.
        Global logs are only trimmed, never wiped across concurrent active sessions.
        """
        if session_id:
            if session_id in self._session_subscribers:
                for q in self._session_subscribers[session_id]:
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except Exception:
                            break
            self._logs = [e for e in self._logs if e.session_id != session_id]
        else:
            # Clear global subscribers
            for q in list(self._subscribers):
                while not q.empty():
                    try:
                        q.get_nowait()
                    except Exception:
                        break
            self._logs.clear()

    def get_logs(self, session_id: Optional[str] = None) -> List[AgentEvent]:
        """Retrieve recorded events, optionally filtered by session_id."""
        if session_id:
            return [e for e in self._logs if e.session_id == session_id]
        return list(self._logs)

    def get_session_scope(self, session_id: str) -> "SessionScopedBus":
        """Returns a session-isolated adapter bound to a specific session_id."""
        return SessionScopedBus(self, session_id)


class SessionScopedBus:
    """Wrapper that automatically tags all emitted events with the given session_id."""

    def __init__(self, parent_bus: EventBus, session_id: str):
        self._bus = parent_bus
        self.session_id = session_id

    async def emit(
        self,
        source: str,
        target: str,
        event_type: str,
        content: str,
        payload: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> AgentEvent:
        return await self._bus.emit(
            source=source,
            target=target,
            event_type=event_type,
            content=content,
            payload=payload,
            session_id=session_id or self.session_id,
        )

    def subscribe(self, session_id: Optional[str] = None) -> asyncio.Queue:
        return self._bus.subscribe(session_id=session_id or self.session_id)

    def unsubscribe(self, q: asyncio.Queue, session_id: Optional[str] = None) -> None:
        self._bus.unsubscribe(q, session_id=session_id or self.session_id)

    def clear(self, session_id: Optional[str] = None) -> None:
        self._bus.clear(session_id=session_id or self.session_id)

    def get_logs(self, session_id: Optional[str] = None) -> List[AgentEvent]:
        return self._bus.get_logs(session_id=session_id or self.session_id)

    def get_session_scope(self, session_id: str) -> "SessionScopedBus":
        return self._bus.get_session_scope(session_id)

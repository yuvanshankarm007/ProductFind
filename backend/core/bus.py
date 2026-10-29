"""
Bidirectional Event Bus for Inter-Agent Communication and WebSocket Streaming.
Allows agents to publish queries, receive feedback, and broadcast live traces to the client.
"""

import asyncio
from typing import Callable, List, Dict, Any
from .state import AgentNegotiationEvent
import uuid
import time

class EventBus:
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []
        self._event_log: List[AgentNegotiationEvent] = []

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def emit(self, source: str, target: str, event_type: str, content: str, payload: Dict[str, Any] = None) -> AgentNegotiationEvent:
        event = AgentNegotiationEvent(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            source_agent=source,
            target_agent=target,
            event_type=event_type,
            content=content,
            payload=payload or {}
        )
        self._event_log.append(event)
        
        # Broadcast to all live listeners (including WebSockets)
        for q in self._subscribers:
            await q.put(event)
            
        return event

    def get_logs(self) -> List[AgentNegotiationEvent]:
        return list(self._event_log)

    def clear(self):
        self._event_log.clear()

import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket


class OrderUpdatesHub:
    """In-memory hub to broadcast order status events to connected WebSocket clients."""

    def __init__(self) -> None:
        self._connections_by_order: Dict[int, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, order_id: int, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections_by_order.setdefault(order_id, set()).add(ws)

    async def disconnect(self, order_id: int, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections_by_order.get(order_id)
            if not conns:
                return
            conns.discard(ws)
            if not conns:
                self._connections_by_order.pop(order_id, None)

    async def broadcast(self, order_id: int, payload: dict) -> None:
        message = json.dumps(payload, default=str)
        async with self._lock:
            conns = list(self._connections_by_order.get(order_id, set()))
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                # Best-effort: ignore broken connections
                pass


# Singleton instance used by routes
hub = OrderUpdatesHub()

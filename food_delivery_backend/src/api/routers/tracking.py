from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.deps import get_current_user
from src.db.models import Order, Restaurant, User, UserRole
from src.db.session import get_db
from src.realtime.hub import hub

router = APIRouter(prefix="/tracking", tags=["Tracking"])


@router.get(
    "/orders/{order_id}/status",
    summary="Get order status (polling)",
    description="Polling-friendly endpoint to get latest order status for an order (role-aware).",
)
def get_order_status(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Return current status for a single order, with role-based access checks."""
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role == UserRole.customer and order.customer_user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.role == UserRole.delivery and order.delivery_person_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if user.role == UserRole.restaurant:
        restaurant = db.execute(select(Restaurant).where(Restaurant.id == order.restaurant_id)).scalar_one_or_none()
        if restaurant is None or restaurant.owner_user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")

    return {"order_id": order.id, "status": order.status.value, "payment_status": order.payment_status.value}


@router.websocket("/ws/orders/{order_id}")
async def ws_order_updates(ws: WebSocket, order_id: int) -> None:
    """
    WebSocket endpoint for real-time order status updates.

    Usage:
    - Connect to ws://<host>/tracking/ws/orders/{order_id}
    - Server sends JSON messages when order status changes.
    Note: This is an unauthenticated demo WebSocket; in production, authenticate using a token query param
    or a cookie-based session.
    """
    await hub.connect(order_id, ws)
    try:
        while True:
            # Keep connection open; ignore client messages (or could treat as ping).
            await ws.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(order_id, ws)
    except Exception:
        await hub.disconnect(order_id, ws)

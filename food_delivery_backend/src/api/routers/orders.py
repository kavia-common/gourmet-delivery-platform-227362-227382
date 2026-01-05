from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.deps import get_current_user, require_role
from src.db.models import (
    CartItem,
    MenuItem,
    Order,
    OrderEvent,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    Restaurant,
    User,
    UserRole,
)
from src.db.session import get_db
from src.realtime.hub import hub
from src.schemas import OrderCreateRequest, OrderResponse, OrderStatusUpdateRequest

router = APIRouter(prefix="/orders", tags=["Orders"])


def _order_to_response(order: Order) -> OrderResponse:
    # Ensure relationships are loaded; in typical sync SQLAlchemy this will lazy load.
    return OrderResponse.model_validate(order)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place order/checkout (customer role)",
    description="Creates an order from the current cart. Clears cart on success.",
)
async def create_order(
    payload: OrderCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.customer)),
) -> OrderResponse:
    """Create order from cart items; computes totals and generates initial status event."""
    restaurant = db.execute(select(Restaurant).where(Restaurant.id == payload.restaurant_id)).scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    cart_items = db.execute(select(CartItem).where(CartItem.user_id == user.id)).scalars().all()
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Compute subtotal based on current menu prices
    subtotal = 0.0
    order_items: list[OrderItem] = []
    for ci in cart_items:
        mi = db.execute(select(MenuItem).where(MenuItem.id == ci.menu_item_id)).scalar_one_or_none()
        if mi is None or not mi.is_available:
            raise HTTPException(status_code=400, detail=f"Menu item {ci.menu_item_id} unavailable")
        subtotal += float(mi.price) * int(ci.quantity)
        order_items.append(
            OrderItem(
                menu_item_id=mi.id,
                name_snapshot=mi.name,
                price_snapshot=float(mi.price),
                quantity=int(ci.quantity),
            )
        )

    delivery_fee = 3.99
    total = float(subtotal) + float(delivery_fee)

    order = Order(
        customer_user_id=user.id,
        restaurant_id=restaurant.id,
        status=OrderStatus.pending,
        delivery_address=payload.delivery_address.strip(),
        subtotal_amount=subtotal,
        delivery_fee=delivery_fee,
        total_amount=total,
        payment_status=PaymentStatus.pending,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for oi in order_items:
        oi.order_id = order.id
        db.add(oi)

    event = OrderEvent(order_id=order.id, status=OrderStatus.pending, message="Order placed")
    db.add(event)

    # Clear cart
    for ci in cart_items:
        db.delete(ci)

    db.commit()
    db.refresh(order)

    # Broadcast initial status to any listeners
    await hub.broadcast(
        order.id,
        {"type": "order_status", "order_id": order.id, "status": order.status.value, "ts": datetime.utcnow().isoformat()},
    )

    return _order_to_response(order)


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="List my orders",
    description="Customers see their orders; restaurants see orders for their restaurants; delivery sees assigned orders.",
)
def list_my_orders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[OrderResponse]:
    """Role-aware order listing."""
    if user.role == UserRole.customer:
        q = select(Order).where(Order.customer_user_id == user.id).order_by(Order.created_at.desc())
    elif user.role == UserRole.restaurant:
        restaurant_ids = [r.id for r in db.execute(select(Restaurant).where(Restaurant.owner_user_id == user.id)).scalars().all()]
        if not restaurant_ids:
            return []
        q = select(Order).where(Order.restaurant_id.in_(restaurant_ids)).order_by(Order.created_at.desc())
    elif user.role == UserRole.delivery:
        q = select(Order).where(Order.delivery_person_id == user.id).order_by(Order.created_at.desc())
    else:
        return []

    orders = db.execute(q).scalars().all()
    return [OrderResponse.model_validate(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order details",
    description="Role-aware access to a specific order.",
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderResponse:
    """Get order if user has access."""
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

    return OrderResponse.model_validate(order)


@router.post(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
    description="Restaurants can move order through preparing; delivery can mark picked_up/delivered; customers can cancel if pending.",
)
async def update_order_status(
    order_id: int,
    payload: OrderStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> OrderResponse:
    """Update order status with basic role-based constraints and record an OrderEvent."""
    order = db.execute(select(Order).where(Order.id == order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    new_status = payload.status

    if user.role == UserRole.customer:
        if order.customer_user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if new_status != OrderStatus.cancelled or order.status != OrderStatus.pending:
            raise HTTPException(status_code=400, detail="Customers can only cancel pending orders")
    elif user.role == UserRole.restaurant:
        restaurant = db.execute(select(Restaurant).where(Restaurant.id == order.restaurant_id)).scalar_one_or_none()
        if restaurant is None or restaurant.owner_user_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if new_status not in {OrderStatus.confirmed, OrderStatus.preparing}:
            raise HTTPException(status_code=400, detail="Restaurant can only set confirmed/preparing")
        if order.status in {OrderStatus.cancelled, OrderStatus.delivered}:
            raise HTTPException(status_code=400, detail="Order is final")
    elif user.role == UserRole.delivery:
        if order.delivery_person_id is not None and order.delivery_person_id != user.id:
            raise HTTPException(status_code=403, detail="Forbidden")
        if new_status not in {OrderStatus.picked_up, OrderStatus.delivered}:
            raise HTTPException(status_code=400, detail="Delivery can only set picked_up/delivered")
        if order.delivery_person_id is None:
            order.delivery_person_id = user.id
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    order.status = new_status
    db.add(OrderEvent(order_id=order.id, status=new_status, message=payload.message))
    db.commit()
    db.refresh(order)

    await hub.broadcast(
        order.id,
        {"type": "order_status", "order_id": order.id, "status": order.status.value, "message": payload.message},
    )

    return OrderResponse.model_validate(order)

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.deps import require_role
from src.core.config import get_settings
from src.db.models import Order, PaymentStatus, User, UserRole
from src.db.session import get_db
from src.schemas import PaymentIntentRequest, PaymentIntentResponse

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/intent",
    response_model=PaymentIntentResponse,
    summary="Create payment intent (mock)",
    description="Creates a mock payment intent for an order. If external provider keys aren't configured, this remains a stub.",
)
def create_payment_intent(
    payload: PaymentIntentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.customer)),
) -> PaymentIntentResponse:
    """Create a payment intent for a customer's order (mock)."""
    settings = get_settings()

    order = db.execute(select(Order).where(Order.id == payload.order_id)).scalar_one_or_none()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.customer_user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    if settings.payments_provider != "mock" and payload.provider != "mock":
        # Placeholder for real provider integration
        raise HTTPException(status_code=501, detail="Payment provider integration not configured")

    # For mock, mark as authorized and return a fake client secret.
    order.payment_status = PaymentStatus.authorized
    db.commit()
    db.refresh(order)

    return PaymentIntentResponse(
        order_id=order.id,
        provider="mock",
        client_secret=f"mock_{secrets.token_urlsafe(24)}",
        status=order.payment_status,
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Payment webhook (stub)",
    description="Webhook receiver for payment providers. Currently accepts payload and returns 202.",
)
def payment_webhook() -> dict:
    """Webhook endpoint placeholder (validate signature when provider is configured)."""
    settings = get_settings()
    return {"status": "accepted", "provider": settings.payments_provider}

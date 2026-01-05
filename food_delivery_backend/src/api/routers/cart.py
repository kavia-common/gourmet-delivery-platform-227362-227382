from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.deps import require_role
from src.db.models import CartItem, MenuItem, User, UserRole
from src.db.session import get_db
from src.schemas import CartItemResponse, CartItemUpsertRequest

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get(
    "",
    response_model=list[CartItemResponse],
    summary="Get my cart (customer role)",
    description="Customers can view the current cart items.",
)
def get_cart(
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.customer)),
) -> list[CartItemResponse]:
    """Return current user's cart."""
    items = db.execute(select(CartItem).where(CartItem.user_id == user.id)).scalars().all()
    return list(items)


@router.post(
    "/items",
    response_model=CartItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add/update cart item (customer role)",
    description="Upsert a cart item (by menu_item_id).",
)
def upsert_cart_item(
    payload: CartItemUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.customer)),
) -> CartItemResponse:
    """Add or update quantity for an item in the cart."""
    menu_item = db.execute(select(MenuItem).where(MenuItem.id == payload.menu_item_id)).scalar_one_or_none()
    if menu_item is None or not menu_item.is_available:
        raise HTTPException(status_code=404, detail="Menu item not found or unavailable")

    existing = db.execute(
        select(CartItem).where(CartItem.user_id == user.id, CartItem.menu_item_id == payload.menu_item_id)
    ).scalar_one_or_none()

    if existing is None:
        ci = CartItem(user_id=user.id, menu_item_id=payload.menu_item_id, quantity=payload.quantity)
        db.add(ci)
        db.commit()
        db.refresh(ci)
        return ci

    existing.quantity = payload.quantity
    db.commit()
    db.refresh(existing)
    return existing


@router.delete(
    "/items/{cart_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove cart item (customer role)",
    description="Remove an item from the cart by cart_item_id.",
)
def remove_cart_item(
    cart_item_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.customer)),
) -> None:
    """Delete a cart item belonging to current user."""
    item = db.execute(select(CartItem).where(CartItem.id == cart_item_id, CartItem.user_id == user.id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()

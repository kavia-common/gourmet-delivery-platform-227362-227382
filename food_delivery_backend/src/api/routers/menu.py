from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.deps import require_role
from src.db.models import MenuItem, Restaurant, User, UserRole
from src.db.session import get_db
from src.schemas import MenuItemCreateRequest, MenuItemResponse

router = APIRouter(prefix="/menu", tags=["Menu"])


@router.get(
    "/restaurants/{restaurant_id}/items",
    response_model=list[MenuItemResponse],
    summary="List menu items for a restaurant",
    description="Public endpoint to browse menu items by restaurant.",
)
def list_menu_items(restaurant_id: int, db: Session = Depends(get_db)) -> list[MenuItemResponse]:
    """List menu items for a given restaurant."""
    restaurant = db.execute(select(Restaurant).where(Restaurant.id == restaurant_id)).scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    items = db.execute(select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)).scalars().all()
    return list(items)


@router.post(
    "/restaurants/{restaurant_id}/items",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create menu item (restaurant role)",
    description="Restaurant owners can create menu items for their restaurant.",
)
def create_menu_item(
    restaurant_id: int,
    payload: MenuItemCreateRequest,
    db: Session = Depends(get_db),
    owner: User = Depends(require_role(UserRole.restaurant)),
) -> MenuItemResponse:
    """Create a menu item under a restaurant owned by the current user."""
    restaurant = db.execute(select(Restaurant).where(Restaurant.id == restaurant_id)).scalar_one_or_none()
    if restaurant is None:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    if restaurant.owner_user_id != owner.id:
        raise HTTPException(status_code=403, detail="Not owner of restaurant")

    item = MenuItem(
        restaurant_id=restaurant_id,
        name=payload.name.strip(),
        description=(payload.description.strip() if payload.description else None),
        price=float(payload.price),
        is_available=bool(payload.is_available),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

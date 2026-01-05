from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.deps import require_role
from src.db.models import Restaurant, User, UserRole
from src.db.session import get_db
from src.schemas import RestaurantCreateRequest, RestaurantResponse

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.get(
    "",
    response_model=list[RestaurantResponse],
    summary="List restaurants",
    description="Public endpoint to list all restaurants.",
)
def list_restaurants(db: Session = Depends(get_db)) -> list[RestaurantResponse]:
    """List all restaurants."""
    return list(db.execute(select(Restaurant).order_by(Restaurant.name.asc())).scalars().all())


@router.post(
    "",
    response_model=RestaurantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create restaurant (restaurant role)",
    description="Restaurant owners can create a restaurant profile.",
)
def create_restaurant(
    payload: RestaurantCreateRequest,
    db: Session = Depends(get_db),
    owner: User = Depends(require_role(UserRole.restaurant)),
) -> RestaurantResponse:
    """Create a restaurant owned by the authenticated restaurant user."""
    existing = db.execute(select(Restaurant).where(Restaurant.slug == payload.slug)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=400, detail="Restaurant slug already exists")

    r = Restaurant(
        owner_user_id=owner.id,
        name=payload.name.strip(),
        slug=payload.slug.strip().lower(),
        description=(payload.description.strip() if payload.description else None),
        is_open=True,
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.get(
    "/me",
    response_model=list[RestaurantResponse],
    summary="List my restaurants (restaurant role)",
    description="Restaurant owners can list restaurants they own.",
)
def list_my_restaurants(
    db: Session = Depends(get_db),
    owner: User = Depends(require_role(UserRole.restaurant)),
) -> list[RestaurantResponse]:
    """List restaurants owned by current restaurant user."""
    return list(db.execute(select(Restaurant).where(Restaurant.owner_user_id == owner.id)).scalars().all())

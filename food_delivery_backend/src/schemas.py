from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from src.db.models import OrderStatus, PaymentStatus, UserRole


class HealthResponse(BaseModel):
    message: str = Field(..., description="Service health status message")


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")


class UserCreateRequest(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., description="Full name")
    password: str = Field(..., min_length=8, description="Plaintext password (min length 8)")
    role: UserRole = Field(..., description="Role: customer, restaurant, delivery")


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class RestaurantCreateRequest(BaseModel):
    name: str = Field(..., description="Restaurant name")
    slug: str = Field(..., description="URL-friendly unique identifier")
    description: Optional[str] = Field(None, description="Restaurant description")


class RestaurantResponse(BaseModel):
    id: int
    owner_user_id: int
    name: str
    slug: str
    description: Optional[str]
    is_open: bool

    class Config:
        from_attributes = True


class MenuItemCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0, description="Unit price")
    is_available: bool = True


class MenuItemResponse(BaseModel):
    id: int
    restaurant_id: int
    name: str
    description: Optional[str]
    price: float
    is_available: bool

    class Config:
        from_attributes = True


class CartItemUpsertRequest(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., ge=1, le=50)


class CartItemResponse(BaseModel):
    id: int
    user_id: int
    menu_item_id: int
    quantity: int

    class Config:
        from_attributes = True


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    name_snapshot: str
    price_snapshot: float
    quantity: int

    class Config:
        from_attributes = True


class OrderEventResponse(BaseModel):
    id: int
    status: OrderStatus
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreateRequest(BaseModel):
    restaurant_id: int
    delivery_address: str = Field(..., min_length=5, max_length=500)


class OrderResponse(BaseModel):
    id: int
    customer_user_id: int
    restaurant_id: int
    delivery_person_id: Optional[int]
    status: OrderStatus
    delivery_address: str
    subtotal_amount: float
    delivery_fee: float
    total_amount: float
    payment_status: PaymentStatus
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemResponse] = []
    events: List[OrderEventResponse] = []

    class Config:
        from_attributes = True


class OrderStatusUpdateRequest(BaseModel):
    status: OrderStatus
    message: Optional[str] = None


class PaymentIntentRequest(BaseModel):
    order_id: int
    provider: str = Field("mock", description="Payment provider identifier (mock by default)")


class PaymentIntentResponse(BaseModel):
    order_id: int
    provider: str
    client_secret: str = Field(..., description="Client secret (mock) or payment gateway secret")
    status: PaymentStatus

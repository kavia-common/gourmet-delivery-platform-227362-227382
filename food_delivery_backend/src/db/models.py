import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


class UserRole(str, enum.Enum):
    customer = "customer"
    restaurant = "restaurant"
    delivery = "delivery"


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    preparing = "preparing"
    picked_up = "picked_up"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    not_required = "not_required"
    pending = "pending"
    authorized = "authorized"
    paid = "paid"
    failed = "failed"
    refunded = "refunded"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    restaurants: Mapped[list["Restaurant"]] = relationship(back_populates="owner")
    delivery_assignments: Mapped[list["Order"]] = relationship(
        back_populates="delivery_person", foreign_keys="Order.delivery_person_id"
    )


class Restaurant(Base):
    __tablename__ = "restaurants"
    __table_args__ = (UniqueConstraint("slug", name="uq_restaurants_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_open: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped["User"] = relationship(back_populates="restaurants")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant")
    orders: Mapped[list["Order"]] = relationship(back_populates="restaurant")


class MenuItem(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True, nullable=False)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="menu_items")


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "menu_item_id", name="uq_cart_user_menu_item"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), index=True, nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    customer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id"), index=True, nullable=False)
    delivery_person_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False, default=OrderStatus.pending)

    delivery_address: Mapped[str] = mapped_column(String(500), nullable=False)

    subtotal_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    delivery_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    payment_status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    restaurant: Mapped["Restaurant"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    events: Mapped[list["OrderEvent"]] = relationship(back_populates="order")
    delivery_person: Mapped[Optional["User"]] = relationship(
        back_populates="delivery_assignments", foreign_keys=[delivery_person_id]
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), index=True, nullable=False)

    name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    price_snapshot: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    order: Mapped["Order"] = relationship(back_populates="items")


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True, nullable=False)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    order: Mapped["Order"] = relationship(back_populates="events")

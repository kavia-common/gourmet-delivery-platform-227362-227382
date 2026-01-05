from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from src.core.config import get_settings
from src.db.init_db import create_all_tables
from src.db.session import init_engine

from src.api.routers import auth, cart, menu, orders, payments, restaurants, tracking

openapi_tags = [
    {"name": "Auth", "description": "User registration and login (JWT)."},
    {"name": "Restaurants", "description": "Restaurant listing and restaurant-owner management."},
    {"name": "Menu", "description": "Menu browsing and menu item management."},
    {"name": "Cart", "description": "Customer cart operations."},
    {"name": "Orders", "description": "Order placement/checkout and order lifecycle management."},
    {"name": "Tracking", "description": "Order status tracking (polling + WebSocket)."},
    {"name": "Payments", "description": "Payment integration endpoints (mock/stub by default)."},
]


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Food delivery backend API providing auth, restaurants, menus, cart, checkout, "
        "order tracking (polling + WebSocket), and payment stubs."
    ),
    version=settings.app_version,
    openapi_tags=openapi_tags,
)

# CORS to allow the React app at port 3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    """Initialize DB engine and create tables if configured."""
    init_engine()
    create_all_tables()


@app.get(
    "/",
    summary="Health check",
    description="Basic health endpoint to verify API is running.",
)
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


@app.get(
    "/docs/websocket",
    response_class=PlainTextResponse,
    summary="WebSocket usage help",
    description="Returns quick notes on how to connect to the order status WebSocket.",
    tags=["Tracking"],
)
def websocket_help() -> str:
    """Human-readable help for WebSocket real-time order updates."""
    return (
        "WebSocket order updates:\n"
        "- Endpoint: /tracking/ws/orders/{order_id}\n"
        "- Connect using ws://<host>/tracking/ws/orders/{order_id}\n"
        "- Server broadcasts JSON on status changes.\n"
        "- Note: demo endpoint is unauthenticated; add auth before production.\n"
    )


app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(menu.router)
app.include_router(cart.router)
app.include_router(orders.router)
app.include_router(tracking.router)
app.include_router(payments.router)

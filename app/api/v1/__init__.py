"""API v1 router initialization."""
from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, admin

api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(auth.router)

# Include user endpoints
api_router.include_router(users.router)

# Include admin endpints
api_router.include_router(admin.router)
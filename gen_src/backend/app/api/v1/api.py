from fastapi import APIRouter

from app.api.v1.endpoints import users
from app.api.v1.endpoints import stocks
from app.api.v1.endpoints import watchlist
from app.api.v1.endpoints import simulation
from app.api.v1.endpoints import settings

# DESCRIPTION: This file aggregates all the v1 API endpoint routers into a single main router.

# Initialize the main router for the v1 API.
api_router = APIRouter()

# Include the user management endpoints from the users router.
# The prefix organizes all user-related endpoints under '/users'.
# The tags group them in the OpenAPI documentation.
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Include the stock data endpoints from the stocks router.
api_router.include_router(stocks.router, prefix="/stocks", tags=["stocks"])

# Include the watchlist management endpoints from the watchlist router.
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])

# Include the trading simulation endpoints from the simulation router.
api_router.include_router(simulation.router, prefix="/simulation", tags=["simulation"])

# Include the user settings endpoints from the settings router.
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])

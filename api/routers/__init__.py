"""API Routers package."""
from api.routers.journalists import router as journalists_router
from api.routers.campaigns import router as campaigns_router
from api.routers.outreach import router as outreach_router
from api.routers.scraping import scraping_router, ai_router
from api.routers.auth import router as auth_router

__all__ = [
    "journalists_router",
    "campaigns_router",
    "outreach_router",
    "scraping_router",
    "ai_router",
    "auth_router",
]

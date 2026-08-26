"""FastAPI Main Entrypoint for OpenClaw PR Manager."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import get_settings
from api.routers import (
    journalists_router,
    campaigns_router,
    outreach_router,
    scraping_router,
    ai_router,
    auth_router,
)
from scripts.seed_data import seed_initial_data
from api.lifecyle import lifespan as custom_lifespan

# Import middleware initialization
from middleware.rate_limiter import limiter, register_rate_limit_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openclaw_pr")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes app state and loads seed demo data if empty."""
    logger.info("Starting OpenClaw PR Manager Backend...")
    logger.info("Supabase Configured: %s", settings.is_supabase_configured)
    logger.info("OpenAI Configured: %s", settings.is_openai_configured)
    logger.info("DeepSeek Configured: %s", settings.is_deepseek_configured)
    logger.info("Gmail OAuth Configured: %s", settings.is_gmail_configured)
    
    # Initialize email services
    from middleware.rate_limiter import initialize_email_services
    email_queue = initialize_email_services()
    logger.info("✅ Email queue initialized")
    
    seed_initial_data()
    
    # Register rate limit error handler
    register_rate_limit_handler(app)
    
    # Call custom lifespan for background scheduler startup
    async with custom_lifespan(app):
        yield


app = FastAPI(
    title="OpenClaw PR Manager API",
    description="Automated Media Relations Engine with Supabase, Multi-AI, Scraping, and Gmail API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials="*" not in settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
API_V1_PREFIX = "/api/v1"
app.include_router(journalists_router, prefix=API_V1_PREFIX)
app.include_router(campaigns_router, prefix=API_V1_PREFIX)
app.include_router(outreach_router, prefix=API_V1_PREFIX)
app.include_router(scraping_router, prefix=API_V1_PREFIX)
app.include_router(ai_router, prefix=API_V1_PREFIX)
app.include_router(auth_router, prefix=API_V1_PREFIX)

# Import new routers
from api.routers.auth_users import router as auth_users_router
app.include_router(auth_users_router, prefix=API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "name": "OpenClaw PR Manager API",
        "status": "online",
        "docs": "/docs",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host=settings.HOST, port=settings.PORT, reload=settings.APP_DEBUG)

"""Scraping and AI Routers."""
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from services.scraping.enricher import MediaDiscoveryService
from services.ai.orchestrator import AIPitchOrchestrator
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.campaigns_repo import CampaignsRepository

# 1. Scraping Router
scraping_router = APIRouter(prefix="/scraping", tags=["Scraping & Discovery"])
discovery_service = MediaDiscoveryService()


class ScrapeRequest(BaseModel):
    keyword: str = Field(..., examples=["Artificial Intelligence"])
    country: str = Field(default="US", examples=["US"])
    limit: int = Field(default=10, ge=1, le=50)
    auto_save: bool = Field(default=True)


@scraping_router.post("/discover")
def discover_journalists(req: ScrapeRequest):
    """Scrape Google News to discover and enrich journalists for a given topic."""
    journalists = discovery_service.discover_journalists_by_keyword(
        keyword=req.keyword,
        country=req.country,
        limit=req.limit,
        auto_save=req.auto_save,
    )
    return {"keyword": req.keyword, "count": len(journalists), "journalists": journalists}


# 2. AI Router
ai_router = APIRouter(prefix="/ai", tags=["AI Engine"])
ai_orchestrator = AIPitchOrchestrator()
journalists_repo = JournalistsRepository()
campaigns_repo = CampaignsRepository()


class GeneratePitchRequest(BaseModel):
    journalist_id: str
    campaign_id: str
    model: str = Field(default="gpt-4o", examples=["gpt-4o"]) # gpt-4o or deepseek-chat
    pitch_type: str = Field(default="initial", examples=["initial"])


@ai_router.post("/generate-pitch")
def generate_pitch(req: GeneratePitchRequest):
    """Generate personalized pitch using GPT-4o or DeepSeek."""
    journalist = journalists_repo.get_by_id(req.journalist_id)
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")

    campaign = campaigns_repo.get_by_id(req.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    pitch = ai_orchestrator.generate_pitch(
        journalist=journalist,
        campaign=campaign,
        model=req.model,
        pitch_type=req.pitch_type,
    )
    return pitch

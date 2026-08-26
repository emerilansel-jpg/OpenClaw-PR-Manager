"""Campaigns API Router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from db.repositories.campaigns_repo import CampaignsRepository
from core.matching import JournalistMatcher
from services.ai.openai_service import OpenAIService

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])
campaigns_repo = CampaignsRepository()
matcher = JournalistMatcher()
ai_service = OpenAIService()


class CampaignCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, examples=["Launch of OpenClaw 2.0 AI"])
    story: str = Field(..., min_length=20, examples=["Today we announce the release of OpenClaw 2.0..."])
    target_beat: List[str] = Field(default_factory=list, examples=[["AI", "Open Source"]])
    target_outlets: List[str] = Field(default_factory=list, examples=[["TechCrunch", "VentureBeat"]])

    @field_validator("name", "story")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


@router.get("/")
def list_campaigns(limit: int = 50, offset: int = 0):
    return campaigns_repo.list_all(limit=limit, offset=offset)


@router.post("/")
def create_campaign(data: CampaignCreateSchema):
    """Create a new campaign and embed its story content."""
    payload = data.model_dump()
    story_text = f"{payload['name']}\n{payload['story']}"
    payload["story_embedding"] = ai_service.generate_embedding(story_text)
    return campaigns_repo.create(payload)


class CampaignUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    story: Optional[str] = Field(None, min_length=20)
    target_beat: Optional[List[str]] = None
    target_outlets: Optional[List[str]] = None
    status: Optional[str] = Field(None, pattern="^(draft|active|completed|archived)$")


@router.get("/{campaign_id}")
def get_campaign(campaign_id: str):
    c = campaigns_repo.get_by_id(campaign_id)
    if not c:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return c


@router.put("/{campaign_id}")
def update_campaign(campaign_id: str, data: CampaignUpdateSchema):
    """Update campaign details and regenerate story embedding if content changed."""
    existing = campaigns_repo.get_by_id(campaign_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Campaign not found")

    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if "story" in payload or "name" in payload:
        new_name = payload.get("name", existing.get("name", ""))
        new_story = payload.get("story", existing.get("story", ""))
        story_text = f"{new_name}\n{new_story}"
        payload["story_embedding"] = ai_service.generate_embedding(story_text)

    updated = campaigns_repo.update(campaign_id, payload)
    return updated


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: str):
    """Delete a campaign."""
    ok = campaigns_repo.delete(campaign_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"success": True, "deleted_id": campaign_id}


@router.post("/{campaign_id}/match")
def match_journalists(campaign_id: str, top_k: int = 20):
    """Find and rank journalists for this campaign using pgvector semantic + 4D score."""
    campaign = campaigns_repo.get_by_id(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    embedding = campaign.get("story_embedding")
    if not embedding:
        embedding = ai_service.generate_embedding(campaign.get("story", ""))

    matched = matcher.rank_journalists_for_campaign(campaign, query_embedding=embedding, top_k=top_k)
    return {"campaign_id": campaign_id, "count": len(matched), "matches": matched}

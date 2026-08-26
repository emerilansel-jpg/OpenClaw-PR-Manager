"""Journalists API Router."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from db.repositories.journalists_repo import JournalistsRepository
from core.scoring import calculate_4d_score
from services.ai.openai_service import OpenAIService

router = APIRouter(prefix="/journalists", tags=["Journalists"])
repo = JournalistsRepository()
ai_service = OpenAIService()


class JournalistCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, examples=["Jane Doe"])
    email: str = Field(..., min_length=3, max_length=255, examples=["jane.doe@techcrunch.com"])
    outlet: Optional[str] = Field(None, examples=["TechCrunch"])
    beat: List[str] = Field(default_factory=list, examples=[["AI", "Startups"]])
    location: Optional[str] = Field(None, examples=["San Francisco, CA"])
    twitter: Optional[str] = Field(None, examples=["@janedoe"])
    linkedin: Optional[str] = Field(None, examples=["linkedin.com/in/janedoe"])
    bio: Optional[str] = Field(None, examples=["Senior tech journalist covering early-stage AI startups."])
    email_status: str = Field(default="unverified", pattern="^(unverified|public|verified)$")
    email_source_url: Optional[str] = Field(
        None,
        examples=["https://publication.example/author/jane-doe"],
    )
    email_source_note: Optional[str] = Field(
        None,
        examples=["Public author page"],
    )

    @field_validator("name", "email")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        from services.scraping.validator import EmailValidator
        normalized = value.lower()
        if not EmailValidator.is_valid_syntax(normalized):
            raise ValueError("must be a valid email address")
        return normalized

    @model_validator(mode="after")
    def require_contact_evidence(self):
        if self.email_status in {"public", "verified"}:
            if not (self.email_source_url or self.email_source_note):
                raise ValueError("public or verified email requires a source URL or source note")
        return self


@router.get("/")
def list_journalists(
    beat: Optional[str] = Query(None),
    outlet: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    """List journalists with filtering and pagination."""
    return repo.list_all(beat=beat, outlet=outlet, search=search, limit=limit, offset=offset)


@router.post("/")
def create_journalist(data: JournalistCreateSchema):
    """Create a new journalist, calculate 4D scores, and generate vector embedding."""
    payload = data.model_dump()
    if repo.get_by_email(payload["email"]):
        raise HTTPException(status_code=409, detail="A journalist with this email already exists")
    
    # 4D scoring calculation
    scores = calculate_4d_score(payload, target_beats=payload.get("beat"))
    payload.update(scores)

    # Vector embedding generation
    embedding_text = f"{payload['name']} {payload.get('outlet', '')} {' '.join(payload.get('beat', []))} {payload.get('bio', '')}"
    payload["embedding"] = ai_service.generate_embedding(embedding_text)

    created = repo.create(payload)
    return created


class JournalistUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[str] = Field(None, min_length=3, max_length=255)
    outlet: Optional[str] = None
    beat: Optional[List[str]] = None
    location: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    bio: Optional[str] = None
    email_status: Optional[str] = Field(None, pattern="^(unverified|public|verified)$")
    email_source_url: Optional[str] = None
    email_source_note: Optional[str] = None


class BulkDeleteSchema(BaseModel):
    journalist_ids: List[str] = Field(..., min_length=1)


@router.get("/{journalist_id}")
def get_journalist(journalist_id: str):
    """Get single journalist by ID."""
    j = repo.get_by_id(journalist_id)
    if not j:
        raise HTTPException(status_code=404, detail="Journalist not found")
    return j


@router.put("/{journalist_id}")
def update_journalist(journalist_id: str, data: JournalistUpdateSchema):
    """Update journalist details and re-calculate 4D scores if beats changed."""
    existing = repo.get_by_id(journalist_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Journalist not found")

    payload = {k: v for k, v in data.model_dump().items() if v is not None}
    if "email" in payload and payload["email"] != existing.get("email"):
        dup = repo.get_by_email(payload["email"])
        if dup and dup["id"] != journalist_id:
            raise HTTPException(status_code=409, detail="A journalist with this email already exists")

    # Re-calculate 4D scores
    merged = {**existing, **payload}
    scores = calculate_4d_score(merged, target_beats=merged.get("beat"))
    payload.update(scores)

    updated = repo.update(journalist_id, payload)
    return updated


@router.delete("/{journalist_id}")
def delete_journalist(journalist_id: str):
    """Delete single journalist."""
    ok = repo.delete(journalist_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Journalist not found")
    return {"success": True, "deleted_id": journalist_id}


@router.post("/bulk-delete")
def bulk_delete_journalists(data: BulkDeleteSchema):
    """Delete multiple journalists at once."""
    deleted_count = 0
    failed_ids = []
    for j_id in data.journalist_ids:
        if repo.delete(j_id):
            deleted_count += 1
        else:
            failed_ids.append(j_id)
    return {
        "success": True,
        "deleted_count": deleted_count,
        "failed_ids": failed_ids,
    }

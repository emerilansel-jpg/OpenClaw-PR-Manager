"""Outreach and Tracking API Router."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.campaigns_repo import CampaignsRepository
from db.repositories.journalists_repo import JournalistsRepository
from services.email.sender import GmailSenderService
from services.email.tracker import EmailTrackerService
from services.scheduler.follow_up import FollowUpScheduler

router = APIRouter(prefix="/outreach", tags=["Outreach & Tracking"])
outreach_repo = OutreachRepository()
tracker_service = EmailTrackerService()
sender_service = GmailSenderService()
followup_scheduler = FollowUpScheduler()
campaigns_repo = CampaignsRepository()
journalists_repo = JournalistsRepository()


class OutreachCreateSchema(BaseModel):
    campaign_id: str = Field(min_length=1)
    journalist_id: str = Field(min_length=1)
    subject_line: str = Field(min_length=1, max_length=500)
    pitch_email: str = Field(min_length=1)
    sender_account_key: Optional[str] = Field(default=None, min_length=3, max_length=255)

    @field_validator("campaign_id", "journalist_id", "subject_line", "pitch_email")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


@router.get("/")
def list_outreach(campaign_id: Optional[str] = None):
    if campaign_id:
        return outreach_repo.list_by_campaign(campaign_id)
    return outreach_repo.list_all()


@router.post("/")
def create_outreach(data: OutreachCreateSchema):
    payload = data.model_dump()
    if not campaigns_repo.get_by_id(payload["campaign_id"]):
        raise HTTPException(status_code=404, detail="Campaign not found")
    journalist = journalists_repo.get_by_id(payload["journalist_id"])
    if not journalist:
        raise HTTPException(status_code=404, detail="Journalist not found")
    existing = outreach_repo.get_active_for_recipient(
        payload["campaign_id"],
        payload["journalist_id"],
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An active outreach already exists for this campaign and journalist",
        )
    return outreach_repo.create(payload)


@router.post("/{outreach_id}/send")
def send_outreach_pitch(outreach_id: str):
    """Send initial pitch via Gmail API."""
    outreach = outreach_repo.get_by_id(outreach_id)
    if not outreach:
        raise HTTPException(status_code=404, detail="Outreach not found")
    journalist = journalists_repo.get_by_id(outreach.get("journalist_id", ""))
    if not journalist or journalist.get("email_status") not in {"public", "verified"}:
        raise HTTPException(
            status_code=400,
            detail="Journalist email must have public or verified evidence before sending",
        )
    if not outreach.get("sender_account_key"):
        raise HTTPException(status_code=400, detail="Select a connected Gmail sender account")
    res = followup_scheduler.dispatch_initial_pitch(outreach_id, allow_simulation=False)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.get("/track/open/{token}")
def track_email_open(token: str):
    """1x1 transparent tracking pixel endpoint."""
    tracker_service.record_open(token)
    return Response(
        content=EmailTrackerService.TRANSPARENT_PIXEL_BYTES,
        media_type="image/gif",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@router.post("/{outreach_id}/reply")
def record_manual_reply(outreach_id: str):
    """Mark outreach as replied."""
    ok = tracker_service.record_reply(outreach_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Outreach not found")
    return {"success": True, "status": "replied"}


@router.post("/process-follow-ups")
def trigger_due_followups():
    """Trigger processing for all due follow-ups (3+7+7+14 days)."""
    results = followup_scheduler.process_due_follow_ups()
    return {"processed_count": len(results), "details": results}


from services.email.reply_sync import GmailReplySyncService

reply_sync_service = GmailReplySyncService(outreach_repo, journalists_repo)


@router.post("/sync-replies")
def sync_gmail_replies():
    """Poll Gmail threads to automatically detect incoming responses from journalists."""
    result = reply_sync_service.sync_replies()
    return result


@router.get("/stats")
def get_outreach_stats(campaign_id: Optional[str] = None):
    return outreach_repo.get_stats(campaign_id)

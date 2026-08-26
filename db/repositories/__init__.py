"""Database repositories package."""
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.campaigns_repo import CampaignsRepository
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.templates_repo import TemplatesRepository

__all__ = [
    "JournalistsRepository",
    "CampaignsRepository",
    "OutreachRepository",
    "TemplatesRepository",
]

"""Seed sample journalists, campaigns, and templates for instant testing."""
import logging
from config.settings import get_settings
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.campaigns_repo import CampaignsRepository
from db.repositories.outreach_repo import OutreachRepository
from core.scoring import calculate_4d_score

logger = logging.getLogger(__name__)

SAMPLE_JOURNALISTS = [
    {
        "name": "Demo Reporter One",
        "email": "reporter.one@example.com",
        "email_status": "unverified",
        "outlet": "Example Technology Desk",
        "beat": ["AI", "Startups", "Mobile Apps", "Software"],
        "location": "Demo record",
        "twitter": "",
        "linkedin": "",
        "bio": "Synthetic local-development record. Never use for real outreach.",
        "response_rate": 0.45,
        "relationship_score": 0.70,
    },
    {
        "name": "Demo Reporter Two",
        "email": "reporter.two@example.com",
        "email_status": "unverified",
        "outlet": "Example Business Desk",
        "beat": ["Enterprise", "Big Tech", "AI", "Venture Capital"],
        "location": "Demo record",
        "twitter": "",
        "linkedin": "",
        "bio": "Synthetic local-development record. Never use for real outreach.",
        "response_rate": 0.30,
        "relationship_score": 0.60,
    }
]

SAMPLE_CAMPAIGN = {
    "name": "OpenClaw PR 2.0 Global Release",
    "story": (
        "OpenClaw PR Manager introduces the first open-source autonomous PR and media relations engine. "
        "Built on Supabase pgvector and multi-model AI (GPT-4o & DeepSeek), it automatically discovers relevant journalists, "
        "calculates 4D alignment scores, and manages personalized outreach with scheduled 3+7+7+14 follow-up sequences."
    ),
    "target_beat": ["AI", "Teknologi", "Startups", "Open Source"],
    "target_outlets": ["TechCrunch", "The Verge", "Kompas", "Katadata", "Bloomberg"],
    "status": "draft",
}


def seed_initial_data():
    """Populate synthetic records only when explicitly enabled for local use."""
    settings = get_settings()
    if not settings.SEED_DEMO_DATA:
        return
    if settings.is_supabase_configured:
        logger.warning("SEED_DEMO_DATA was ignored because Supabase is configured")
        return
    j_repo = JournalistsRepository()
    c_repo = CampaignsRepository()
    o_repo = OutreachRepository()

    # Seed Journalists if empty
    existing_j = j_repo.list_all(limit=10)
    if not existing_j:
        logger.info("Seeding sample journalists with 4D scoring...")
        for j in SAMPLE_JOURNALISTS:
            scores = calculate_4d_score(j, target_beats=["AI", "Startups"])
            j.update(scores)
            j_repo.create(j)

    # Seed Campaign if empty
    existing_c = c_repo.list_all(limit=5)
    if not existing_c:
        logger.info("Seeding sample campaign...")
        c_repo.create(SAMPLE_CAMPAIGN)

    logger.info("Seed data ready.")

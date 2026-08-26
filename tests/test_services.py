"""Unit tests for services (Validator, PromptBuilder, Scheduler)."""
from datetime import datetime, timezone
from services.scraping.validator import EmailValidator
from services.ai.prompt_builder import PromptBuilder
from services.scheduler.follow_up import FollowUpScheduler, FOLLOW_UP_INTERVALS
from services.email.sender import GmailSenderService
from services.email.tracker import EmailTrackerService
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.templates_repo import TemplatesRepository


def test_email_validator():
    # Valid syntax
    assert EmailValidator.is_valid_syntax("reporter@bloomberg.com") is True
    assert EmailValidator.is_valid_syntax("jane.doe+news@kompas.co.id") is True

    # Invalid syntax
    assert EmailValidator.is_valid_syntax("invalid-email") is False
    assert EmailValidator.is_valid_syntax("@missingusername.com") is False

    # Disposable domain detection
    val_res = EmailValidator.validate("test@tempmail.com")
    assert val_res["valid"] is False
    assert "Disposable" in val_res["reason"]


def test_prompt_builder():
    tpl = "Hello {{journalist_name}}, I loved your work at {{outlet}} covering {{beat}}."
    ctx = {
        "journalist_name": "Jane",
        "outlet": "TechCrunch",
        "beat": ["AI", "Startups"]
    }
    rendered = PromptBuilder.render(tpl, ctx)
    assert "Hello Jane" in rendered
    assert "TechCrunch" in rendered
    assert "AI, Startups" in rendered


def test_followup_intervals_formula():
    # Verify 3+7+7+14 formula
    assert FOLLOW_UP_INTERVALS[1] == 3   # Stage 1 -> F1
    assert FOLLOW_UP_INTERVALS[2] == 7   # F1 -> F2
    assert FOLLOW_UP_INTERVALS[3] == 7   # F2 -> F3
    assert FOLLOW_UP_INTERVALS[4] == 14  # F3 -> Breakup

    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    next_f1 = FollowUpScheduler.calculate_next_follow_up(1, base_time=base)
    assert (next_f1 - base).days == 3

    next_f2 = FollowUpScheduler.calculate_next_follow_up(2, base_time=base)
    assert (next_f2 - base).days == 7

    next_f4 = FollowUpScheduler.calculate_next_follow_up(4, base_time=base)
    assert (next_f4 - base).days == 14


def test_html_email_escapes_untrusted_copy():
    message = GmailSenderService().build_message(
        "recipient@example.com",
        "Safe subject",
        "Hello <script>alert('x')</script>\nNext line",
    )
    html_part = message.get_payload()[1].get_payload(decode=True).decode()
    assert "<script>" not in html_part
    assert "&lt;script&gt;" in html_part
    assert "<br>Next line" in html_part


def test_template_selection_prefers_requested_model():
    template = TemplatesRepository().get_default(pitch_type="initial", model="deepseek-chat")
    assert template["model"] == "deepseek-chat"


def test_reply_tracking_is_idempotent():
    journalists = JournalistsRepository()
    outreach = OutreachRepository()
    journalists._local_store.clear()
    outreach._local_store.clear()
    journalist = journalists.create({
        "name": "Reply Test",
        "email": "reply-test@example.com",
        "history_score": 0.5,
        "relationship_score": 0.5,
    })
    item = outreach.create({"journalist_id": journalist["id"], "status": "sent"})
    tracker = EmailTrackerService(outreach, journalists)

    assert tracker.record_reply(item["id"]) is True
    first_history_score = journalists.get_by_id(journalist["id"])["history_score"]
    assert tracker.record_reply(item["id"]) is True
    assert journalists.get_by_id(journalist["id"])["history_score"] == first_history_score

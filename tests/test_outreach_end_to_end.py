"""End-to-end local tests for outreach delivery and follow-up state changes."""

import asyncio
from datetime import datetime, timedelta, timezone

from api.lifecyle import process_follow_ups_job
from db.repositories.campaigns_repo import CampaignsRepository
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.outreach_repo import OutreachRepository
from services.email.email_queue import EmailQueue, EmailTask
from services.email.tracker import EmailTrackerService
from services.scheduler.follow_up import FollowUpScheduler


class RecordingSender:
    def __init__(self, simulated=False):
        self.calls = []
        self.simulated = simulated

    def send_pitch(self, **kwargs):
        self.calls.append(kwargs)
        sequence = len(self.calls)
        return {
            "success": True,
            "simulated": self.simulated,
            "gmail_message_id": f"sim-{sequence}",
            "gmail_thread_id": "thread-1",
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }


class FollowUpAI:
    def generate_pitch(self, **kwargs):
        return {"pitch_email": f"Generated {kwargs['pitch_type']} body"}


def local_repositories():
    journalists = object.__new__(JournalistsRepository)
    campaigns = object.__new__(CampaignsRepository)
    outreach = object.__new__(OutreachRepository)
    journalists.client = campaigns.client = outreach.client = None
    journalists._local_store.clear()
    campaigns._local_store.clear()
    outreach._local_store.clear()
    return journalists, campaigns, outreach


def test_full_outreach_sequence_sends_once_per_stage():
    journalists, campaigns, outreach = local_repositories()
    journalist = journalists.create({"name": "Reporter", "email": "reporter@example.com"})
    campaign = campaigns.create({"name": "Launch", "story": "A sufficiently detailed launch story for testing."})
    item = outreach.create({
        "campaign_id": campaign["id"],
        "journalist_id": journalist["id"],
        "subject_line": "A relevant launch",
        "pitch_email": "Initial pitch body",
        "sender_account_key": "pr.sender@gmail.com",
    })
    sender = RecordingSender()
    scheduler = FollowUpScheduler(outreach, campaigns, journalists, FollowUpAI(), sender)

    first = scheduler.dispatch_initial_pitch(item["id"])
    duplicate = scheduler.dispatch_initial_pitch(item["id"])
    assert first["success"] is True and first["already_sent"] is False
    assert duplicate["success"] is True and duplicate["already_sent"] is True
    assert len(sender.calls) == 1

    for expected_sequence in (2, 3, 4, 5):
        outreach.update(item["id"], {
            "next_follow_up": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat(),
        })
        result = scheduler.process_due_follow_ups()
        assert result == [{
            "outreach_id": item["id"],
            "sequence": expected_sequence,
            "recipient": journalist["email"],
            "success": True,
            "simulated": False,
        }]

    final = outreach.get_by_id(item["id"])
    assert final["follow_up_sequence"] == 5
    assert final["status"] == "completed_no_reply"
    assert final["next_follow_up"] is None
    assert len(sender.calls) == 5
    assert {call["user_id"] for call in sender.calls} == {"pr.sender@gmail.com"}
    assert outreach.get_stats()["sent"] == 1


def test_simulated_initial_send_never_schedules_live_follow_up():
    journalists, campaigns, outreach = local_repositories()
    journalist = journalists.create({"name": "Reporter", "email": "simulation@example.com"})
    campaign = campaigns.create({"name": "Launch", "story": "A sufficiently detailed launch story for testing."})
    item = outreach.create({
        "campaign_id": campaign["id"],
        "journalist_id": journalist["id"],
        "subject_line": "Simulation",
        "pitch_email": "This must remain a simulation",
    })
    scheduler = FollowUpScheduler(
        outreach,
        campaigns,
        journalists,
        FollowUpAI(),
        RecordingSender(simulated=True),
    )

    result = scheduler.dispatch_initial_pitch(item["id"])
    stored = outreach.get_by_id(item["id"])
    assert result["success"] is True and result["simulated"] is True
    assert stored["status"] == "simulated"
    assert stored["next_follow_up"] is None
    assert outreach.get_stats()["sent"] == 0
    assert scheduler.process_due_follow_ups() == []


def test_late_open_does_not_revive_terminal_status():
    journalists, _, outreach = local_repositories()
    journalist = journalists.create({"name": "Reporter", "email": "terminal@example.com"})
    item = outreach.create({"journalist_id": journalist["id"], "status": "unsubscribed"})
    tracker = EmailTrackerService(outreach, journalists)

    assert tracker.record_open(item["tracking_token"]) is True
    assert outreach.get_by_id(item["id"])["status"] == "unsubscribed"


def test_background_job_constructs_scheduler(monkeypatch):
    class FakeScheduler:
        def process_due_follow_ups(self):
            return [{"outreach_id": "one", "success": True}]

    monkeypatch.setattr("services.scheduler.follow_up.FollowUpScheduler", FakeScheduler)
    assert process_follow_ups_job() == {
        "processed": 1,
        "details": [{"outreach_id": "one", "success": True}],
    }


def test_email_queue_uses_gmail_sender_contract(monkeypatch):
    sender = RecordingSender()
    monkeypatch.setattr("services.email.sender.GmailSenderService", lambda: sender)
    queue = object.__new__(EmailQueue)
    task = EmailTask(
        outreach_id="out-1",
        to_email="queue@example.com",
        subject="Queue subject",
        body_html="Fallback body",
        body_text="Plain body",
        tracking_token="track-1",
        thread_id="thread-1",
    )

    assert asyncio.run(queue._send_email(task)) is True
    assert sender.calls[0]["to_email"] == "queue@example.com"
    assert sender.calls[0]["body_text"] == "Plain body"
    assert sender.calls[0]["thread_id"] == "thread-1"

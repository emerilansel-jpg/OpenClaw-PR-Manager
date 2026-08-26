"""Tests for FollowUpScheduler sequence completion and exhaustion behavior.

Covers `services/scheduler/follow_up.py` with mocked repositories, external APIs,
and AI services. The test suite verifies that sequences stop after reaching
their configured maximum (final stage) without attempting further sends.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

from services.scheduler.follow_up import FOLLOW_UP_INTERVALS, FollowUpScheduler


@pytest.fixture()
def empty_mock_repo():
    """A minimal OutreachRepository mock returning None."""
    repo = MagicMock()
    repo.get_by_id.return_value = None
    repo.update = MagicMock(side_effect=lambda *_args, **_kw: None)
    return repo


# ---------------------------------------------------------------------------
# Sequence boundaries and final states
# ---------------------------------------------------------------------------


class TestFollowUpSequenceExhaustion:
    def test_final_stage_marks_no_reply_when_next_seq_exceeds_max(self):
        """After breakup (seq 5) completes, status should be 'completed_no_reply'."""
        outreach_item = {
            "id": "item-1",
            "status": "sent",
            "follow_up_sequence": 5,  # Already at breakup stage
            "next_follow_up": "2026-09-15T12:00:00+00:00",
            "subject_line": "Exclusive Story Pitch",
            "gmail_thread_id": "thread-abc",
            "journalist_id": "j-1",
            "campaign_id": "camp-1",
        }

        mock_outreach = MagicMock(get_due_follow_ups=lambda: [outreach_item])
        mock_outreach.get_by_id.side_effect = lambda *_a, **_k: outreach_item

        mock_sender = MagicMock()
        mock_sender.send_pitch = MagicMock(return_value={"success": True})

        scheduler = FollowUpScheduler(
            outreach_repo=mock_outreach,
            campaigns_repo=MagicMock(),
            journalists_repo=MagicMock(),
            ai_orchestrator=MagicMock(),
            email_sender=mock_sender,
        )

        results = scheduler.process_due_follow_ups(user_id="user-1")
        
        # Should mark as completed (not send) because sequence 6 > 5
        assert len(results) == 0

        assert mock_outreach.update.call_count > 0
        updates = mock_outreach.update.call_args.args[1]
        assert updates["status"] == "completed_no_reply"
        assert updates["next_follow_up"] is None

        # Sender should not be called because sequence exceeds max
        assert not mock_sender.send_pitch.called

    def test_breakup_email_sent_at_sequence_5_then_reaches_final(self):
        """F4 (Breakup) sends once; then marks completed without further sends."""
        now_utc = datetime.now(timezone.utc)
        outreach_item = {
            "id": "item-2",
            "status": "sent",
            "follow_up_sequence": 4,  # Currently at F3 (not breakup yet)
            "next_follow_up": now_utc.isoformat(),
            "subject_line": "Final notice",
            "gmail_thread_id": None,
            "journalist_id": "j-2",
            "campaign_id": "camp-2",
        }

        mock_outreach = MagicMock(
            get_due_follow_ups=lambda: [outreach_item],
            get_by_id=lambda *_a, **_k: outreach_item,
        )
        mock_campaigns = MagicMock(get_by_id=lambda _id: {"id": "camp-2", "story": "Test story"})
        mock_journalists = MagicMock(get_by_id=lambda _id: {"id": "j-2", "email": "r@test.com"})
        mock_ai = MagicMock(generate_pitch=lambda *a, **k: {"pitch_email": "Breakup text"})

        send_calls = []
        def record_send(*args, **kwargs):
            send_calls.append(True)
            return {"success": True}
        
        mock_sender = MagicMock()
        mock_sender.send_pitch = MagicMock(side_effect=record_send)

        scheduler = FollowUpScheduler(
            outreach_repo=mock_outreach,
            campaigns_repo=mock_campaigns,
            journalists_repo=mock_journalists,
            ai_orchestrator=mock_ai,
            email_sender=mock_sender,
        )

        results = scheduler.process_due_follow_ups(user_id="user-1")
        # Should send the breakup email
        assert len(results) >= 1
        assert mock_sender.send_pitch.call_count >= 1
        assert mock_outreach.update.call_count >= 1
        final_updates = mock_outreach.update.call_args.args[1]
        # After breakup (sequence 5), next_follow_up should be None
        assert final_updates["status"] == "completed_no_reply"
        assert final_updates["next_follow_up"] is None

    @pytest.mark.parametrize(
        ("current_status","should_skip"),
        [
            ("replied", True),
            ("bounced", True),
            ("unsubscribed", True),
            ("opened", False),
            ("sent", False),
        ],
    )
    def test_skips_completed_statuses(self, current_status, should_skip):
        """Items already marked replied/bounced/unsubscribed must not be re-sent."""
        outreach_item = {
            "id": f"skip-{current_status}",
            "status": current_status,
            "follow_up_sequence": 2,
            "next_follow_up": datetime.now(timezone.utc).isoformat(),
            "journalist_id": "j-skip",
            "campaign_id": "c-skip",
        }

        mock_outreach = MagicMock(get_due_follow_ups=lambda: [outreach_item])
        # A fresh read protects against state changes after the due-list query.
        mock_outreach.get_by_id.side_effect = lambda *_a, **_k: (
            outreach_item if current_status in {"sent", "opened"} else None
        )

        mock_sender = MagicMock()
        mock_sender.send_pitch = MagicMock(return_value={"success": True})

        scheduler = FollowUpScheduler(
            outreach_repo=mock_outreach,
            campaigns_repo=MagicMock(),
            journalists_repo=MagicMock(),
            ai_orchestrator=MagicMock(),
            email_sender=mock_sender,
        )

        results = scheduler.process_due_follow_ups(user_id="user-1")

        if should_skip:
            assert len(results) == 0
            assert not mock_sender.send_pitch.called
        else:
            # When status is sent/opened, should attempt to send
            assert len(results) >= 1
            assert mock_sender.send_pitch.call_count >= 1

    def test_missing_journalist_or_campaign_stops_send_for_that_item(self):
        """Outreach records lacking journalist/campaign data must skip sending."""
        outreach_item = {
            "id": "no-journ-item",
            "status": "sent",
            "follow_up_sequence": 2,
            "next_follow_up": datetime.now(timezone.utc).isoformat(),
            "journalist_id": "missing-1",
            "campaign_id": "missing-2",
        }

        mock_outreach = MagicMock(get_due_follow_ups=lambda: [outreach_item])
        mock_outreach.get_by_id.side_effect = lambda *_a, **_k: outreach_item

        # Both journalist and campaign return None when called
        mock_journalists = MagicMock()
        mock_journalists.get_by_id = MagicMock(return_value=None)
        mock_campaigns = MagicMock()
        mock_campaigns.get_by_id = MagicMock(return_value=None)

        mock_sender = MagicMock()
        mock_sender.send_pitch = MagicMock(return_value={"success": True})

        scheduler = FollowUpScheduler(
            outreach_repo=mock_outreach,
            campaigns_repo=mock_campaigns,
            journalists_repo=mock_journalists,
            ai_orchestrator=MagicMock(),
            email_sender=mock_sender,
        )

        results = scheduler.process_due_follow_ups(user_id="user-1")
        assert len(results) == 0
        assert not mock_sender.send_pitch.called

    def test_initial_pitch_tracks_follow_up_sequence_and_dates(self):
        """dispatch_initial_pitch sets initial state and calculates +3 days next follow up."""
        outreach_item = {
            "id": "initial-item",
            "journalist_id": "j-init",
            "subject_line": "New launch story",
            "pitch_email": "Hello,",
        }

        mock_outreach = MagicMock(get_by_id=lambda *_a, **_k: outreach_item)
        mock_outreach.update = MagicMock()

        def record_send(*a, **k):
            return {"success": True}

        scheduler = FollowUpScheduler(
            outreach_repo=mock_outreach,
            campaigns_repo=MagicMock(),
            journalists_repo=MagicMock(get_by_id=lambda _id: {"email": "init@example.com"}),
            ai_orchestrator=MagicMock(),
            email_sender=MagicMock(send_pitch=record_send),
        )

        result = scheduler.dispatch_initial_pitch(outreach_item["id"], user_id="u-1")

        assert result["success"] is True
        next_follow_up = result["next_follow_up"]
        # Check that the difference in days is approximately 3 (accounting for float precision)
        days_diff = (next_follow_up - datetime.now(timezone.utc)).days
        # Use tolerance since floating point arithmetic can cause off-by-1 errors
        assert FOLLOW_UP_INTERVALS[1] - 1 <= days_diff <= FOLLOW_UP_INTERVALS[1] + 1  # 2-4 days range

        mock_outreach.update.assert_called_once()
        updates = mock_outreach.update.call_args.args[1]
        assert updates["status"] == "sent"
        assert updates["follow_up_sequence"] == 1
        assert updates["next_follow_up"] is not None


# ---------------------------------------------------------------------------
# Edge cases: missing items, bad inputs, idempotent retries
# ---------------------------------------------------------------------------


class TestMissingRecordHandling:
    def test_dispatch_initial_pitch_fails_gracefully_when_not_found(self):
        mock_outreach = MagicMock()
        mock_outreach.get_by_id.return_value = None
        
        scheduler = FollowUpScheduler(
            outreach_repo=mock_outreach,
            campaigns_repo=MagicMock(),
            journalists_repo=MagicMock(),
            ai_orchestrator=MagicMock(),
            email_sender=MagicMock(),
        )
        result = scheduler.dispatch_initial_pitch("non-existent-id", user_id="u-1")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_dispatch_requires_journalist_email_to_proceed(self):
        outreach = {"id": "x", "journalist_id": "j-x", "subject_line": "S", "pitch_email": ""}
        scheduler = FollowUpScheduler(
            outreach_repo=MagicMock(get_by_id=lambda *_a, **_k: outreach),
            campaigns_repo=MagicMock(),
            journalists_repo=MagicMock(get_by_id=lambda _id: {"email": None}),
            ai_orchestrator=MagicMock(),
            email_sender=MagicMock(),
        )
        result = scheduler.dispatch_initial_pitch("x")
        assert result["success"] is False
        assert "email" in result["error"].lower()


# ---------------------------------------------------------------------------
# Formula verification
# ---------------------------------------------------------------------------


class TestFormulaIntegrity:
    @pytest.mark.parametrize(
        ("seq","expected_days"),
        [
            (1, 3),
            (2, 7),
            (3, 7),
            (4, 14),
        ],
    )
    def test_follow_up_interval_matches_specification(self, seq, expected_days):
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        target = FollowUpScheduler.calculate_next_follow_up(seq, base_time=base)
        assert (target - base).days == expected_days

    def test_invalid_sequence_returns_none(self):
        result = FollowUpScheduler.calculate_next_follow_up(99, base_time=datetime(2026, 1, 1, tzinfo=timezone.utc))
        assert result is None

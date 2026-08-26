"""Unit tests for Gmail disconnect and reply sync services."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from api.main import app
from services.email.gmail_auth import GmailOAuthManager
from services.email.reply_sync import GmailReplySyncService
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.journalists_repo import JournalistsRepository

client = TestClient(app)


def test_disconnect_gmail_account():
    auth_mgr = GmailOAuthManager()
    # Save a test token
    test_key = "test_disconnect_user@example.com"
    auth_mgr.save_tokens(test_key, {
        "user_id": test_key,
        "access_token": "mock_token",
        "email_address": test_key,
    })
    assert auth_mgr.has_connected_account(test_key) is True

    # Call disconnect API
    res = client.delete(f"/api/v1/auth/google/accounts/{test_key}")
    assert res.status_code == 200
    assert res.json()["success"] is True
    assert auth_mgr.has_connected_account(test_key) is False

    # Second call should return 404
    res_404 = client.delete(f"/api/v1/auth/google/accounts/{test_key}")
    assert res_404.status_code == 404


def test_reply_sync_endpoint():
    res = client.post("/api/v1/outreach/sync-replies")
    assert res.status_code == 200
    data = res.json()
    assert "checked_threads" in data
    assert "replies_detected" in data


def test_reply_sync_service_detection():
    o_repo = OutreachRepository()
    o_repo.client = None
    o_repo._local_store.clear()

    j_repo = JournalistsRepository()
    j_repo.client = None
    j_repo._local_store.clear()

    auth_mgr = GmailOAuthManager()
    auth_mgr.client = None

    # Create dummy journalist & outreach
    j = j_repo.create({
        "name": "Reply Tester",
        "email": "reply.tester@outlet.com",
        "outlet": "Outlet Daily",
    })
    o = o_repo.create({
        "campaign_id": "test_camp_123",
        "journalist_id": j["id"],
        "subject_line": "Pitch story",
        "pitch_email": "Pitch content",
        "status": "sent",
        "gmail_message_id": "real_msg_123",
        "gmail_thread_id": "thread_12345",
        "sender_account_key": "sender@myagency.com",
    })

    # Mock Gmail API thread response with an incoming reply from the journalist
    mock_service = MagicMock()
    mock_thread_data = {
        "messages": [
            {
                "id": "msg_1",
                "payload": {"headers": [{"name": "From", "value": "sender@myagency.com"}]},
            },
            {
                "id": "msg_2",
                "payload": {"headers": [{"name": "From", "value": "reply.tester@outlet.com"}]},
                "snippet": "Thanks, I would love to cover this story!",
            }
        ]
    }
    mock_service.users().threads().get().execute.return_value = mock_thread_data

    with patch("services.email.reply_sync.build", return_value=mock_service), \
         patch.object(auth_mgr, "get_credentials", return_value=MagicMock()):
        
        sync_svc = GmailReplySyncService(
            outreach_repo=o_repo,
            journalists_repo=j_repo,
            auth_manager=auth_mgr,
        )
        result = sync_svc.sync_replies()
        assert result["replies_detected"] >= 1

        # Outreach status should now be updated to replied
        updated_o = o_repo.get_by_id(o["id"])
        assert updated_o["status"] == "replied"

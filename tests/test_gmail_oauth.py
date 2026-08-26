"""Tests for Gmail OAuth2 authorization URL generation and token storage.

All Google interactions are mocked -- no real credentials or network calls.
Covers `services/email/gmail_auth.py` and `api/routers/auth.py` behavior.
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from services.email.gmail_auth import GmailOAuthManager, SCOPES
from services.email.sender import GmailSenderService


def _make_manager(client=None):
    """Build a GmailOAuthManager with a controlled Supabase client (or None)."""
    manager = GmailOAuthManager.__new__(GmailOAuthManager)
    manager.client = client
    # __init__ normally just loads settings + client; replicate the settings
    # part so tests can patch it via the override_settings fixtures.
    from config.settings import get_settings

    manager.settings = get_settings()
    return manager


# ---------------------------------------------------------------------------
# Authorization URL generation
# ---------------------------------------------------------------------------


class TestAuthorizationUrl:
    def test_returns_none_when_gmail_not_configured(self, gmail_unconfigured_settings):
        manager = _make_manager()
        assert manager.get_authorization_url() is None

    def test_returns_none_when_client_id_is_placeholder(self, override_settings):
        # Production guard: placeholder values from the sample .env must be
        # treated as "not configured".
        override_settings(
            GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com",
            GOOGLE_CLIENT_SECRET="qa-test-client-secret",
        )
        manager = _make_manager()
        assert manager.get_authorization_url() is None

    def test_url_contains_required_oauth_params(self, gmail_configured_settings):
        manager = _make_manager()
        url = manager.get_authorization_url()

        assert url is not None
        assert url.startswith("https://accounts.google.com/o/oauth2/auth")
        assert "client_id=qa-test-client-id.apps.googleusercontent.com" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url
        assert "include_granted_scopes=true" in url
        assert "gmail.send" in url  # requested scope is encoded in the URL

    def test_login_endpoint_returns_url_when_configured(self, gmail_configured_settings):
        manager = _make_manager()
        with patch("api.routers.auth.auth_mgr", manager):
            from api.main import app

            client = TestClient(app)
            res = client.get("/api/v1/auth/google/login")
            assert res.status_code == 200
            assert res.json()["authorization_url"].startswith("https://accounts.google.com/")

    def test_login_endpoint_400_when_not_configured(self, gmail_unconfigured_settings):
        manager = _make_manager()
        with patch("api.routers.auth.auth_mgr", manager):
            from api.main import app

            client = TestClient(app)
            res = client.get("/api/v1/auth/google/login")
            assert res.status_code == 400
            assert "not configured" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Code exchange and token storage
# ---------------------------------------------------------------------------


class TestExchangeCodeForTokens:
    def test_exchange_returns_none_when_not_configured(self, gmail_unconfigured_settings):
        manager = _make_manager()
        assert manager.exchange_code_for_tokens("any-code") is None

    def test_exchange_saves_tokens_locally(self, gmail_configured_settings, clean_gmail_token_store):
        manager = _make_manager(client=None)

        fake_creds = SimpleNamespace(
            token="qa-access-token",
            refresh_token="qa-refresh-token",
            expiry=datetime(2026, 9, 1, tzinfo=timezone.utc),
            scopes=list(SCOPES),
        )
        fake_flow = MagicMock()
        fake_flow.credentials = fake_creds

        with patch("services.email.gmail_auth.Flow") as flow_cls:
            flow_cls.from_client_config.return_value = fake_flow
            result = manager.exchange_code_for_tokens("qa-auth-code", user_id="user-1")

        fake_flow.fetch_token.assert_called_once_with(code="qa-auth-code")
        assert result is not None
        assert result["access_token"] == "qa-access-token"
        assert result["refresh_token"] == "qa-refresh-token"
        assert result["token_expiry"] == "2026-09-01T00:00:00+00:00"
        # Stored in the local fallback store under the given user id
        stored = GmailOAuthManager._local_tokens["user-1"]
        assert stored["access_token"] == "qa-access-token"

    def test_exchange_failure_returns_none_and_stores_nothing(
        self, gmail_configured_settings, clean_gmail_token_store
    ):
        manager = _make_manager(client=None)
        fake_flow = MagicMock()
        fake_flow.fetch_token.side_effect = Exception("invalid_grant")

        with patch("services.email.gmail_auth.Flow") as flow_cls:
            flow_cls.from_client_config.return_value = fake_flow
            assert manager.exchange_code_for_tokens("bad-code") is None

        assert GmailOAuthManager._local_tokens == {}

    def test_exchange_uses_verified_google_email_as_account_key(
        self, gmail_configured_settings, clean_gmail_token_store
    ):
        manager = _make_manager(client=None)
        fake_creds = SimpleNamespace(
            token="qa-access-token",
            refresh_token="qa-refresh-token",
            expiry=None,
            scopes=list(SCOPES),
        )
        fake_flow = MagicMock(credentials=fake_creds)

        with patch("services.email.gmail_auth.Flow") as flow_cls, patch.object(
            manager,
            "_fetch_authorized_email",
            return_value="Sender.Account@Gmail.com",
        ):
            flow_cls.from_client_config.return_value = fake_flow
            result = manager.exchange_code_for_tokens("qa-auth-code")

        assert result["email_address"] == "sender.account@gmail.com"
        assert "sender.account@gmail.com" in GmailOAuthManager._local_tokens


# ---------------------------------------------------------------------------
# Token persistence (Supabase upsert vs local fallback)
# ---------------------------------------------------------------------------


class TestTokenStorage:
    def _token_data(self):
        return {
            "user_id": "user-1",
            "access_token": "qa-access-token",
            "refresh_token": "qa-refresh-token",
            "token_expiry": "2026-09-01T00:00:00+00:00",
            "scopes": list(SCOPES),
            "email_address": "me",
        }

    def test_save_tokens_upserts_to_supabase(self, gmail_configured_settings, mock_supabase_client):
        manager = _make_manager(client=mock_supabase_client)
        manager.save_tokens("user-1", self._token_data())

        table = mock_supabase_client.table
        table.assert_called_once_with("gmail_tokens")
        upsert_call = table.return_value.upsert.call_args
        row = upsert_call.args[0]
        assert row["account_key"] == "user-1"
        assert row["access_token"] == "qa-access-token"
        assert row["refresh_token"] == "qa-refresh-token"
        assert upsert_call.kwargs.get("on_conflict") == "account_key"
        table.return_value.upsert.return_value.execute.assert_called_once()
        # Must not fall through to the local store when Supabase succeeds
        assert "user-1" not in GmailOAuthManager._local_tokens

    def test_save_tokens_falls_back_to_local_when_supabase_raises(
        self, gmail_configured_settings, clean_gmail_token_store, mock_supabase_client
    ):
        mock_supabase_client.table.side_effect = Exception("connection refused")
        manager = _make_manager(client=mock_supabase_client)

        manager.save_tokens("user-1", self._token_data())
        assert GmailOAuthManager._local_tokens["user-1"]["access_token"] == "qa-access-token"

    def test_save_tokens_local_when_no_client(self, gmail_configured_settings, clean_gmail_token_store):
        manager = _make_manager(client=None)
        manager.save_tokens("user-1", self._token_data())
        assert GmailOAuthManager._local_tokens["user-1"]["refresh_token"] == "qa-refresh-token"

    def test_account_listing_never_exposes_tokens(
        self, gmail_configured_settings, clean_gmail_token_store
    ):
        manager = _make_manager(client=None)
        manager.save_tokens("sender@gmail.com", {
            "access_token": "secret-access-token",
            "refresh_token": "secret-refresh-token",
            "email_address": "sender@gmail.com",
        })

        accounts = manager.list_connected_accounts()
        assert accounts == [{
            "account_key": "sender@gmail.com",
            "email_address": "sender@gmail.com",
            "token_expiry": None,
            "created_at": None,
            "updated_at": None,
        }]
        assert "access_token" not in accounts[0]
        assert "refresh_token" not in accounts[0]


# ---------------------------------------------------------------------------
# Credential retrieval / refresh
# ---------------------------------------------------------------------------


class TestGetCredentials:
    def test_returns_none_when_no_tokens_anywhere(self, gmail_configured_settings, clean_gmail_token_store):
        manager = _make_manager(client=None)
        assert manager.get_credentials("unknown-user") is None

    def test_builds_credentials_from_local_store(self, gmail_configured_settings, clean_gmail_token_store):
        manager = _make_manager(client=None)
        manager.save_tokens("user-1", {
            "user_id": "user-1",
            "access_token": "qa-access-token",
            "refresh_token": "qa-refresh-token",
            "token_expiry": None,
            "scopes": list(SCOPES),
        })

        creds = manager.get_credentials("user-1")
        assert creds is not None
        assert creds.token == "qa-access-token"
        assert creds.refresh_token == "qa-refresh-token"

    def test_prefers_supabase_tokens_over_local(
        self, gmail_configured_settings, clean_gmail_token_store, mock_supabase_client
    ):
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.execute.return_value = (
            SimpleNamespace(data=[{
                "access_token": "supabase-access-token",
                "refresh_token": "supabase-refresh-token",
                "token_expiry": None,
                "email_address": "me",
            }])
        )
        manager = _make_manager(client=mock_supabase_client)
        # Local store has a different (stale) token that must be ignored
        GmailOAuthManager._local_tokens["user-1"] = {
            "access_token": "stale-local-token",
            "refresh_token": "stale",
        }

        creds = manager.get_credentials("user-1")
        assert creds.token == "supabase-access-token"

    def test_refresh_failure_returns_none(self, gmail_configured_settings, clean_gmail_token_store):
        manager = _make_manager(client=None)
        manager.save_tokens("user-1", {
            "user_id": "user-1",
            "access_token": "expired-token",
            "refresh_token": "qa-refresh-token",
            "token_expiry": None,
        })

        with patch("services.email.gmail_auth.Credentials") as creds_cls:
            expired = MagicMock()
            expired.expired = True
            expired.refresh_token = "qa-refresh-token"
            expired.refresh.side_effect = Exception("token revoked")
            creds_cls.return_value = expired

            assert manager.get_credentials("user-1") is None


# ---------------------------------------------------------------------------
# Sender behavior around credentials
# ---------------------------------------------------------------------------


class TestSenderCredentialHandling:
    def test_send_pitch_simulated_when_no_credentials(self, gmail_unconfigured_settings, clean_gmail_token_store):
        sender = GmailSenderService()
        res = sender.send_pitch("reporter@example.com", "Subject", "Body text")
        assert res["success"] is True
        assert res["simulated"] is True
        assert res["gmail_message_id"].startswith("sim_")

    def test_real_send_fails_when_selected_account_is_not_connected(
        self, gmail_unconfigured_settings, clean_gmail_token_store
    ):
        sender = GmailSenderService()
        res = sender.send_pitch(
            "reporter@example.com",
            "Subject",
            "Body text",
            user_id="missing@gmail.com",
            allow_simulation=False,
        )
        assert res["success"] is False
        assert res["simulated"] is False
        assert "not connected" in res["error"]

    def test_send_pitch_reports_failure_when_gmail_api_raises(
        self, gmail_configured_settings, clean_gmail_token_store
    ):
        from services.email.gmail_auth import GmailOAuthManager
        manager = _make_manager()
        manager.save_tokens("user-1", {
            "user_id": "user-1",
            "access_token": "qa-access-token",
            "refresh_token": "qa-refresh-token",
            "token_expiry": None,
        })
        
        # Get credentials properly
        fake_creds = SimpleNamespace(
            token="qa-access-token",
            refresh_token="qa-refresh-token",
            expiry=None,
        )
        with patch.object(GmailOAuthManager, 'get_credentials', return_value=fake_creds):
            with patch("services.email.sender.build") as build_mock:
                service = build_mock.return_value
                service.users.return_value.messages.return_value.send.return_value.execute.side_effect = Exception(
                    "403 insufficient permissions"
                )
                sender = GmailSenderService(auth_manager=manager)
                res = sender.send_pitch("reporter@example.com", "Subject", "Body text")

        assert res["success"] is False
        assert res["simulated"] is False
        assert "insufficient permissions" in res["error"]

    def test_send_pitch_success_via_mocked_gmail_api(self, gmail_configured_settings, clean_gmail_token_store):
        manager = _make_manager(client=None)
        # Save tokens with a future expiry to ensure credentials are valid
        future_expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        manager.save_tokens("user-1", {
            "user_id": "user-1",
            "access_token": "qa-access-token",
            "refresh_token": "qa-refresh-token",
            "token_expiry": future_expiry,
        })
        sender = GmailSenderService(auth_manager=manager)

        with patch("services.email.sender.build") as build_mock:
            send_exec = build_mock.return_value.users.return_value.messages.return_value.send.return_value.execute
            send_exec.return_value = {"id": "msg-123", "threadId": "thread-456"}
            # Pass user_id="user-1" to match the saved tokens
            res = sender.send_pitch(
                "reporter@example.com", "Subject", "Body text", user_id="user-1", thread_id="thread-456"
            )

        assert res["success"] is True
        assert res["simulated"] is False
        assert res["gmail_message_id"] == "msg-123"
        assert res["gmail_thread_id"] == "thread-456"
        sent_call = build_mock.return_value.users.return_value.messages.return_value.send.call_args
        if sent_call:
            assert "body" in sent_call.kwargs
            body = sent_call.kwargs["body"]
            if isinstance(body, dict) and "threadId" in body:
                assert body["threadId"] == "thread-456"

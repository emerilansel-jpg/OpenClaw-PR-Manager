"""Shared fixtures and settings helpers for the OpenClaw PR Manager test suite.

No real network access or external credentials are required by any test in
this suite: Google OAuth flows, Gmail API calls, Supabase, and news APIs are
always replaced with mocks/fakes, and repositories fall back to their
in-memory local stores.
"""
from unittest.mock import MagicMock

import pytest

from config.settings import get_settings


@pytest.fixture()
def override_settings(monkeypatch):
    """Return a helper that monkeypatches attributes on the cached Settings.

    `get_settings()` is an `lru_cache`d singleton, so every component that
    calls it shares one instance. Patching attributes on that instance is the
    supported way to simulate configuration (e.g. Gmail client credentials)
    without a real `.env` file.
    """
    settings = get_settings()

    def _apply(**kwargs):
        for key, value in kwargs.items():
            monkeypatch.setattr(settings, key, value)
        return settings

    return _apply


@pytest.fixture()
def gmail_configured_settings(override_settings):
    """Settings patched to look like Gmail OAuth is fully configured.

    Uses obviously fake, non-routable placeholder credentials -- the test
    suite must never hit real Google endpoints.
    """
    return override_settings(
        GOOGLE_CLIENT_ID="qa-test-client-id.apps.googleusercontent.com",
        GOOGLE_CLIENT_SECRET="qa-test-client-secret",
        GOOGLE_REDIRECT_URI="http://localhost:8000/api/v1/auth/google/callback",
    )


@pytest.fixture()
def gmail_unconfigured_settings(override_settings):
    """Settings patched so Gmail OAuth is explicitly NOT configured."""
    return override_settings(GOOGLE_CLIENT_ID=None, GOOGLE_CLIENT_SECRET=None)


@pytest.fixture()
def clean_gmail_token_store():
    """Reset the class-level local token store before and after each test."""
    from services.email.gmail_auth import GmailOAuthManager

    GmailOAuthManager._local_tokens.clear()
    yield GmailOAuthManager._local_tokens
    GmailOAuthManager._local_tokens.clear()


@pytest.fixture()
def mock_supabase_client():
    """A MagicMock stand-in for a connected Supabase client.

    Chain methods (`table(...).upsert(...).execute()` etc.) return further
    MagicMocks, so repository/service code runs against it without network.
    """
    return MagicMock(name="SupabaseClient")

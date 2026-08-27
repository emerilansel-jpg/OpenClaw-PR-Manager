"""Google OAuth2 authentication and connected-sender management."""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import AuthorizedSession, Request
from config.settings import get_settings
from db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailOAuthManager:
    """Manages Gmail OAuth2 tokens and client credentials."""

    _local_tokens: Dict[str, Dict[str, Any]] = {}

    def __init__(self):
        self.settings = get_settings()
        self.client = get_supabase_client()

    def _client_config(self) -> Dict[str, Any]:
        return {
            "web": {
                "client_id": self.settings.GOOGLE_CLIENT_ID,
                "client_secret": self.settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.GOOGLE_REDIRECT_URI],
            }
        }

    def get_authorization_request(
        self,
        state: Optional[str] = None,
    ) -> Optional[Tuple[str, str]]:
        """Generate an OAuth URL and the PKCE verifier required by its callback."""
        if not self.settings.is_gmail_configured:
            logger.warning("Gmail OAuth client ID / Secret not configured in .env")
            return None

        flow = Flow.from_client_config(
            self._client_config(),
            scopes=SCOPES,
            redirect_uri=self.settings.GOOGLE_REDIRECT_URI,
            state=state,
        )

        auth_url, _generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        if not flow.code_verifier:
            logger.error("Google OAuth flow did not generate a PKCE code verifier")
            return None
        return auth_url, flow.code_verifier

    def get_authorization_url(self, state: Optional[str] = None) -> Optional[str]:
        """Generate an OAuth URL for backwards-compatible API consumers."""
        request = self.get_authorization_request(state=state)
        return request[0] if request else None

    def get_streamlit_authorization_url(
        self,
        redirect_uri: str,
        state: Optional[str] = None,
    ) -> Optional[str]:
        """Generate an OAuth URL for a Streamlit-native flow (no PKCE persistence).

        The web client type carries a client_secret, so the authorization-code
        exchange is authenticated by that secret and PKCE is optional. This lets
        Streamlit handle the whole flow without a separate FastAPI backend: the
        user returns to ``redirect_uri`` with ``?code=...`` which the dashboard
        exchanges directly.
        """
        if not self.settings.is_gmail_configured:
            logger.warning("Gmail OAuth client ID / Secret not configured")
            return None

        config = self._client_config()
        config["web"]["redirect_uris"] = [redirect_uri]

        flow = Flow.from_client_config(
            config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=state,
            autogenerate_code_verifier=False,
        )
        auth_url, _generated_state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code_streamlit(
        self,
        code: str,
        redirect_uri: str,
    ) -> Optional[Dict[str, Any]]:
        """Exchange an authorization code inside a Streamlit-native flow.

        Uses the registered ``redirect_uri`` (the Streamlit app URL) and the
        client_secret for the token exchange; no PKCE verifier is required.
        """
        if not self.settings.is_gmail_configured:
            return None

        try:
            config = self._client_config()
            config["web"]["redirect_uris"] = [redirect_uri]
            flow = Flow.from_client_config(
                config,
                scopes=SCOPES,
                redirect_uri=redirect_uri,
                autogenerate_code_verifier=False,
            )
            flow.fetch_token(code=code)
            credentials = flow.credentials

            email_address = self._fetch_authorized_email(credentials)
            if not email_address:
                logger.error("OAuth succeeded but authorized Google email could not be verified")
                return None
            account_key = email_address.strip().lower()

            token_data = {
                "user_id": account_key,
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "scopes": credentials.scopes,
                "email_address": account_key,
            }
            self.save_tokens(account_key, token_data)
            return token_data
        except Exception as e:
            logger.error("Streamlit OAuth token exchange failed: %s", e)
            return None

    @staticmethod
    def _fetch_authorized_email(credentials: Credentials) -> Optional[str]:
        """Read the verified Google identity attached to the granted token."""
        try:
            response = AuthorizedSession(credentials).get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                timeout=10,
            )
            response.raise_for_status()
            profile = response.json()
            email_address = str(profile.get("email") or "").strip().lower()
            if not email_address or profile.get("email_verified") is False:
                return None
            return email_address
        except Exception as exc:
            logger.error("Could not read the connected Google account identity: %s", exc)
            return None

    def exchange_code_for_tokens(
        self,
        code: str,
        user_id: Optional[str] = None,
        state: Optional[str] = None,
        code_verifier: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Exchange a code and store tokens under the authorized Gmail address.

        ``user_id`` is retained only for backwards-compatible unit tests and
        server migrations. Normal OAuth callbacks must derive the account key
        from Google's verified identity response.
        """
        if not self.settings.is_gmail_configured:
            return None

        try:
            flow = Flow.from_client_config(
                self._client_config(),
                scopes=SCOPES,
                redirect_uri=self.settings.GOOGLE_REDIRECT_URI,
                state=state,
                code_verifier=code_verifier,
                autogenerate_code_verifier=False,
            )
            flow.fetch_token(code=code)
            credentials = flow.credentials

            email_address = user_id or self._fetch_authorized_email(credentials)
            if not email_address:
                logger.error("OAuth succeeded but the authorized Google email could not be verified")
                return None
            account_key = email_address.strip().lower()

            token_data = {
                "user_id": account_key,
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                "scopes": credentials.scopes,
                "email_address": account_key,
            }

            self.save_tokens(account_key, token_data)
            return token_data
        except Exception as e:
            logger.error("OAuth token exchange failed: %s", e)
            return None

    def save_tokens(self, user_id: str, token_data: Dict[str, Any]) -> None:
        """Save tokens to Supabase or local storage."""
        existing = None if token_data.get("refresh_token") else self._load_token_data(user_id)
        refresh_token = token_data.get("refresh_token") or (existing or {}).get("refresh_token")
        normalized = {
            **token_data,
            "refresh_token": refresh_token,
            "email_address": token_data.get("email_address") or user_id,
            "scopes": token_data.get("scopes") or (existing or {}).get("scopes") or SCOPES,
        }
        if self.client:
            try:
                self.client.table("gmail_tokens").upsert({
                    "account_key": user_id,
                    "access_token": normalized["access_token"],
                    "refresh_token": normalized.get("refresh_token"),
                    "token_expiry": normalized.get("token_expiry"),
                    "email_address": normalized["email_address"],
                    "scopes": normalized["scopes"],
                }, on_conflict="account_key").execute()
                return
            except Exception as e:
                logger.error("Failed to save tokens to Supabase: %s", e)

        self._local_tokens[user_id] = normalized

    def _load_token_data(self, account_key: str) -> Optional[Dict[str, Any]]:
        if self.client:
            try:
                res = self.client.table("gmail_tokens").select("*").eq("account_key", account_key).execute()
                if res.data:
                    return res.data[0]
            except Exception as exc:
                logger.warning("Could not load Gmail token for %s: %s", account_key, exc)
        return self._local_tokens.get(account_key)

    def list_connected_accounts(self) -> List[Dict[str, Any]]:
        """Return sender-safe account metadata without exposing OAuth tokens."""
        rows: List[Dict[str, Any]] = []
        if self.client:
            try:
                res = (
                    self.client.table("gmail_tokens")
                    .select("account_key,email_address,token_expiry,created_at,updated_at")
                    .order("email_address")
                    .execute()
                )
                rows = res.data or []
            except Exception as exc:
                logger.warning("Could not list connected Gmail accounts: %s", exc)
        else:
            rows = [
                {
                    "account_key": key,
                    "email_address": value.get("email_address") or key,
                    "token_expiry": value.get("token_expiry"),
                }
                for key, value in self._local_tokens.items()
            ]

        return sorted(
            [
                {
                    "account_key": row.get("account_key"),
                    "email_address": row.get("email_address") or row.get("account_key"),
                    "token_expiry": row.get("token_expiry"),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
                for row in rows
                if row.get("account_key") and row.get("account_key") != "default_user"
            ],
            key=lambda row: str(row.get("email_address") or "").lower(),
        )

    def has_connected_account(self, account_key: str) -> bool:
        return bool(account_key and self._load_token_data(account_key))

    def disconnect_account(self, account_key: str) -> bool:
        """Disconnects a connected sender Gmail account and removes its tokens."""
        if not account_key:
            return False

        success = False
        if self.client:
            try:
                self.client.table("gmail_tokens").delete().eq("account_key", account_key).execute()
                success = True
            except Exception as e:
                logger.error("Failed to delete Gmail token from Supabase: %s", e)

        if account_key in self._local_tokens:
            del self._local_tokens[account_key]
            success = True

        return success

    def get_credentials(self, user_id: str = "default_user") -> Optional[Credentials]:
        """Fetch and automatically refresh Google OAuth2 credentials."""
        token_data = self._load_token_data(user_id)
        if not token_data:
            return None

        expiry = token_data.get("token_expiry")
        if isinstance(expiry, str):
            try:
                expiry = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if expiry.tzinfo is not None:
                    expiry = expiry.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                expiry = None

        creds = Credentials(
            token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=self.settings.GOOGLE_CLIENT_ID,
            client_secret=self.settings.GOOGLE_CLIENT_SECRET,
            scopes=token_data.get("scopes") or SCOPES,
            expiry=expiry,
        )

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.save_tokens(user_id, {
                    "user_id": user_id,
                    "access_token": creds.token,
                    "refresh_token": creds.refresh_token,
                    "token_expiry": creds.expiry.isoformat() if creds.expiry else None,
                    "email_address": token_data.get("email_address") or user_id,
                    "scopes": token_data.get("scopes") or SCOPES,
                })
            except Exception as e:
                logger.error("Failed to refresh Google token: %s", e)
                return None

        return creds

"""Authentication API Router for connecting Gmail sender accounts."""
import html
import secrets

from fastapi import APIRouter, Query, HTTPException, Request, Response, responses
from services.email.gmail_auth import GmailOAuthManager
from config.settings import get_settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_mgr = GmailOAuthManager()
settings = get_settings()
OAUTH_STATE_COOKIE = "openclaw_gmail_oauth_state"
OAUTH_PKCE_COOKIE = "openclaw_gmail_oauth_pkce"


def _new_oauth_state() -> str:
    return secrets.token_urlsafe(32)


def _set_oauth_cookies(response: Response, state: str, code_verifier: str) -> None:
    cookie_options = {
        "max_age": 600,
        "httponly": True,
        "secure": settings.GOOGLE_REDIRECT_URI.startswith("https://"),
        "samesite": "lax",
    }
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        **cookie_options,
    )
    response.set_cookie(
        OAUTH_PKCE_COOKIE,
        code_verifier,
        **cookie_options,
    )


@router.get("/google/login")
def google_login(response: Response):
    """Returns Google OAuth login URL."""
    state = _new_oauth_state()
    auth_request = auth_mgr.get_authorization_request(state=state)
    if not auth_request:
        raise HTTPException(
            status_code=400,
            detail="Google Client ID and Secret not configured in .env",
        )
    url, code_verifier = auth_request
    _set_oauth_cookies(response, state, code_verifier)
    return {"authorization_url": url}


@router.get("/google/connect")
def google_connect(request: Request, return_to: Optional[str] = Query(None)):
    """Start a browser OAuth flow for a new Gmail sender account."""
    state = _new_oauth_state()
    auth_request = auth_mgr.get_authorization_request(state=state)
    if not auth_request:
        raise HTTPException(
            status_code=400,
            detail="Google Client ID and Secret not configured in .env",
        )
    url, code_verifier = auth_request
    response = responses.RedirectResponse(url=url, status_code=302)
    _set_oauth_cookies(response, state, code_verifier)
    
    # Store return_to destination in cookie
    dest = return_to or request.headers.get("referer") or settings.DASHBOARD_BASE_URL
    response.set_cookie("openclaw_oauth_return_to", dest, max_age=600, httponly=True, samesite="lax")
    return response


@router.get("/google/callback")
def google_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
):
    """Handles OAuth2 redirect and stores tokens."""
    cookie_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not cookie_state or not secrets.compare_digest(cookie_state, state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    code_verifier = request.cookies.get(OAUTH_PKCE_COOKIE)
    if not code_verifier:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth PKCE verifier")

    tokens = auth_mgr.exchange_code_for_tokens(
        code,
        state=state,
        code_verifier=code_verifier,
    )
    if not tokens:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code")

    sender_email = html.escape(str(tokens.get("email_address") or "Gmail account"))
    return_dest = request.cookies.get("openclaw_oauth_return_to") or settings.DASHBOARD_BASE_URL
    clean_dest = return_dest.split("?")[0].rstrip("/")
    dashboard_url = html.escape(f"{clean_dest}/?auth_success=1&sender={sender_email}", quote=True)
    
    response = responses.HTMLResponse(
        content=(
            "<!doctype html><html><head><meta charset='utf-8'>"
            f"<meta http-equiv='refresh' content='2;url={dashboard_url}'>"
            "<title>Gmail connected</title>"
            "<style>body{font-family:system-ui;background:#0a0c0f;color:#f2f0e9;max-width:620px;"
            "margin:12vh auto;padding:32px;text-align:center}a{color:#8fd6ad;font-weight:600;font-size:1.1rem;text-decoration:none;display:inline-block;margin-top:16px;background:#181c21;padding:10px 20px;border-radius:8px;border:1px solid #2a3037}</style></head><body>"
            "<h2>🦅 Gmail Sender Connected!</h2>"
            f"<p><strong style='color:#8fd6ad;font-size:1.15rem;'>{sender_email}</strong> is now authorized and connected as your email sender.</p>"
            "<p style='color:#9ba3ad;font-size:0.9rem;'>Redirecting back to OpenClaw Dashboard in 2 seconds...</p>"
            f"<p><a href='{dashboard_url}'>➡️ Click here if not redirected automatically</a></p></body></html>"
        )
    )
    response.delete_cookie(OAUTH_STATE_COOKIE)
    response.delete_cookie(OAUTH_PKCE_COOKIE)
    response.delete_cookie("openclaw_oauth_return_to")
    return response


@router.get("/google/accounts")
def google_accounts():
    """List connected sender identities without returning any token data."""
    return {"accounts": auth_mgr.list_connected_accounts()}


@router.delete("/google/accounts/{account_key}")
def disconnect_google_account(account_key: str):
    """Disconnect and revoke stored tokens for a specific sender account."""
    if not auth_mgr.has_connected_account(account_key):
        raise HTTPException(status_code=404, detail="Sender account not found")

    success = auth_mgr.disconnect_account(account_key)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to disconnect account")

    return {"success": True, "disconnected": account_key}

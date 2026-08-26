# Integration Setup Guide

This document provides step-by-step instructions to configure each integration. **All credentials must be supplied by you** and stored in `.env`. None of these integrations are pre-connected or verified.

---

## 1. Supabase (PostgreSQL + pgvector + Auth)

### Steps

1. Create a project at [supabase.com](https://supabase.com/dashboard).
2. Navigate to **Settings → API**.
3. Record:
   - `Project URL` → `SUPABASE_URL` (looks like `https://<project-ref>.supabase.co`).
   - `anon public key` → `SUPABASE_KEY`.
   - `service_role` key (hidden click if needed) → `SUPABASE_SERVICE_ROLE_KEY`.
4. Apply the database migrations to your SQL Editor **in order**:
   - `db/migrations/001_initial_schema.sql`
   - `db/migrations/002_rls_policies.sql`
   - `db/migrations/003_functions.sql`
   - `db/migrations/004_gmail_account_key.sql`
   - `db/migrations/005_auth_system.sql`
   - `db/migrations/006_verified_contacts_multi_sender.sql`

### Notes

- The initial RLS policies are permissive (`USING (true)`). Replace them before production use.
- `pgvector` extension is enabled by migration 001.

---

## 2. OpenAI (Embeddings & GPT-4o)

### Steps

1. Visit [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Create an API key.
3. Set `OPENAI_API_KEY=sk-your-key` in `.env`.
4. Ensure models match:
   - `OPENAI_MODEL=gpt-4o`
   - `OPENAI_EMBEDDING_MODEL=text-embedding-3-small`

### Verification

Check presence via boolean flag:
```bash
python -c "from config.settings import get_settings; s=get_settings(); print('openai_configured:', s.is_openai_configured)"
```

---

## 3. DeepSeek (Cost-Efficient Bulk Pitches)

### Steps

1. Visit [deepseek.com](https://platform.deepseek.com/api_keys).
2. Create an API key.
3. Set `DEEPSEEK_API_KEY=sk-your-key` in `.env`.
4. Base URL and model are already correct:
   - `DEEPSEEK_BASE_URL=https://api.deepseek.com/v1`
   - `DEEPSEEK_MODEL=deepseek-chat`

### Verification

```bash
python -c "from config.settings import get_settings; s=get_settings(); print('deepseek_configured:', s.is_deepseek_configured)"
```

---

## 4. Gmail OAuth2 (Google Cloud Console)

### Prerequisites

- You must own a Google Cloud project.
- Enable the **Gmail API**.
- Configure the **OAuth consent screen**.

### Steps

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. **Enable Gmail API**:
   - APIs & Services → Library → Search "Gmail API" → Enable.
3. **OAuth Consent Screen**:
   - APIs & Services → OAuth consent screen → Configure.
   - Choose appropriate user type and required scopes.
   - Add test users if in testing mode.
4. **Create Credentials**:
   - APIs & Services → Credentials → Create credentials → OAuth client ID.
   - Application type: **Web application**.
5. **Authorized redirect URIs** — add exactly this URI:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
   This path matches the FastAPI route `/api/v1/auth/google/callback` implemented in `api/routers/auth.py`.
6. Copy **Client ID** and **Client Secret** into `.env`:
   - `GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com`
   - `GOOGLE_CLIENT_SECRET=your-client-secret`
7. Set `GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback` (default is correct for local dev).

### Ownership model

- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` belong to the Google Cloud project owned by the OpenClaw operator.
- They do not need to belong to the mailbox used to send a pitch.
- Every Gmail or Google Workspace sender must click **Connect another Gmail sender** and grant consent once.
- The initial pitch and all follow-ups are pinned to that connected account.
- While the consent screen is in Testing, add every sender as a Google OAuth test user. Publish/verify the app before allowing broader external accounts.
- Because `gmail.send` is not an identity-only scope, Google test-user authorizations and refresh tokens expire after 7 days. Use Testing only for setup/QA, then move the production OAuth project through the appropriate publishing/verification process.

### Scope

The application requests `openid`, `email`, and `https://www.googleapis.com/auth/gmail.send`. The identity scopes are used only to identify the connected account; Gmail delivery uses `gmail.send`.

### Verification

```bash
python -c "from config.settings import get_settings; s=get_settings(); print('gmail_configured:', s.is_gmail_configured)"
```

> A `True` result means `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are present and pass basic format checks. It does not verify OAuth connectivity or that tokens can be exchanged.

---

## 5. News Scraping APIs (Optional)

Google News RSS discovery works without keys. The following services provide additional sources.

### NewsAPI.org

1. Register at [newsapi.org/register](https://newsapi.org/register).
2. Copy your **API Key**.
3. Set `NEWS_API_ORG_KEY=<key>` in `.env`.

### TheNewsAPI.com

1. Register at [the newsapi.com](https://www.thenewsapi.com/).
2. Copy your **API Token**.
3. Set `THE_NEWS_API_KEY=<token>` in `.env`.

Both services are optional; the scraper will still function using free Google News RSS when these keys are omitted.

---

## 6. CORS Configuration

CORS is handled by FastAPI's `CORSMiddleware` configured in `api/main.py`.

### Local Development

The default values work for Streamlit running locally:
```ini
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```

### Production

Replace with your actual dashboard domain(s), comma-separated:
```ini
CORS_ORIGINS=https://dashboard.yourdomain.com,https://app.yourdomain.com
```

Ensure the URLs include the scheme (`https://`). Do **not** include a trailing slash.

---

## 7. Tracking Pixel (Open Rates)

The application sends emails with a hidden 1x1 tracking pixel. When the email loads the image, the backend records an open event.

### Route Implemented

The tracking endpoint served by the backend is:
```
{TRACKING_BASE_URL}/open/{tracking_token}
```

### Local Development

Default:
```ini
TRACKING_BASE_URL=http://localhost:8000/api/v1/outreach/track
```

### Production

You must use HTTPS and ensure the host is publicly reachable from email clients:
```ini
TRACKING_BASE_URL=https://api.yourdomain.com/api/v1/outreach/track
```

If your deployment cannot expose an HTTPS endpoint, opens and replies must be tracked manually or via webhooks from another provider.

---

## 8. Follow-up Scheduler (State Machine)

The application implements a manual state machine (no cron worker yet):

- **Day 0:** Initial pitch
- **Day 3:** Follow-up #1
- **Day 10:** Follow-up #2
- **Day 17:** Follow-up #3
- **Day 31:** Breakup

To process due follow-ups, call:
```bash
curl http://localhost:8000/api/v1/outreach/process-follow-ups -X POST
```

There is no persistent background job. For production, deploy a cron/job service to run this periodically.

---

## Quick Reference Checklist

- [ ] `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY` set and migrations applied.
- [ ] `OPENAI_API_KEY` set and `is_openai_configured` returns `True`.
- [ ] `DEEPSEEK_API_KEY` set and `is_deepseek_configured` returns `True` (optional but recommended).
- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` set, redirect URI added to Google Cloud, and `is_gmail_configured` returns `True`.
- [ ] `CORS_ORIGINS` restricts allowed origins appropriately.
- [ ] `TRACKING_BASE_URL` points to an HTTPS endpoint in production.
- [ ] Migrations `001`–`006` applied to Supabase.
- [ ] Security review completed (RLS hardening, tenant enforcement, cron worker planned).

---

## Diagnostic Commands (Boolean Checks Only)

These commands reveal configuration booleans without exposing secrets:

```bash
python -c "from config.settings import get_settings; s=get_settings(); print('supabase_configured:', s.is_supabase_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('openai_configured:', s.is_openai_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('deepseek_configured:', s.is_deepseek_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('gmail_configured:', s.is_gmail_configured)"
```

Verify routes exist:
```bash
curl -s http://localhost:8000/openapi.json | python -c "import sys, json; p=json.load(sys.stdin)['paths']; print('/google/callback' in str(p)); print('/track/open/{token}' in str(p))"
```

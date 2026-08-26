# 🦅 OpenClaw PR Manager

An autonomous, multi-model AI Public Relations & Media Relations management system built on **FastAPI**, **Supabase (PostgreSQL + pgvector + Auth)**, **OpenAI GPT-4o / DeepSeek**, **Gmail API (OAuth2)**, and an interactive **Streamlit Dashboard**.

---

## 🌟 Key Features

1. **OpenClaw 4D Scoring & pgvector Matching**:
   - Scores media contacts across 4 dimensions: *Category Match (40%)*, *Influence Tier (25%)*, *Response History (20%)*, and *Relationship Closeness (15%)*.
   - Uses `pgvector` (`VECTOR(1536)`) for semantic search between press releases and journalist coverage.
2. **Evidence-First Journalist Discovery**:
   - Free Google News RSS scraper (no API key required).
   - Optional connectors for NewsAPI.org and TheNewsAPI.com.
   - Coverage candidates are never assigned guessed email addresses.
   - Public/provider evidence and verification status are stored with each contact.
3. **Multi-Model AI Pitch Studio**:
   - **OpenAI GPT-4o**: Premium personalized angles and embeddings.
   - **DeepSeek**: Cost-effective bulk pitch generation.
   - Jinja2 templates with variables (`{{journalist_name}}`, `{{outlet}}`, `{{beat}}`, `{{story}}`).
4. **Gmail API OAuth2 & 3+7+7+14 Follow-up Automation**:
   - Native Gmail API integration with OAuth2 token refresh.
   - 1x1 transparent tracking pixel for open rates.
   - Follow-up sequence: Day 0 → Day 3 → Day 10 → Day 17 → Day 31.
5. **Interactive Web Dashboard (Streamlit)**:
   - Analytics funnel, journalist explorer, campaign generator, AI pitch studio, and outreach kanban.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your own credentials:
```bash
cp .env.example .env
```

> **🔒 Security Warning**
> - `.env` contains secrets and is already listed in `.gitignore`.
> - **Never commit `.env` or any file with real API keys, tokens, or passwords.**
> - All values in `.env.example` are placeholders. You must supply valid credentials.
> - Setting a value in `.env` does **not** mean the integration is connected or verified.

#### Required for Production Use

| Service | Environment Variables | Used For |
|---|---|---|
| Supabase | `SUPABASE_URL`, `SUPABASE_KEY` | PostgreSQL, pgvector, persistent data |
| Supabase (admin) | `SUPABASE_SERVICE_ROLE_KEY` | Backend-only administrative operations; never expose in browsers |
| OpenAI | `OPENAI_API_KEY` | GPT-4o pitch generation and `text-embedding-3-small` embeddings |
| Google Cloud OAuth | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` | OAuth app owned by you; connecting one or more Gmail sender accounts |
| Public Backend URL | `TRACKING_BASE_URL` | Open-tracking pixel; must be HTTPS and publicly reachable |

#### Optional

| Service | Environment Variables | Used For |
|---|---|---|
| DeepSeek | `DEEPSEEK_API_KEY` | Lower-cost bulk pitch generation |
| NewsAPI.org | `NEWS_API_ORG_KEY` | Additional article discovery source |
| TheNewsAPI.com | `THE_NEWS_API_KEY` | Additional article discovery source |

> **Note:** Google News RSS discovery works without any key.

#### Gmail OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Gmail API**.
3. Configure the **OAuth consent screen**.
4. Create **OAuth 2.0 Client Credentials** (type: *Web application*).
5. Add this exact redirect URI to **Authorized redirect URIs**:
   ```
   http://localhost:8000/api/v1/auth/google/callback
   ```
   The URI must match the `GOOGLE_REDIRECT_URI` value and the actual FastAPI route exactly.
6. The app requests `openid`, `email`, and `https://www.googleapis.com/auth/gmail.send`. Identity scopes label the connected sender; `gmail.send` is used for delivery.
7. Start the API and dashboard, then open **Settings → Connect another Gmail sender**. Repeat this once for every Gmail/Workspace account that may send outreach.

#### CORS Configuration
`CORS_ORIGINS` is a comma-separated allow-list used by the FastAPI CORS middleware. For local development, the default covers the Streamlit dashboard:
```
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
```
In production, replace this with your actual dashboard domain(s) over HTTPS.

#### Tracking Pixel URL
The tracking pixel is served from:
```
{TRACKING_BASE_URL}/open/{tracking_token}
```
For production, `TRACKING_BASE_URL` must be a publicly reachable HTTPS endpoint, e.g.:
```
TRACKING_BASE_URL=https://api.yourdomain.com/api/v1/outreach/track
```

### 3. Setup Supabase Database Migrations
Open your [Supabase SQL Editor](https://supabase.com/dashboard) and run the scripts **in order**:

1. `db/migrations/001_initial_schema.sql` — Creates tables, indexes, and enables `pgvector` and `uuid-ossp` extensions.
2. `db/migrations/002_rls_policies.sql` — Enables Row Level Security (RLS) and creates policies.
3. `db/migrations/003_functions.sql` — Creates `updated_at` triggers and the `match_journalists` semantic-search function.
4. `db/migrations/004_gmail_account_key.sql` — Adds the `account_key` column to `gmail_tokens` so OAuth tokens can be shared between the FastAPI and Streamlit processes.
5. `db/migrations/005_auth_system.sql` — Adds authentication and tenant-related tables/policies.
6. `db/migrations/006_verified_contacts_multi_sender.sql` — Adds contact evidence fields and pins each outreach thread to its Gmail sender.

> **⚠️ Important:** The RLS policies in migration 002 are **development-oriented and permissive** (e.g., `USING (true)` for campaigns/outreach, and `auth.role() = 'anon'` allowed for some writes). They are **not safe for production** with real user data.

### 4. Run the Backend API (FastAPI)
```bash
uvicorn api.main:app --reload --port 8000
```
- Swagger UI: `http://localhost:8000/docs`
- Redoc: `http://localhost:8000/redoc`

### 5. Run the Web Dashboard (Streamlit)
```bash
streamlit run dashboard/app.py
```
- Dashboard URL: `http://localhost:8501`

---

## ✅ Verifying Configuration Status (Boolean Checks Only)

You can safely check whether the application **detects** credentials without printing secrets. These commands output only `True` or `False`.

> **Safety:** These commands do not read or print the contents of `.env`; they evaluate the same boolean properties the application uses at startup.

```bash
python -c "from config.settings import get_settings; s=get_settings(); print('supabase_configured:', s.is_supabase_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('openai_configured:', s.is_openai_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('deepseek_configured:', s.is_deepseek_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('gmail_configured:', s.is_gmail_configured)"
```

You can also check the live API routes are registered:
```bash
curl -s http://localhost:8000/openapi.json | python -c "import sys, json; paths=json.load(sys.stdin)['paths']; print('/api/v1/auth/google/callback' in paths, '/api/v1/outreach/track/open/{token}' in paths)"
```

> **Note:** A `True` result means the configuration value is present and passes basic format checks. It does **not** guarantee the external service is reachable or that OAuth tokens are valid.

---

## 🚨 Current Production Blockers

Before deploying to production or storing real data, be aware of these unresolved issues:

1. **No application-level authentication or tenant enforcement**
   - The FastAPI routers do not require user login.
   - There is no middleware enforcing `organization_id` isolation per request.
   - Any client that can reach the API can read or modify data.

2. **Permissive Row Level Security (RLS) policies**
   - Migration `002_rls_policies.sql` allows public read on journalists, full access to campaigns/outreach, and write access for `anon` roles.
   - These policies must be replaced with tenant-aware policies using `auth.uid()` and `organization_id`.

3. **Scheduler is process-local**
   - APScheduler runs due follow-ups while the FastAPI process is alive.
   - Production still needs a durable singleton worker/lock so restarts and multiple API replicas cannot miss or duplicate work.

4. **Gmail sender tokens are not yet workspace-scoped**
   - Each connected Google email now has its own `account_key`, and outreach is pinned to it.
   - Ownership and authorization are still not enforced per authenticated user/organization, so token management is not yet multi-tenant safe.

---

## 🧪 Running Tests

Execute the automated test suite:
```bash
pytest
```

---

## 📁 Project Structure

```
.
├── config/                  # Pydantic Settings & Environment loader
├── db/                      # Supabase client, migrations, & repositories
│   ├── migrations/          # SQL DDL, RLS, pgvector Stored Procedures
│   └── repositories/        # Journalists, Campaigns, Outreach, Templates
├── core/                    # OpenClaw 4D Scoring & Matching Algorithm
├── services/
│   ├── scraping/            # Google News RSS Scraper & Email Validator
│   ├── ai/                  # OpenAI (GPT-4o), DeepSeek, & PromptBuilder
│   ├── email/               # Gmail API OAuth2, MIME Sender, & Open Tracker
│   └── scheduler/           # 3+7+7+14 Days Follow-up Automation
├── api/                     # FastAPI Routers & REST Endpoints
├── dashboard/               # Streamlit Interactive Web Application
├── scripts/                 # Migration helper and Seed Data
└── tests/                   # Pytest test suite
```

---

## 📚 Additional Documentation

Detailed integration and security guides are available in the `docs/` directory:

- `docs/integrations.md` — Step-by-step setup for Supabase, Gmail OAuth, OpenAI, DeepSeek, News APIs, CORS, and tracking.
- `docs/security.md` — Credential handling, production blockers, RLS hardening guidance, and safe verification commands.

# Security & Configuration Notes

This document outlines credential handling, current production blockers, and safe verification commands. **No integrations are pre-connected.** All secrets must be supplied by the user and stored in `.env`.

---

## Credential Handling

### Where Secrets Live

- **Local development:** `.env` (must not exist in repositories; included in `.gitignore`).
- **Backend services:** Environment variables provided at process start time.
- **Database:** Credentials do **not** go into Supabase tables. OAuth tokens may be persisted per `account_key`, but API keys remain in environment configuration only.

### What Must Never Be Committed

- **`.env`** — Contains `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, OpenAI/DeepSeek keys, Google OAuth client secret, etc.
- **Any log files** that may contain partial secrets or tokens.
- **Screenshots** of dashboards that expose sensitive data.

### Supplying Your Own Values

1. Copy `.env.example` to `.env`.
2. Replace all placeholder values with your own.
3. Verify the file is excluded from version control:
   ```bash
   git check-file .env  # Should report "is ignored" if properly configured
   ```

> Setting a value does not guarantee external connectivity. Some providers require additional console configuration (e.g., redirect URIs for OAuth).

---

## Current Production Blockers

Before deploying to production or storing real contacts/Gmail tokens, address these issues:

### 1. No Application-Level Authentication or Tenant Enforcement

- The FastAPI routers (`api/routers/*.py`) do **not** require user login.
- There is no middleware enforcing `organization_id` isolation per request.
- Any client that can reach the API can read or modify data.

**Recommendation:** Add JWT-based authentication using Supabase Auth, enforce tenant claims, and isolate data by `organization_id` on every repository call.

### 2. Permissive Row Level Security (RLS) Policies

Migration `002_rls_policies.sql` includes policies like:
- Journalists: `USING (true)` (public read); writes allowed for `anon` role.
- Campaigns/Outreach: Fully open (`USING (true)`, `WITH CHECK (true)`).
- Gmail Tokens: Scoped to `auth.uid() = user_id`, but the code uses a shared `account_key` pattern.

These are appropriate for local testing, not production.

**Recommendation:** Replace permissive policies with tenant-aware policies, e.g.:
```sql
CREATE POLICY "tenant_isolation" ON outreach FOR ALL
USING (organization_id = current_setting('app.current_organization_id')::UUID)
WITH CHECK (...);
```

Use `auth.uid()` and proper organization scoping. Disable `anon` write access entirely.

### 3. Process-Local Background Worker for Follow-ups

APScheduler runs follow-ups while the FastAPI process is alive. The manual endpoint remains available for controlled operations.

This is not durable across downtime and needs a singleton/lock when multiple API replicas are deployed.

**Recommendation:** Move due-work claiming to a durable worker or database-backed scheduler with idempotent locks.

### 4. Gmail Sender Ownership

New connections are stored under the verified Google email address and multiple senders no longer overwrite one another. However, ownership is not yet enforced per authenticated organization.

**Recommendation:** Add organization ownership, authenticated connect/list/revoke endpoints, encrypted token storage, and an audit log before multi-tenant production use.

---

## Safe Verification Commands (Boolean Only)

The following commands output only `True` or `False` and never reveal secrets. They evaluate the same properties used at application startup.

### Service Configuration Checks

```bash
python -c "from config.settings import get_settings; s=get_settings(); print('supabase_configured:', s.is_supabase_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('openai_configured:', s.is_openai_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('deepseek_configured:', s.is_deepseek_configured)"
python -c "from config.settings import get_settings; s=get_settings(); print('gmail_configured:', s.is_gmail_configured)"
```

Interpretation:
- `True`: A non-empty value exists and passes basic format checks (e.g., starts with expected prefix). It does **not** verify connectivity or token validity.
- `False`: No value, too short, or fails basic format validation.

### Route Presence Check

Verify endpoints are registered without loading `.env` secrets:

```bash
curl -s http://localhost:8000/openapi.json | python -c "import sys,json; p=json.load(sys.stdin)['paths']; print('/api/v1/auth/google/callback' in str(p)); print('/api/v1/outreach/track/open/{token}' in str(p))"
```

Expected: two boolean results printed. If `False`, the router was not loaded correctly.

---

## Migration Summary

Apply migrations **in order**:

| File | Purpose |
|---|---|
| `001_initial_schema.sql` | Creates organizations, journalists, campaigns, outreach, gmail_tokens, prompt_templates, indexes, and enables `pgvector` + `uuid-ossp`. |
| `002_rls_policies.sql` | Enables RLS and creates **development-only**, permissive policies. Not safe for production with real data. |
| `003_functions.sql` | Adds `updated_at` triggers and the `match_journalists(query_embedding, threshold, count, filter_beat)` function for semantic search. |
| `004_gmail_account_key.sql` | Adds `account_key` column to `gmail_tokens` for cross-process OAuth token sharing. |

---

## CORS Guidance

`CORS_ORIGINS` is used directly by FastAPI's CORS middleware (`api/main.py`). For production:

- Use a comma-separated list of exact origins over HTTPS.
- Do not add trailing slashes.
- Do not use wildcards unless you accept the increased attack surface.

Example:
```ini
CORS_ORIGINS=https://dashboard.yourdomain.com,https://app.yourdomain.com
```

---

## Tracking Pixel URL

Implemented route:
```
{TRACKING_BASE_URL}/open/{tracking_token}
```

For production, `TRACKING_BASE_URL` must be a reachable HTTPS domain. Browsers cannot execute HTTP tracking pixels from HTTPS email clients when `TRACKING_BASE_URL` is `http://...`.

---

## Checklist Before Production

- [ ] `.env` created and added to `.gitignore`.
- [ ] Migrations 001–004 applied to Supabase.
- [ ] RLS policies hardened for tenant isolation.
- [ ] App-level authentication enabled (JWT via Supabase Auth).
- [ ] Background worker configured for follow-up scheduling.
- [ ] Gmail tokens scoped per authenticated user, not shared `account_key`.
- [ ] `CORS_ORIGINS` restricted to known domains.
- [ ] `TRACKING_BASE_URL` points to HTTPS endpoint.
- [ ] Boolean verification commands return expected values for active integrations.

---

## Glossary

- **RLS** — Row Level Security in PostgreSQL/Supabase. Enforces row-level visibility based on policy conditions.
- **OAuth scope** — Permissions requested by an OAuth app. The application requests only `gmail.send`.
- **Account key** — Stable identifier for server-managed Gmail connections (local convenience, not multi-user safe).
- **Tenant** — An organization/entity isolating its journalists, campaigns, and outreach data from others.

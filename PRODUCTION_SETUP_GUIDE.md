# 🚀 OpenClaw PR Manager - Production Setup Guide

## Overview

This guide walks you through setting up the production-ready features of OpenClaw PR Manager, including:

- ✅ User authentication with Supabase Auth & JWT tokens
- ✅ Multi-tenant data isolation (organizations)
- ✅ Background job scheduler for automated follow-ups
- ✅ Rate limiting to prevent abuse
- ✅ Email infrastructure hardening (SMTP fallback, bounce handling, unsubscribe compliance)

---

## Quick Start Checklist

Before deploying to production, complete these steps in order:

1. [ ] Run database migrations in Supabase
2. [ ] Configure environment variables
3. [ ] Verify installation
4. [ ] Start API server with background workers
5. [ ] Test authentication flow
6. [ ] Configure email sending

---

## Step 1: Database Migrations

### Run Migration 005 (Auth & Multi-Tenancy)

**Location**: `db/migrations/005_auth_system.sql`

#### Steps:

1. **Open Supabase Dashboard**
   ```
   https://supabase.com/dashboard/project/wthwbojxiikcxicqxeco
   ```

2. **Navigate to SQL Editor**
   - Click "New Query" button
   - Copy entire content from `db/migrations/005_auth_system.sql`
   - Paste into editor
   - Click "Run" or press Ctrl+Enter

3. **Verify Success**
   The script outputs a comment: `Migration 005 completed successfully!`

#### What This Creates:

| Table | Purpose |
|-------|---------|
| `public.profiles` | User profiles extending auth.users |
| `organization_members` | User-to-org membership junction |
| `api_keys` | Programmatic access keys |
| `audit_logs` | Action logging for compliance |

| Function | Purpose |
|----------|---------|
| `is_org_member(org_id)` | Check user organization access |
| `get_current_user_org_ids()` | Get all orgs current user belongs to |
| `has_org_role(org_id, role)` | Check specific role permissions |

| RLS Policy | Protects |
|------------|----------|
| Multi-tenant isolation | All tenant-scoped tables |
| View own organizations | Prevent cross-org data leaks |

---

## Step 2: Environment Variables

### Update `.env` File

Add/modify these critical variables:

```bash
# ==============================================================================
# APPLICATION SETTINGS
# ==============================================================================
APP_ENV=production
APP_DEBUG=false

# JWT Token Configuration (CRITICAL - CHANGE THIS!)
JWT_SECRET_KEY=your-random-64-characters-here-generate-with-openssl
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=30

# Background Scheduler
SCHEDULER_ENABLED=true
SCHEDULER_INTERVAL_MINUTES=5

# Rate Limiting
RATE_LIMIT_ENABLED=true
EMAIL_SEND_RATE_PER_MINUTE=10
EMAIL_SEND_RATE_PER_DAY=500

# ==============================================================================
# SUPABASE CONFIGURATION
# ==============================================================================
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

# ==============================================================================
# SMTP FALLBACK (Optional but recommended)
# ==============================================================================
# If Gmail API fails, use SMTP as backup
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true

# ==============================================================================
# UNSUBSCRIBE MANAGEMENT (Security)
# ==============================================================================
UNSUBSCRIBE_SECRET_KEY=another-random-secret-key-for-unsubscribe-tokens

# ==============================================================================
# CORS CONFIGURATION  
# ==============================================================================
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

# For production, add your actual domain:
# CORS_ORIGINS=https://your-domain.com
```

### Generate Secure Keys

Use OpenSSL to generate secure secrets:

```powershell
# Generate JWT secret (64 characters hex)
openssl rand -hex 32

# Generate Unsubscribe secret (64 characters hex)
openssl rand -hex 32
```

Copy output and paste into `.env`.

---

## Step 3: Verify Installation

### Run Verification Script

After updating `.env`, verify everything is ready:

```powershell
cd "G:\OpenClaw PR Manager"

python scripts/verify_production_setup.py
```

**Expected Output:**

```
🔍 OPENCLAW PRODUCTION SETUP VERIFICATION
============================================================

✅ Python imports successful
✅ Migration 005 file exists
✅ .env configuration valid
✅ FastAPI routes registered
✅ APScheduler installed
✅ All files exist

✅ ALL CHECKS PASSED!

Your OpenClaw PR Manager is ready for production deployment.
```

If any checks fail, review the error messages above each ❌ symbol.

---

## Step 4: Start API Server with Background Workers

### Launch Command

```powershell
cd "G:\OpenClaw PR Manager"

# Terminal 1: Backend with auto-reload
python -m uvicorn api.main:app --reload --port 8000
```

### What Happens on Startup:

1. Loads environment variables from `.env`
2. Connects to Supabase
3. **STARTS BACKGROUND SCHEDULER** ⏰
4. Registers API routes
5. Logs startup status

### Expected Console Output:

```
Starting OpenClaw PR Manager Backend...
Supabase Configured: True
Scheduler started (interval: 5 minutes)
⏰ Background scheduler started (interval: 5 minutes)
Application initialized successfully
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000
```

If you see `Background scheduler disabled`, check that `SCHEDULER_ENABLED=true` in `.env`.

---

## Step 5: Test Authentication Flow

### 1. Register New User

```powershell
curl -X POST "http://localhost:8000/api/v1/auth/users/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"TestPass123\",\"full_name\":\"Test User\",\"organization_name\":\"My Company\"}"
```

**Expected Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Login with Credentials

```powershell
curl -X POST "http://localhost:8000/api/v1/auth/users/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"test@example.com\",\"password\":\"TestPass123\"}"
```

### 3. Get Current User Profile

```powershell
curl "http://localhost:8000/api/v1/auth/users/me" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

**Expected Response:**

```json
{
  "id": "user_test_at_example.com",
  "email": "test@example.com",
  "full_name": "Test User",
  "role": "owner",
  "active": true,
  "organizations": [
    {
      "id": "org_my_company",
      "role": "owner"
    }
  ]
}
```

### 4. Join Existing Organization

```powershell
curl -X POST "http://localhost:8000/api/v1/auth/users/join-organization" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d "{\"organization_id\":\"existing_org_uuid\",\"role\":\"member\"}"
```

---

## Step 6: Test Background Scheduler

### Watch Scheduler Logs

While the API server is running, watch console logs for scheduler activity:

```
▶️  Starting follow-up processing job...
✅ Follow-up job completed: processed=0, due=0
▶️  Starting follow-up processing job...  # Repeats every 5 minutes
```

### Manually Trigger Job

You can also trigger the follow-up processor manually via API:

```powershell
curl -X POST "http://localhost:8000/api/v1/outreach/process-follow-ups" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## Step 7: Test Email Infrastructure

### Enable Rate Limiting

Rate limiting is active by default when server starts. Monitor headers in responses:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
Retry-After: 60
```

### Test SMTP Fallback (Optional)

If Gmail API fails, system automatically tries SMTP:

```python
from services.email.smtp_fallback import smtp_fallback

# Check if configured
if smtp_fallback.is_configured():
    result = smtp_fallback.send_email(
        to="recipient@example.com",
        subject="Test SMTP Fallback",
        body_html="<p>This is a test email via SMTP.</p>",
        body_text="This is a test email via SMTP."
    )
    print(result)
```

### Test Bounce Handler

```python
from services.email.bounce_handler import bounce_handler

# Record a bounce
result = bounce_handler.record_bounce(
    outreach_id="abc-123",
    email="invalid@example.com",
    reason="550 5.1.1 User unknown",
    is_hard=True
)

print(f"Bounced: {result}")
print(f"Email suppressed: {bounce_handler.is_suppressed('invalid@example.com')}")

# Get statistics
stats = bounce_handler.get_bounce_stats()
print(stats)
```

### Test Unsubscribe Management

```python
from services.email.unsubscribe import unsubscribe_manager

# Generate unsubscribe link
outreach_id = "some-outreach-uuid"
link = unsubscribe_manager.get_unsubscribe_link(outreach_id)
print(f"Unsubscribe link: {link}")

# Process unsubscribe request
success = unsubscribe_manager.unsubscribe_from_campaign(
    outreach_id=outreach_id,
    email="user@example.com"
)
```

---

## Production Deployment Considerations

### Security Checklist

- [x] ✅ JWT secret key changed from default
- [x] ✅ Service role key never exposed to frontend
- [x] ✅ CORS origins restricted to specific domains
- [x] ✅ Rate limiting enabled
- [x] ✅ HTML escaping prevents XSS attacks
- [ ] ⏳ SSL certificates deployed (HTTPS required)
- [ ] ⏳ Database backups enabled (Supabase provides this)
- [ ] ⏳ Audit logs monitored and retained appropriately

### Performance Tips

1. **Use Redis for Queue Persistence**
   
   Replace in-memory queue with Redis-backed one:
   ```python
   limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
   ```

2. **Enable Caching**
   
   Add Redis/Memcached for frequently accessed data:
   ```python
   from django.core.cache import cache
   
   # Cache journalist list
   journalists = cache.get_or_set("journalist_list", fetch_journalists, timeout=300)
   ```

3. **Optimize Database Queries**
   
   Ensure indexes exist on commonly filtered columns:
   ```sql
   CREATE INDEX IF NOT EXISTS idx_journalists_email ON journalists(email);
   CREATE INDEX IF NOT EXISTS idx_outreach_next_followup ON outreach(next_followup_date)
       WHERE status IN ('pending', 'sent');
   ```

### Monitoring Recommendations

1. **Log Aggregation**
   - Use services like Datadog, Sentry, or CloudWatch
   - Set alerts for repeated errors

2. **Health Checks**
   ```python
   @app.get("/health")
   def health_check():
       return {
           "status": "healthy",
           "scheduler_running": hasattr(app.state, 'scheduler'),
           "supabase_connected": True
       }
   ```

3. **Metrics Export**
   - Track: emails sent, jobs executed, rate limit hits
   - Integrate with Prometheus/Grafana

---

## Troubleshooting

### Issue: Scheduler Not Starting

**Symptoms:** No follow-up job logs

**Fix:**
1. Check `SCHEDULER_ENABLED=true` in `.env`
2. Verify APScheduler installed: `pip install apscheduler`
3. Review server logs for errors during startup

### Issue: Cross-Tenant Data Leak Detected

**Symptoms:** User A sees User B's data

**Fix:**
1. Confirm migration 005 ran correctly
2. Check RLS policies are active:
   ```sql
   SELECT schemaname, tablename, policyname FROM pg_policies;
   ```
3. Verify repository code injects `organization_id` filter

### Issue: Rate Limit Too Strict

**Symptoms:** Frequent HTTP 429 errors

**Fix:**
1. Adjust limits in `.env`:
   ```bash
   EMAIL_SEND_RATE_PER_MINUTE=20
   ```
2. Restart server after change

### Issue: SMTP Fallback Not Working

**Symptoms:** Emails failing when Gmail API down

**Fix:**
1. Verify SMTP credentials in `.env`
2. Test manual connection:
   ```python
   import smtplib
   server = smtplib.SMTP("smtp.gmail.com", 587)
   server.login(username, password)
   ```
3. Check firewall allows outbound port 587

---

## Next Steps After Initial Setup

### Week 1: Testing & Validation

1. **User Acceptance Testing**
   - Register multiple users
   - Create organizations
   - Add journalists
   - Send pitches
   - Verify multi-tenant isolation

2. **Load Testing**
   - Simulate concurrent users
   - Test email queue under load
   - Measure response times

3. **Monitor & Optimize**
   - Review logs for patterns
   - Identify bottlenecks
   - Tune database queries

### Month 1: Production Readiness

1. **Backup Strategy**
   - Enable Supabase daily backups
   - Test restore procedure

2. **Incident Response**
   - Document common failure scenarios
   - Create runbooks for fixes
   - Set up alert channels

3. **Compliance**
   - GDPR/CCPA data handling
   - CAN-SPAM unsubscribe links
   - Privacy policy updates

---

## Resources

### Documentation Files

- `SETUP_INSTRUCTIONS.md` - Migration SQL scripts
- `docs/integrations.md` - Service setup guides
- `docs/security.md` - Security best practices
- `IMPLEMENTATION_COMPLETE.md` - Implementation report

### Key Code Locations

- Authentication: `core/auth.py`, `api/routers/auth_users.py`
- Background Jobs: `api/lifecyle.py`, `services/scheduler/follow_up.py`
- Email System: `services/email/email_queue.py`, `services/email/smtp_fallback.py`
- Multi-tenancy: `db/repositories/base_multitenant.py`, DB migrations

### Support

For issues or questions:
1. Review troubleshooting section above
2. Check relevant logs in API console
3. Verify all configuration values match requirements

---

**Congratulations!** 🎉 You've set up a production-ready media relations platform with enterprise-grade security and reliability features.

Happy building! 🚀

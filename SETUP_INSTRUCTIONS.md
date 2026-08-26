# 🚀 Quick Supabase Setup Guide

## ✅ Step 1: Credentials Configured

Your Supabase credentials have been saved to `.env`:
- **URL**: `https://wthwbojxiikcxicqxeco.supabase.co`
- **Key**: Configured (anon/public key)
- **Service Role**: Configured (for admin operations)

---

## ⚠️ Step 2: Run Migrations (REQUIRED)

You must execute these 4 SQL migrations in your **Supabase Dashboard** to create all tables and functions:

### How to Run Migrations:

1. **Open your Supabase Dashboard:**
   - Go to: https://supabase.com/dashboard/project/wthwbojxiikcxicqxeco  
   - Navigate to: **SQL Editor** → Click **"New Query"**

2. **Copy & Paste each migration file below, one at a time:**

---

### 📝 Migration 1: Initial Schema (CREATE ALL TABLES)

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create organizations table (for potential multi-tenant future)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create journalists table
CREATE TABLE IF NOT EXISTS journalists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    outlet VARCHAR(255) NOT NULL,
    outlet_url TEXT,
    beats TEXT[] DEFAULT '{}',
    topic_keywords TEXT[],
    
    -- OpenClaw 4D scoring fields
    category_match INTEGER DEFAULT 0,
    influence_score REAL DEFAULT 0.0,
    history_score REAL DEFAULT 0.0,
    relationship_score REAL DEFAULT 0.0,
    overall_score REAL DEFAULT 0.0,
    
    -- Vector embedding for semantic search
    embedding VECTOR(384),
    
    -- Metadata
    notes TEXT,
    status VARCHAR(50) DEFAULT 'active',
    last_contacted_at TIMESTAMP WITH TIME ZONE,
    contact_count INTEGER DEFAULT 0,
    tags TEXT[],
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Story embedding for matching
    story_embedding VECTOR(768),
    
    start_date DATE,
    end_date DATE,
    status VARCHAR(50) DEFAULT 'planning',
    
    -- Metadata
    objective VARCHAR(255),
    budget DECIMAL(10,2),
    priority VARCHAR(50) DEFAULT 'medium',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create outreach table
CREATE TABLE IF NOT EXISTS outreach (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    journalist_id UUID REFERENCES journalists(id) ON DELETE CASCADE,
    
    -- Email tracking
    tracking_token UUID UNIQUE DEFAULT uuid_generate_v4(),
    sent_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    replied_at TIMESTAMP WITH TIME ZONE,
    bounced_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- Status tracking
    current_status VARCHAR(50) DEFAULT 'pending',
    next_followup_date TIMESTAMP WITH TIME ZONE,
    followup_stage INTEGER DEFAULT 0,
    
    -- Content
    initial_pitch_body TEXT,
    reply_body TEXT,
    reply_from_email VARCHAR(255),
    
    -- Simulated mode flag (if not using real Gmail)
    simulated BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create templates table (for AI pitch generation)
CREATE TABLE IF NOT EXISTS templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    model VARCHAR(50) NOT NULL DEFAULT 'gpt-4o',
    template_type VARCHAR(50) NOT NULL DEFAULT 'default',
    content TEXT NOT NULL,
    variables TEXT[],
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create gmail_tokens table
CREATE TABLE IF NOT EXISTS gmail_tokens (
    id SERIAL PRIMARY KEY,
    account_key TEXT UNIQUE DEFAULT 'default_user',
    user_id UUID REFERENCES auth.users(id),
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expiry TIMESTAMP WITH TIME ZONE,
    scopes TEXT[] DEFAULT ARRAY['gmail.send'],
    email_address VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_journalists_outlet ON journalists(outlet);
CREATE INDEX IF NOT EXISTS idx_journalists_beats ON journalists USING GIN(beats);
CREATE INDEX IF NOT EXISTS idx_journalists_overall_score ON journalists(overall_score DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_outreach_campaign ON outreach(campaign_id);
CREATE INDEX IF NOT EXISTS idx_outreach_journalist ON outreach(journalist_id);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(current_status);
CREATE INDEX IF NOT EXISTS idx_templates_model ON templates(model);
CREATE INDEX IF NOT EXISTS gmail_tokens_account_idx ON gmail_tokens(account_key);

-- Insert default templates (must match Python code's default_templates list)
INSERT INTO templates (name, model, template_type, content, is_default) VALUES
('GPT Default Pitch', 'gpt-4o', 'default', 
 'Subject: {outlet} story idea\n\nHi {{journalist_name}},\n\nI noticed you cover {beats} at {{outlet}}. \n\n{story_preview}\n\nWould love to discuss how this aligns with what readers are following.\n\nBest regards\n{{sender_name}}', 
 '[pitch_topic]', TRUE),
('DeepSeek Alternative', 'deepseek-chat', 'default',
 'Subject: {outlet} story angle\n\nHey {{journalist_name}},\n\nFollowing your work on {beats}. Here''s a relevant opportunity.\n\n{story_preview}\n\nInterested in chatting?\n\nCheers\n{{sender_name}}',
 '[pitch_topic]', FALSE);

-- Add updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add triggers to all tables
DROP TRIGGER IF EXISTS update_organizations_timestamp ON organizations;
DROP TRIGGER IF EXISTS update_journalists_timestamp ON journalists;
DROP TRIGGER IF EXISTS update_campaigns_timestamp ON campaigns;
DROP TRIGGER IF EXISTS update_outreach_timestamp ON outreach;
DROP TRIGGER IF EXISTS update_templates_timestamp ON templates;
DROP TRIGGER IF EXISTS update_gmail_tokens_timestamp ON gmail_tokens;

CREATE TRIGGER update_organizations_timestamp
BEFORE UPDATE ON organizations
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_journalists_timestamp
BEFORE UPDATE ON journalists
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_campaigns_timestamp
BEFORE UPDATE ON campaigns
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_outreach_timestamp
BEFORE UPDATE ON outreach
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_timestamp
BEFORE UPDATE ON templates
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_gmail_tokens_timestamp
BEFORE UPDATE ON gmail_tokens
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable pgvector extension (must be done separately if not enabled)
-- If this fails, go to Supabase Dashboard → Extensions → Enable pgvector manually
COMMENT ON EXTENSION vector IS 'vector similarity search extension';
```

---

### 📝 Migration 2: RLS Policies (ACCESS CONTROL)

```sql
-- IMPORTANT: Development-permissive policies ONLY
-- Replace these before production use!

-- Allow all users to access everything (DEVELOPMENT MODE)
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on organizations" ON organizations FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE journalists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on journalists" ON journalists FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on campaigns" ON campaigns FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE outreach ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on outreach" ON outreach FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow all on templates" ON templates FOR ALL USING (true) WITH CHECK (true);

ALTER TABLE gmail_tokens ENABLE ROW LEVEL SECURITY;
-- Users can only manage their own tokens OR service role
CREATE POLICY "Manage own tokens" ON gmail_tokens FOR ALL
USING (auth.uid() = user_id OR auth.role() = 'service_role');
```

---

### 📝 Migration 3: Functions (SEMANTIC SEARCH)

```sql
-- Semantic search function for journalists (using cosine similarity)
CREATE OR REPLACE FUNCTION match_journalists(
    query_embedding VECTOR(384),
    match_threshold FLOAT DEFAULT 0.0,
    match_limit INT DEFAULT 10,
    p_organization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    full_name VARCHAR(255),
    email VARCHAR(255),
    outlet VARCHAR(255),
    beats TEXT[],
    category_match INTEGER,
    influence_score REAL,
    history_score REAL,
    relationship_score REAL,
    overall_score REAL,
    similarity FLOAT
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    j.id,
    j.full_name,
    j.email,
    j.outlet,
    j.beats,
    j.category_match,
    j.influence_score,
    j.history_score,
    j.relationship_score,
    j.overall_score,
    1 - (j.embedding <=> query_embedding) AS similarity
  FROM journalists j
  WHERE j.embedding IS NOT NULL
    AND 1 - (j.embedding <=> query_embedding) > match_threshold
    AND (p_organization_id IS NULL OR j.organization_id = p_organization_id)
  ORDER BY similarity DESC
  LIMIT match_limit;
$$;

-- Semantic search function for campaigns (using cosine similarity)
CREATE OR REPLACE FUNCTION match_campaigns(
    query_embedding VECTOR(768),
    match_threshold FLOAT DEFAULT 0.0,
    match_limit INT DEFAULT 10,
    p_organization_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    title VARCHAR(255),
    description TEXT,
    story_embedding VECTOR(768),
    similarity FLOAT
)
LANGUAGE sql
STABLE
AS $$
  SELECT
    c.id,
    c.title,
    c.description,
    c.story_embedding,
    1 - (c.story_embedding <=> query_embedding) AS similarity
  FROM campaigns c
  WHERE c.story_embedding IS NOT NULL
    AND 1 - (c.story_embedding <=> query_embedding) > match_threshold
    AND (p_organization_id IS NULL OR c.organization_id = p_organization_id)
  ORDER BY similarity DESC
  LIMIT match_limit;
$$;
```

---

### 📝 Migration 4: Gmail Account Key (TOKEN SHARING)

```sql
-- This migration adds account_key column for cross-process token sharing
-- Run this AFTER migration 001 has already created gmail_tokens table

-- Check if account_key column exists (add if missing)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'gmail_tokens' 
        AND column_name = 'account_key'
    ) THEN
        ALTER TABLE gmail_tokens ADD COLUMN account_key TEXT UNIQUE DEFAULT 'default_user';
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'gmail_tokens' 
        AND column_name = 'user_id'
    ) THEN
        ALTER TABLE gmail_tokens ADD COLUMN user_id UUID REFERENCES auth.users(id);
    END IF;
END
$$;

-- Update existing record to use account_key pattern
UPDATE gmail_tokens SET account_key = 'default_user' WHERE account_key IS NULL;
```

---

## ✅ Step 3: Verify Migration Success

After running all 4 migrations, verify with this command:

```bash
python -c "from config.settings import get_settings; s=get_settings(); print('Supabase configured:', s.is_supabase_configured)"
```

Expected output:
```
Supabase configured: True
```

---

## 🎉 Step 4: You're Ready!

Now you can:
1. Start FastAPI server: `python -m uvicorn api.main:app --reload --port 8000`
2. Launch dashboard: `python -m streamlit run dashboard/app.py`
3. Visit `http://localhost:8501` to see your new Dark Space UI

---

## ⚠️ Security Warning

**The current RLS policies (Migration 2) are permissive for development only!**

Before deploying to production:
1. Implement proper application authentication (Supabase Auth / JWT)
2. Create organization membership tables
3. Replace permissive RLS policies with strict tenant isolation
4. Use service role keys ONLY on backend, never expose to frontend

See `docs/security.md` for detailed security guidelines.

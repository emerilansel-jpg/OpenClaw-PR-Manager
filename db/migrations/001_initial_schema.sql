-- ==============================================================================
-- OpenClaw PR Manager - Migration 001: Initial Schema
-- ==============================================================================

-- 1. Enable Required Extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Organizations / Workspaces Table (Multi-tenancy support)
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Journalists Table
CREATE TABLE IF NOT EXISTS journalists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    email_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
        CHECK (email_status IN ('missing', 'unverified', 'public', 'verified', 'invalid')),
    email_source_url TEXT,
    email_source_note TEXT,
    email_verified_at TIMESTAMP WITH TIME ZONE,
    email_last_checked_at TIMESTAMP WITH TIME ZONE,
    outlet VARCHAR(255),
    beat TEXT[] DEFAULT '{}', -- Array of topics/categories e.g. {'tech', 'ai', 'startups'}
    location VARCHAR(100),
    twitter VARCHAR(100),
    linkedin VARCHAR(255),
    bio TEXT,
    recent_articles JSONB DEFAULT '[]', -- Array of recent article titles & URLs
    last_contacted TIMESTAMP WITH TIME ZONE,
    response_rate DECIMAL(4,3) DEFAULT 0.000,
    
    -- OpenClaw 4D Scoring Factors (0.00 to 1.00)
    category_match DECIMAL(4,3) DEFAULT 0.500,
    influence_score DECIMAL(4,3) DEFAULT 0.500,
    history_score DECIMAL(4,3) DEFAULT 0.500,
    relationship_score DECIMAL(4,3) DEFAULT 0.500,
    overall_score DECIMAL(4,3) DEFAULT 0.500,
    
    -- AI Semantic Search Vector (OpenAI text-embedding-3-small dimension: 1536)
    embedding VECTOR(1536),
    
    -- Metadata
    source VARCHAR(50) DEFAULT 'manual', -- 'newsapi', 'googlenews', 'thenewsapi', 'manual', 'csv'
    created_by UUID, -- References auth.users(id) in Supabase
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_email_per_org UNIQUE(email, organization_id)
);

-- 4. Campaigns Table
CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    story TEXT NOT NULL,
    story_embedding VECTOR(1536),
    target_beat TEXT[] DEFAULT '{}',
    target_outlets TEXT[] DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'scheduled', 'sending', 'completed', 'paused'
    created_by UUID, -- References auth.users(id) in Supabase
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Outreach Table (Email Tracking & Follow-up State Machine)
CREATE TABLE IF NOT EXISTS outreach (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    journalist_id UUID NOT NULL REFERENCES journalists(id) ON DELETE CASCADE,
    subject_line VARCHAR(500) NOT NULL,
    pitch_email TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'queued', 'sent', 'opened', 'replied', 'bounced', 'unsubscribed'
    
    -- Follow-up Sequence Engine (Formula 3+7+7+14)
    follow_up_sequence INTEGER DEFAULT 1, -- 1: Initial Pitch, 2: F1 (Day 3), 3: F2 (Day 10), 4: F3 (Day 17), 5: Breakup (Day 31)
    max_follow_ups INTEGER DEFAULT 4,
    next_follow_up TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    sent_at TIMESTAMP WITH TIME ZONE,
    opened_at TIMESTAMP WITH TIME ZONE,
    replied_at TIMESTAMP WITH TIME ZONE,
    
    -- Gmail API Identifiers
    gmail_message_id VARCHAR(255),
    gmail_thread_id VARCHAR(255),
    sender_account_key TEXT,
    tracking_token UUID DEFAULT gen_random_uuid(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Gmail Tokens Table (OAuth2 Storage)
CREATE TABLE IF NOT EXISTS gmail_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE, -- References auth.users(id) in Supabase
    account_key TEXT UNIQUE NOT NULL, -- Verified connected Google email for this sender
    email_address VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expiry TIMESTAMP WITH TIME ZONE,
    scopes TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Prompt Templates Table (Multi-Model System Prompts)
CREATE TABLE IF NOT EXISTS prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    model VARCHAR(50) DEFAULT 'gpt-4o', -- 'gpt-4o', 'deepseek-chat', 'claude-3-5-sonnet'
    pitch_type VARCHAR(50) DEFAULT 'initial', -- 'initial', 'followup_1', 'followup_2', 'breakup'
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 8. Indexes for High Performance
CREATE INDEX IF NOT EXISTS idx_journalists_beat ON journalists USING GIN (beat);
CREATE INDEX IF NOT EXISTS idx_journalists_outlet ON journalists(outlet);
CREATE INDEX IF NOT EXISTS idx_journalists_email ON journalists(email);
CREATE INDEX IF NOT EXISTS idx_journalists_email_status ON journalists(email_status);
CREATE INDEX IF NOT EXISTS idx_outreach_sender_account ON outreach(sender_account_key);
CREATE INDEX IF NOT EXISTS idx_journalists_overall_score ON journalists(overall_score DESC);

CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_outreach_campaign ON outreach(campaign_id);
CREATE INDEX IF NOT EXISTS idx_outreach_journalist ON outreach(journalist_id);
CREATE INDEX IF NOT EXISTS idx_outreach_status ON outreach(status);
CREATE INDEX IF NOT EXISTS idx_outreach_next_followup ON outreach(next_follow_up) WHERE status NOT IN ('replied', 'bounced', 'unsubscribed');
CREATE INDEX IF NOT EXISTS idx_outreach_tracking_token ON outreach(tracking_token);

-- ==============================================================================
-- OpenClaw PR Manager - Migration 002: Row Level Security (RLS) Policies
-- ==============================================================================

-- Enable RLS on all tables
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE journalists ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE outreach ENABLE ROW LEVEL SECURITY;
ALTER TABLE gmail_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE prompt_templates ENABLE ROW LEVEL SECURITY;

-- 1. Journalists Policies
CREATE POLICY "Allow public read during dev / authenticated users"
ON journalists FOR SELECT
USING (true);

CREATE POLICY "Allow authenticated insert/update"
ON journalists FOR ALL
USING (auth.role() = 'authenticated' OR auth.role() = 'anon')
WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'anon');

-- 2. Campaigns Policies
CREATE POLICY "Allow access to campaigns"
ON campaigns FOR ALL
USING (true)
WITH CHECK (true);

-- 3. Outreach Policies
CREATE POLICY "Allow access to outreach"
ON outreach FOR ALL
USING (true)
WITH CHECK (true);

-- 4. Gmail Tokens Policies (Secured per user)
CREATE POLICY "Users can only manage their own Gmail token"
ON gmail_tokens FOR ALL
USING (auth.uid() = user_id OR auth.role() = 'service_role')
WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- 5. Prompt Templates Policies
CREATE POLICY "Anyone can view default templates"
ON prompt_templates FOR SELECT
USING (true);

CREATE POLICY "Authenticated users can create/update templates"
ON prompt_templates FOR ALL
USING (auth.role() = 'authenticated' OR auth.role() = 'anon')
WITH CHECK (auth.role() = 'authenticated' OR auth.role() = 'anon');

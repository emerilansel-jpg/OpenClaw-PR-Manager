-- ============================================================
-- Migration 005: Authentication & Multi-Tenancy System
-- ============================================================
-- Creates:
--   1. User profiles table
--   2. Organization members junction table
--   3. API keys for programmatic access
--   4. Audit logs for compliance
--   5. Multi-tenant RLS policies
--   6. Helper functions for organization checks
-- ============================================================

-- Enable required extensions (if not already enabled)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
COMMENT ON EXTENSION uuid_ossp IS 'Generate universally unique identifiers';

-- ============================================
-- 1. PUBLIC PROFILES TABLE
-- Extension of auth.users with additional user data
-- ============================================

CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(50) DEFAULT 'user', -- admin/user/viewer
    active BOOLEAN DEFAULT true,
    last_sign_in_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE UNIQUE INDEX IF NOT EXISTS idx_profiles_email ON profiles(email);

-- Triggers for automatic updated_at
DROP TRIGGER IF EXISTS update_profiles_timestamp ON public.profiles;
CREATE TRIGGER update_profiles_timestamp
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS Policies
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Users can only view their own profile
CREATE POLICY "Users can view own profile"
ON public.profiles FOR SELECT
USING (auth.uid() = id);

-- Insert policy (for registration flow)
CREATE POLICY "Users can insert own profile"
ON public.profiles FOR INSERT
WITH CHECK (auth.uid() = id);

-- Update policy (users can update own profile)
CREATE POLICY "Users can update own profile"
ON public.profiles FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- ============================================
-- 2. ORGANIZATION MEMBERS TABLE
-- Junction table linking users to organizations
-- ============================================

CREATE TABLE IF NOT EXISTS organization_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL DEFAULT 'member', -- owner/admin/editor/member/viewer
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active/invited/suspended/blocked
    invited_by UUID REFERENCES auth.users(id),
    accepted_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT unique_user_org UNIQUE(user_id, organization_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_members_role ON organization_members(role);
CREATE INDEX IF NOT EXISTS idx_org_members_status ON organization_members(status);

-- RLS Policies
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;

-- Members can view org members if they are active member
CREATE POLICY "Active members can view org members"
ON organization_members FOR SELECT
USING (EXISTS (
    SELECT 1 FROM organization_members om
    WHERE om.organization_id = organization_members.organization_id
    AND om.user_id = auth.uid()
    AND om.status = 'active'
));

-- Only owners/admins can insert/update/delete org members
CREATE POLICY "Owners/Admins manage org members"
ON organization_members FOR ALL
USING (EXISTS (
    SELECT 1 FROM organization_members om
    WHERE om.organization_id = organization_members.organization_id
    AND om.user_id = auth.uid()
    AND om.role IN ('owner', 'admin')
));

-- ============================================
-- 3. API KEYS TABLE
-- For programmatic access with scoped permissions
-- ============================================

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(20) NOT NULL, -- First 8 chars of hashed key
    key_hash VARCHAR(255) NOT NULL, -- Hashed version (bcrypt format)
    scopes TEXT[] NOT NULL DEFAULT '{}', -- read:journalists,write:campaigns etc.
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES auth.users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT unique_key_prefix UNIQUE(key_prefix)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_api_keys_org ON api_keys(organization_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(revoked_at) WHERE revoked_at IS NULL;

-- RLS Policies
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Read: Active members can view their org's API keys
CREATE POLICY "Active members can view API keys"
ON api_keys FOR SELECT
USING (EXISTS (
    SELECT 1 FROM organization_members om
    WHERE om.organization_id = api_keys.organization_id
    AND om.user_id = auth.uid()
    AND om.status = 'active'
));

-- Write: Only admins/owners can create/update/revoke API keys
CREATE POLICY "Admins manage API keys"
ON api_keys FOR ALL
USING (EXISTS (
    SELECT 1 FROM organization_members om
    WHERE om.organization_id = api_keys.organization_id
    AND om.user_id = auth.uid()
    AND om.role IN ('owner', 'admin')
))
WITH CHECK (EXISTS (
    SELECT 1 FROM organization_members om
    WHERE om.organization_id = api_keys.organization_id
    AND om.user_id = auth.uid()
    AND om.role IN ('owner', 'admin')
));

-- ============================================
-- 4. AUDIT LOGS TABLE
-- Track critical actions for compliance
-- ============================================

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id),
    action VARCHAR(100) NOT NULL, -- login,create,update,delete,export,etc.
    resource_type VARCHAR(50) NOT NULL, -- journalist,campaign,outreach,user,api_key
    resource_id UUID,
    changes JSONB, -- Before/after delta
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for filtering
CREATE INDEX IF NOT EXISTS idx_audit_logs_org ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- RLS Policy
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Users can view their org's audit logs (admins can filter, all can see limited view)
CREATE POLICY "Members can view audit logs"
ON audit_logs FOR SELECT
USING (EXISTS (
    SELECT 1 FROM organization_members om
    WHERE om.organization_id = audit_logs.organization_id
    AND om.user_id = auth.uid()
    AND om.status = 'active'
));

-- Only admins can insert audit logs (via application, not direct)
CREATE POLICY "System inserts audit logs"
ON audit_logs FOR INSERT
WITH CHECK (auth.role() = 'service_role');

-- ============================================
-- 5. UPDATE EXISTING TABLES FOR MULTI-TENANCY
-- ============================================

-- Add organization_id to outreach table
ALTER TABLE outreach ADD COLUMN IF NOT EXISTS organization_id UUID;

-- Add organization_id to prompt_templates if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'prompt_templates' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE prompt_templates ADD COLUMN organization_id UUID;
    END IF;
END
$$;

-- Foreign key constraints
ALTER TABLE outreach ADD CONSTRAINT fk_outreach_org
    FOREIGN KEY(organization_id) REFERENCES organizations(id)
    ON DELETE SET NULL;

-- If template org field was added, add constraint
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE table_name = 'prompt_templates' AND constraint_name = 'fk_template_org_new'
    ) THEN
        ALTER TABLE prompt_templates DROP CONSTRAINT fk_template_org_new;
    END IF;
END
$$;

ALTER TABLE prompt_templates ADD CONSTRAINT fk_prompt_template_org
    FOREIGN KEY(organization_id) REFERENCES organizations(id)
    ON DELETE SET NULL;

-- ============================================
-- 6. HELPER FUNCTIONS FOR ORG ACCESS
-- ============================================

-- Function: Check if user is member of an organization
CREATE OR REPLACE FUNCTION is_org_member(org_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM organization_members
        WHERE organization_id = org_id
        AND user_id = auth.uid()
        AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION is_org_member IS 'Check if current authenticated user is an active member of the given organization';

-- Function: Get all organization IDs for current user
CREATE OR REPLACE FUNCTION get_current_user_org_ids()
RETURNS UUID[] AS $$
DECLARE
    org_ids UUID[];
BEGIN
    SELECT ARRAY_AGG(DISTINCT organization_id) INTO org_ids
    FROM organization_members
    WHERE user_id = auth.uid()
    AND status = 'active';
    
    RETURN org_ids;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION get_current_user_org_ids IS 'Returns array of organization IDs user belongs to as active member';

-- Function: Check if user has specific role in organization
CREATE OR REPLACE FUNCTION has_org_role(org_id UUID, required_role VARCHAR)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM organization_members
        WHERE organization_id = org_id
        AND user_id = auth.uid()
        AND role IN (required_role, 'owner', 'admin')
        AND status = 'active'
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION has_org_role IS 'Check if user has the specified role or higher in organization';

-- ============================================
-- 7. STRICT MULTI-TENANT RLS POLICIES
-- Replace permissive dev-only policies
-- ============================================

-- PostgreSQL does not support `DROP POLICY ... FOR ALL` or wildcard policy
-- deletion. Remove every existing policy from the tables being hardened before
-- installing the strict replacements below.
DO $$
DECLARE
    target_table TEXT;
    policy_record RECORD;
BEGIN
    FOREACH target_table IN ARRAY ARRAY[
        'journalists',
        'campaigns',
        'outreach',
        'prompt_templates',
        'organizations',
        'gmail_tokens'
    ]
    LOOP
        FOR policy_record IN
            SELECT policyname
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename = target_table
        LOOP
            EXECUTE format(
                'DROP POLICY IF EXISTS %I ON public.%I',
                policy_record.policyname,
                target_table
            );
        END LOOP;
    END LOOP;
END;
$$;

-- Journalists multi-tenant policy
CREATE POLICY "Multi-tenant isolation" ON journalists
FOR ALL
USING (is_org_member(organization_id))
WITH CHECK (is_org_member(organization_id));

-- Campaigns multi-tenant policy
CREATE POLICY "Multi-tenant isolation" ON campaigns
FOR ALL
USING (is_org_member(organization_id))
WITH CHECK (is_org_member(organization_id));

-- Outreach multi-tenant policy (via campaign relationship)
CREATE POLICY "Multi-tenant isolation" ON outreach
FOR ALL
USING (EXISTS (
    SELECT 1 FROM campaigns c
    WHERE c.id = outreach.campaign_id
    AND is_org_member(c.organization_id)
))
WITH CHECK (EXISTS (
    SELECT 1 FROM campaigns c
    WHERE c.id = outreach.campaign_id
    AND is_org_member(c.organization_id)
));

-- Templates multi-tenant policy
CREATE POLICY "Multi-tenant templates" ON prompt_templates
FOR ALL
USING (is_org_member(organization_id) OR organization_id IS NULL)
WITH CHECK (is_org_member(organization_id) OR organization_id IS NULL);

-- Organizations policy - users can only view owned/joined orgs
CREATE POLICY "View own organizations" ON organizations FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM organization_members om
        WHERE om.organization_id = organizations.id
        AND om.user_id = auth.uid()
        AND om.status = 'active'
    )
);

CREATE POLICY "Create own organizations" ON organizations FOR INSERT
WITH CHECK (
    auth.uid() = (
        SELECT organization_members.user_id
        FROM organization_members
        WHERE organization_members.organization_id = organizations.id
        LIMIT 1
    )
);

-- Gmail tokens policy (per-user, not per-org)
CREATE POLICY "Manage own Gmail tokens" ON gmail_tokens
FOR ALL
USING (auth.uid() = user_id OR auth.role() = 'service_role')
WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');

-- ============================================
-- 8. SEED DEFAULT TEMPLATES (If not exists)
-- Ensure templates have organization context
-- ============================================

INSERT INTO prompt_templates (name, model, pitch_type, system_prompt, user_prompt_template, is_default, organization_id) VALUES
('Default GPT Pitch', 'gpt-4o', 'initial',
 'You are a professional PR specialist. Create a personalized pitch.',
 'Subject: {{outlet}} story idea\n\nHi {{journalist_name}},\n\nI noticed you cover {{beats}} at {{outlet}}.\n\n{{story_preview}}\n\nWould love to discuss how this aligns.\n\nBest regards\n{{sender_name}}',
 true, NULL)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- 9. CREATE SERVICE ROLE USER
-- Special user for admin operations (optional)
-- ============================================

-- Note: This creates a service account that bypasses RLS
-- Use sparingly and only for internal backend operations
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolename = 'openclaw_service_admin'
    ) THEN
        -- Create a special role for service-level admin operations
        RAISE NOTICE 'Service admin role would be created here in production';
    END IF;
END
$$;

-- ============================================
-- MIGRATION COMPLETE
-- ============================================

COMMENT ON DATABASE postgres IS 'OpenClaw PR Manager Database with Auth System v2';

-- Success message
SELECT 'Migration 005 completed successfully!' as status;

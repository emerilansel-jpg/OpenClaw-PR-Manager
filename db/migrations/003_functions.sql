-- ==============================================================================
-- OpenClaw PR Manager - Migration 003: Stored Procedures & Triggers
-- ==============================================================================

-- 1. Auto-update updated_at timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables
DROP TRIGGER IF EXISTS trg_journalists_updated_at ON journalists;
CREATE TRIGGER trg_journalists_updated_at
BEFORE UPDATE ON journalists
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_campaigns_updated_at ON campaigns;
CREATE TRIGGER trg_campaigns_updated_at
BEFORE UPDATE ON campaigns
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_outreach_updated_at ON outreach;
CREATE TRIGGER trg_outreach_updated_at
BEFORE UPDATE ON outreach
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2. pgvector Semantic Search Function for Journalists Matching
-- Calculates cosine similarity: 1 - (embedding <=> query_embedding)
CREATE OR REPLACE FUNCTION match_journalists(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 20,
    filter_beat TEXT[] DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    name VARCHAR,
    email VARCHAR,
    outlet VARCHAR,
    beat TEXT[],
    location VARCHAR,
    bio TEXT,
    overall_score DECIMAL,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        j.id,
        j.name,
        j.email,
        j.outlet,
        j.beat,
        j.location,
        j.bio,
        j.overall_score,
        CAST(1 - (j.embedding <=> query_embedding) AS FLOAT) AS similarity
    FROM journalists j
    WHERE 
        j.embedding IS NOT NULL
        AND 1 - (j.embedding <=> query_embedding) >= match_threshold
        AND (filter_beat IS NULL OR j.beat && filter_beat)
    ORDER BY similarity DESC, j.overall_score DESC
    LIMIT match_count;
END;
$$;

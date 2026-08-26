-- Persist Gmail OAuth tokens across the separate FastAPI and Streamlit processes.
-- The previous implementation queried the UUID user_id column with "default_user".
ALTER TABLE gmail_tokens
ADD COLUMN IF NOT EXISTS account_key TEXT;

UPDATE gmail_tokens
SET account_key = COALESCE(account_key, user_id::TEXT, id::TEXT)
WHERE account_key IS NULL;

ALTER TABLE gmail_tokens
ALTER COLUMN account_key SET DEFAULT 'default_user';

ALTER TABLE gmail_tokens
ALTER COLUMN account_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_gmail_tokens_account_key
ON gmail_tokens(account_key);

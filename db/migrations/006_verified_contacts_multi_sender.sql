-- OpenClaw PR Manager - verified contact evidence and multi-Gmail senders

-- A discovered byline is not proof of an email address. These fields keep the
-- source and verification state visible before a contact can be used.
ALTER TABLE journalists
ADD COLUMN IF NOT EXISTS email_status VARCHAR(20) NOT NULL DEFAULT 'unverified';

ALTER TABLE journalists
ADD COLUMN IF NOT EXISTS email_source_url TEXT;

ALTER TABLE journalists
ADD COLUMN IF NOT EXISTS email_source_note TEXT;

ALTER TABLE journalists
ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE journalists
ADD COLUMN IF NOT EXISTS email_last_checked_at TIMESTAMP WITH TIME ZONE;

ALTER TABLE journalists
DROP CONSTRAINT IF EXISTS journalists_email_status_check;

ALTER TABLE journalists
ADD CONSTRAINT journalists_email_status_check
CHECK (email_status IN ('missing', 'unverified', 'public', 'verified', 'invalid'));

CREATE INDEX IF NOT EXISTS idx_journalists_email_status
ON journalists(email_status);

-- Pin every outreach thread to the Gmail account that sent the initial pitch.
-- Follow-ups must use the same account and Gmail thread.
ALTER TABLE outreach
ADD COLUMN IF NOT EXISTS sender_account_key TEXT;

CREATE INDEX IF NOT EXISTS idx_outreach_sender_account
ON outreach(sender_account_key);

-- Older OAuth rows used a placeholder identity. New connections use the
-- verified Google email address as account_key and email_address.
UPDATE gmail_tokens
SET email_address = account_key
WHERE email_address = 'me' AND account_key LIKE '%@%';

ALTER TABLE gmail_tokens
ALTER COLUMN account_key DROP DEFAULT;

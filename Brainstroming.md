Brainstorming: Membangun Sistem PR Manager di Atas OpenClaw dengan Supabase, Scraping Jurnalis, Multi-AI, Gmail API, dan Web Dashboard
1. Visi & Tujuan
Membangun sistem PR Management yang:

Berbasis OpenClaw PR Manager sebagai mesin utama (https://github.com/ZhenRobotics/openclaw-public-relations-manager)

Menggunakan Supabase sebagai backend-as-a-service (database, auth, storage, realtime)

Mengumpulkan database jurnalis secara otomatis dari sumber gratis

Mengirim email pitch melalui Gmail API (OAuth2) dengan deliverability tinggi

Menggunakan multi-model AI (GPT dan DeepSeek) untuk generate email pitch yang personal

Memiliki dashboard web untuk operasional sehari-hari

Menerapkan follow-up system dengan formula 3+7+7+14 hari

2. Mengapa Supabase?
Supabase adalah open-source Firebase alternative yang menyediakan semua kebutuhan backend dalam satu platform:

Fitur Supabase	Manfaat untuk Sistem PR
PostgreSQL Database	Database relasional yang mature, support JSON, array, dan pgvector untuk AI
Authentication	Auth built-in (email/password, Google OAuth, magic link)
Storage	Untuk menyimpan lampiran email, template, dan aset campaign
Realtime	Update live untuk tracking email (opened, replied)
Edge Functions	Serverless functions untuk webhook tracking email
Row Level Security (RLS)	Keamanan data per user/organisasi
pgvector	Untuk semantic search dan AI-based journalist matching
Free Tier	500 MB database, 2 GB storage, cukup untuk MVP
Supabase juga memiliki integrasi native dengan OpenClaw melalui plugin openclaw-supabase yang menyediakan CRUD, DDL, dan Raw SQL.

3. Komponen Utama Sistem
3.1. Core Engine: OpenClaw PR Manager
Sumber Utama: https://github.com/ZhenRobotics/openclaw-public-relations-manager

Supabase dapat diintegrasikan dengan OpenClaw melalui:

OpenClaw Supabase Plugin (@prbelief/supabase-db-admin) untuk manajemen database

Composio untuk menghubungkan OpenClaw ke Supabase dengan authentication management

OpenClaw Data Importer untuk mengimpor data jurnalis dari CSV/JSON ke Supabase

3.2. Database dengan Supabase
3.2.1. Setup Supabase
python
# Installasi
pip install supabase python-dotenv sqlmodel asyncpg
# atau
pip install fastapi-supabase  # untuk integrasi yang lebih mudah[reference:12]
3.2.2. Koneksi ke Supabase (Async)
python
import os
from supabase import create_async_client
from fastapi import FastAPI

app = FastAPI()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inisialisasi async client[reference:13][reference:14]
supabase = await create_async_client(SUPABASE_URL, SUPABASE_KEY)
3.2.3. Schema Database (SQL untuk Supabase)
sql
-- Enable pgvector untuk AI semantic search[reference:15]
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabel Jurnalis
CREATE TABLE journalists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    outlet VARCHAR(255),
    beat TEXT[], -- array of categories
    location VARCHAR(100),
    twitter VARCHAR(100),
    linkedin VARCHAR(255),
    last_contacted TIMESTAMP,
    response_rate DECIMAL(3,2),
    -- OpenClaw 4D scoring
    category_match DECIMAL(3,2),
    influence_score DECIMAL(3,2),
    history_score DECIMAL(3,2),
    relationship_score DECIMAL(3,2),
    -- Vector embedding untuk semantic search[reference:16]
    embedding VECTOR(1536), -- OpenAI embedding dimension
    -- Tracking
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    source VARCHAR(50), -- 'newsapi', 'googlenews', 'manual'
    created_by UUID REFERENCES auth.users(id) -- RLS
);

-- Enable Row Level Security[reference:17]
ALTER TABLE journalists ENABLE ROW LEVEL SECURITY;

-- Tabel Campaigns
CREATE TABLE campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    story TEXT,
    target_beat TEXT[],
    status VARCHAR(50), -- 'draft', 'scheduled', 'sending', 'completed'
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id)
);

-- Tabel Outreach (Email tracking)
CREATE TABLE outreach (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID REFERENCES campaigns(id) ON DELETE CASCADE,
    journalist_id UUID REFERENCES journalists(id) ON DELETE CASCADE,
    pitch_email TEXT,
    subject_line VARCHAR(500),
    sent_at TIMESTAMP,
    opened_at TIMESTAMP,
    replied_at TIMESTAMP,
    status VARCHAR(50), -- 'pending', 'sent', 'opened', 'replied', 'bounced'
    follow_up_sequence INTEGER DEFAULT 1,
    next_follow_up TIMESTAMP,
    gmail_message_id VARCHAR(255), -- untuk tracking via Gmail API
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tabel untuk Gmail OAuth tokens
CREATE TABLE gmail_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) UNIQUE,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMP,
    email_address VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tabel untuk AI prompt templates
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    model VARCHAR(50), -- 'gpt-4o', 'deepseek-chat'
    template_text TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index untuk performa
CREATE INDEX idx_journalists_beat ON journalists USING GIN (beat);
CREATE INDEX idx_journalists_outlet ON journalists(outlet);
CREATE INDEX idx_outreach_campaign ON outreach(campaign_id);
CREATE INDEX idx_outreach_status ON outreach(status);
CREATE INDEX idx_outreach_next_followup ON outreach(next_follow_up) WHERE status NOT IN ('replied', 'bounced');

-- Trigger untuk auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_journalists_updated_at
BEFORE UPDATE ON journalists
FOR EACH ROW EXECUTE FUNCTION update_updated_at();
3.2.4. RLS (Row Level Security) Policies
sql
-- Contoh: User hanya bisa melihat jurnalis yang dia buat
CREATE POLICY "Users can view their own journalists"
ON journalists FOR SELECT
USING (auth.uid() = created_by);

CREATE POLICY "Users can insert their own journalists"
ON journalists FOR INSERT
WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Users can update their own journalists"
ON journalists FOR UPDATE
USING (auth.uid() = created_by);
3.3. Authentication dengan Supabase Auth
Supabase Auth menyediakan autentikasi lengkap untuk dashboard web:

python
from supabase import create_client

# Login dengan email/password
def login_user(email: str, password: str):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    return response

# Magic link (passwordless)
def send_magic_link(email: str):
    supabase.auth.sign_in_with_otp({
        "email": email
    })

# Google OAuth
def sign_in_with_google():
    supabase.auth.sign_in_with_oauth({
        "provider": "google"
    })
Integrasi dengan FastAPI:

python
from fastapi import FastAPI, Depends, HTTPException
from supabase import create_client

app = FastAPI()

async def get_current_user(token: str):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    try:
        user = supabase.auth.get_user(token)
        return user
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/protected")
async def protected_route(user = Depends(get_current_user)):
    return {"user": user}
3.4. Email Sending Engine (Gmail API OAuth2)
Supabase digunakan untuk menyimpan Gmail OAuth tokens dengan aman:

python
from supabase import create_client

class GmailTokenStorage:
    def __init__(self, supabase: Client, user_id: str):
        self.supabase = supabase
        self.user_id = user_id
    
    async def get_token(self):
        response = await self.supabase.table("gmail_tokens")\
            .select("*")\
            .eq("user_id", self.user_id)\
            .execute()
        return response.data[0] if response.data else None
    
    async def save_token(self, token_data: dict):
        await self.supabase.table("gmail_tokens")\
            .upsert({
                "user_id": self.user_id,
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "token_expiry": token_data["expiry"],
                "email_address": token_data["email"]
            })\
            .execute()
3.5. AI Multi-Model dengan Vector Search (pgvector)
Supabase + pgvector memungkinkan semantic search untuk mencocokkan jurnalis dengan topik pitch:

python
import openai
from supabase import create_client

async def find_matching_journalists(story: str, limit: int = 10):
    # Generate embedding untuk story
    embedding = openai.Embedding.create(
        model="text-embedding-3-small",
        input=story
    )["data"][0]["embedding"]
    
    # Cari jurnalis dengan embedding terdekat
    response = await supabase.rpc(
        "match_journalists",
        {
            "query_embedding": embedding,
            "match_threshold": 0.7,
            "match_count": limit
        }
    ).execute()
    
    return response.data

# Function di Supabase (SQL)
-- CREATE OR REPLACE FUNCTION match_journalists(
--     query_embedding VECTOR(1536),
--     match_threshold FLOAT,
--     match_count INT
-- )
-- RETURNS TABLE(
--     id UUID,
--     name VARCHAR,
--     email VARCHAR,
--     outlet VARCHAR,
--     similarity FLOAT
-- )
-- LANGUAGE plpgsql
-- AS $$
-- BEGIN
--     RETURN QUERY
--     SELECT 
--         j.id,
--         j.name,
--         j.email,
--         j.outlet,
--         1 - (j.embedding <=> query_embedding) AS similarity
--     FROM journalists j
--     WHERE 1 - (j.embedding <=> query_embedding) > match_threshold
--     ORDER BY similarity DESC
--     LIMIT match_count;
-- END;
-- $$;
3.6. Realtime Tracking dengan Supabase Realtime
Supabase Realtime memungkinkan update status email secara live di dashboard:

python
# Subscribe ke perubahan di tabel outreach
from supabase import create_async_client

async def subscribe_to_email_updates():
    supabase = await create_async_client(SUPABASE_URL, SUPABASE_KEY)
    await supabase.realtime.connect()
    
    channel = supabase.channel("outreach-updates")
    
    channel.on_postgres_changes(
        event="UPDATE",
        schema="public",
        table="outreach",
        callback=lambda payload: handle_email_update(payload)
    )
    
    await channel.subscribe()

def handle_email_update(payload):
    # Update dashboard secara realtime
    print(f"Email {payload['new']['id']} status: {payload['new']['status']}")
3.7. Storage untuk Email Attachments & Templates
Supabase Storage untuk menyimpan:

Template email (HTML)

Lampiran (infografis, dataset)

Logo dan aset campaign

python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Upload template
async def upload_template(file_content: bytes, filename: str):
    response = await supabase.storage\
        .from_("email_templates")\
        .upload(f"templates/{filename}", file_content)
    return response

# Download attachment untuk email
async def get_attachment(path: str):
    response = await supabase.storage\
        .from_("attachments")\
        .download(path)
    return response
3.8. Edge Functions untuk Email Webhooks
Supabase Edge Functions untuk menangani email tracking webhooks:

typescript
// supabase/functions/track-email/index.ts
import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from "https://esm.sh/@supabase/supabase-js@2"

serve(async (req) => {
  const { email_id, event_type } = await req.json()
  
  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!
  )
  
  // Update status email
  if (event_type === "open") {
    await supabase
      .from("outreach")
      .update({ opened_at: new Date().toISOString(), status: "opened" })
      .eq("id", email_id)
  } else if (event_type === "reply") {
    await supabase
      .from("outreach")
      .update({ replied_at: new Date().toISOString(), status: "replied" })
      .eq("id", email_id)
  }
  
  return new Response(JSON.stringify({ success: true }))
})
4. Arsitektur Sistem Keseluruhan (dengan Supabase)
text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          WEB DASHBOARD (Streamlit/Next.js)                  │
│   Overview | Media DB | Campaigns | Tracking | AI Settings | Analytics      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │ API (FastAPI)
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                              BACKEND CORE                                   │
├───────────────────┬───────────────────┬───────────────────┬─────────────────┤
│  OpenClaw PR      │  Scraping         │  AI Pitch         │  Email Sender   │
│  Manager          │  Engine           │  Engine           │  (Gmail API)    │
│  - Media Match    │  - The News API   │  - GPT-4o         │  - OAuth2       │
│  - 4D Scoring     │  - NewsAPI.org    │  - DeepSeek       │  - Send/Receive  │
│  - Calendar       │  - Google News    │  - OpenRouter     │  - Tracking     │
│                   │  - OpenClaw Skill │  - pgvector       │  - Labeling     │
└───────────────────┴───────────────────┴───────────────────┴─────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                          SUPABASE (Backend-as-a-Service)                    │
├───────────────────┬───────────────────┬───────────────────┬─────────────────┤
│  PostgreSQL       │  Auth             │  Storage          │  Realtime       │
│  - Journalists    │  - Email/Password │  - Templates      │  - Live Updates │
│  - Campaigns      │  - Google OAuth   │  - Attachments    │  - Notifications│
│  - Outreach       │  - Magic Links    │  - Assets         │  - Webhooks     │
│  - Gmail Tokens   │  - RLS            │                   │                 │
│  - pgvector       │                   │                   │                 │
└───────────────────┴───────────────────┴───────────────────┴─────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                        TASK QUEUE (Redis + Celery)                         │
│              Scraping Jobs | Email Sending | Follow-up Scheduler            │
└─────────────────────────────────────────────────────────────────────────────┘
5. Tech Stack Final
Layer	Pilihan	Alasan
Backend	FastAPI (Python)	Cepat, async, mudah integrasi dengan OpenClaw & Supabase
Database	Supabase (PostgreSQL)	BaaS: database + auth + storage + realtime + pgvector
Auth	Supabase Auth	Built-in, support Google OAuth, magic links
Storage	Supabase Storage	Untuk template, attachments, assets
Realtime	Supabase Realtime	Live tracking email status
Vector Search	Supabase + pgvector	Semantic search untuk journalist matching
Frontend	Streamlit (MVP) / Next.js (production)	Streamlit cepat, Next.js untuk skalabilitas
Task Queue	Redis + Celery	Background tasks (scraping, email sending)
Hosting	VPS (2 vCPU, 4GB RAM) atau Supabase + Vercel	Hybrid: Supabase untuk backend, VPS untuk worker
6. Keuntungan Menggunakan Supabase
Keuntungan	Penjelasan
No infrastructure management	Tidak perlu setup PostgreSQL sendiri, semua managed
Auth siap pakai	Tidak perlu build sistem login dari nol
Realtime out-of-the-box	Dashboard update live tanpa polling
RLS untuk keamanan	Data per user/organisasi terisolasi
pgvector untuk AI	Semantic search untuk mencocokkan jurnalis dengan story
Free tier	Cukup untuk MVP dan testing
Integrasi dengan OpenClaw	Plugin dan ekosistem yang mendukung
7. Prioritas Pengembangan (Roadmap) - Update
Phase 1 - Foundation (Week 1-2)
□ Setup Supabase project (database, auth, storage)
□ Setup schema database di Supabase SQL Editor
□ Setup RLS policies
□ Setup FastAPI + Supabase Python client
□ Install dan test OpenClaw PR Manager
□ Implement Gmail API OAuth2 + token storage di Supabase
□ Dashboard basic (Streamlit) dengan Supabase Auth
Phase 2 - Scraping Engine (Week 3-4)
□ Integrasi The News API + NewsAPI.org
□ Simpan hasil scraping ke Supabase
□ Implement email extractor + validator
□ Scheduler untuk scraping rutin (Celery + Supabase)
□ Test OpenClaw skill untuk Google News scraping
Phase 3 - AI Integration (Week 5-6)
□ Integrasi OpenAI GPT + DeepSeek API
□ Setup pgvector di Supabase
□ Implement semantic search untuk journalist matching
□ Prompt engineering untuk pitch email (dengan feedback klien)
□ Simpan prompt templates di Supabase
Phase 4 - Campaign & Follow-up (Week 7-8)
□ Campaign management (CRUD di Supabase)
□ Implement follow-up formula 3+7+7+14
□ Auto-schedule follow-up (Celery + Supabase)
□ Email tracking via Gmail API + update ke Supabase
□ Supabase Realtime untuk live dashboard update
Phase 5 - Dashboard & Analytics (Week 9-10)
□ Dashboard overview dengan data dari Supabase
□ Campaign performance tracking
□ Response rate analytics per outlet/beat
□ AI settings (model selection, prompt templates)
□ Export reports
Phase 6 - Production (Week 11-12)
□ Setup Supabase Edge Functions untuk email webhooks
□ Deploy ke VPS + Supabase production
□ Monitoring & logging
□ Documentation
8. Integrasi OpenClaw + Supabase
OpenClaw memiliki ekosistem plugin untuk Supabase:

bash
# Install OpenClaw Supabase plugin
npm install @prbelief/supabase-db-admin

# Atau melalui Composio[reference:50]
# Connect OpenClaw to Supabase MCP
Cara kerja integrasi:

OpenClaw PR Manager berjalan sebagai Python library di backend

Data jurnalis disimpan di Supabase PostgreSQL

OpenClaw membaca data dari Supabase untuk melakukan 4D scoring

Hasil scoring disimpan kembali ke Supabase

Dashboard membaca data dari Supabase untuk visualisasi

9. Pertanyaan untuk Diskusi dengan GPT (Tambahan)
Supabase vs Self-hosted PostgreSQL: Apakah Supabase free tier cukup untuk 1.000 email/bulan? Kapan harus upgrade ke Pro?

Supabase Realtime: Bagaimana best practice untuk realtime tracking email? Apakah pakai Realtime atau polling?

pgvector: Apakah kita perlu generate embedding untuk setiap jurnalis? Bagaimana strategi update embedding ketika data berubah?

Supabase Edge Functions: Apakah Edge Functions bisa digunakan untuk menangani email webhook dari Gmail? Atau lebih baik pakai Celery?

RLS Policies: Bagaimana desain RLS yang tepat untuk multi-user (tim PR dengan multiple klien)?

Supabase Storage: Apakah storage bisa digunakan untuk menyimpan template email dalam format HTML dengan variables?

10. Referensi & Inspirasi
Sumber	Fungsi
OpenClaw PR Manager	Mesin utama (media matching, scoring)
Supabase	Database + Auth + Storage + Realtime + pgvector
The News API	Sumber data jurnalis & outlet
NewsAPI.org	Sumber data jurnalis & outlet
Gmail API (OAuth2)	Email sending & tracking
OpenAI GPT	AI pitch generation + embeddings
DeepSeek API	AI pitch generation (bulk)
FastAPI	Backend REST API
Streamlit / Next.js	Web dashboard
Catatan: Dokumen ini adalah bahan brainstorming untuk diskusi dengan GPT. Supabase dipilih sebagai solusi backend yang all-in-one untuk mempercepat development dan mengurangi operational overhead. 🚀
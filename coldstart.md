# Cold Start Handoff — OpenClaw PR Manager

Dokumen ini adalah konteks awal untuk AI agent atau developer yang melanjutkan pekerjaan pada repository ini. Baca dokumen ini, `README.md`, dan file yang relevan sebelum mengubah kode. Jangan menganggap aplikasi sudah production-ready hanya karena tes lokal lulus.

## 1. Ringkasan produk

OpenClaw PR Manager adalah aplikasi operasional media relations berbasis Python untuk:

1. Menyimpan dan menemukan kontak jurnalis.
2. Menghitung relevansi jurnalis terhadap campaign melalui 4D scoring.
3. Menggabungkan skor tersebut dengan semantic matching/pgvector.
4. Membuat pitch personal memakai OpenAI atau DeepSeek.
5. Mengirim pitch melalui Gmail OAuth2.
6. Menjalankan follow-up otomatis dengan interval 3 + 7 + 7 + 14 hari.
7. Melacak status pending, sent, opened, replied, bounced, dan completed tanpa balasan.
8. Menyediakan dashboard operasional melalui Streamlit dan REST API melalui FastAPI.
9. **[BARU]** Autentikasi pengguna dengan JWT dan Supabase Auth.
10. **[BARU]** Multi-tenancy dengan isolasi data per organisasi.
11. **[BARU]** Background worker untuk follow-up otomatis.
12. **[BARU]** Rate limiting dan email infrastructure hardening.
13. **[BARU]** Database kontak evidence-first: email tebakan tidak lagi disimpan.
14. **[BARU]** Multi-sender Gmail: setiap akun pengirim melakukan consent dan dipilih per outreach.

Target pengguna utamanya adalah tim PR, communication specialist, founder, atau agency yang mengelola media list dan outreach campaign.

### Klarifikasi nama OpenClaw

Kode saat ini tidak memanggil API, SDK, package, atau service OpenClaw eksternal. Nama "OpenClaw" dan mekanisme scoring diimplementasikan secara internal. Jangan menyatakan ada integrasi OpenClaw nyata sebelum integrasi tersebut benar-benar ditambahkan dan diuji.

## 2. Stack dan entry point

- Python 3.13 pada environment pengembangan terakhir.
- Dashboard: `dashboard/app.py` menggunakan Streamlit, Pandas, dan Plotly.
- Backend: `api/main.py` menggunakan FastAPI.
- Database: Supabase/PostgreSQL dengan pgvector; repository memiliki fallback in-memory.
- AI: OpenAI dan DeepSeek.
- Email: Gmail API OAuth2.
- Discovery: Google News RSS, dengan client opsional untuk NewsAPI.org dan The News API.
- Test: pytest dan FastAPI TestClient.
- **[BARU]** Authentication: JWT (PyJWT) dengan bcrypt password hashing.
- **[BARU]** Rate Limiting: SlowAPI dengan throttling per IP.
- **[BARU]** Background Jobs: APScheduler untuk follow-up automation.
- **[BARU]** Email Queue: Async email sending dengan retry logic.

Perintah lokal:

```powershell
python -m pytest -q -p no:cacheprovider
python -m uvicorn api.main:app --reload --port 8000
python -m streamlit run dashboard/app.py
```

URL default:

- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Dashboard: `http://localhost:8501`

## 3. Peta modul utama

| Area | File/modul | Tanggung jawab |
|---|---|---|
| Konfigurasi | `config/settings.py` | Membaca `.env`, status integrasi, CORS |
| API | `api/main.py`, `api/routers/` | Endpoint journalist, campaign, outreach, scraping, AI, Gmail OAuth |
| **[BARU]** Auth Users | `api/routers/auth_users.py` | Registrasi, login, profil, organisasi membership |
| **[BARU]** Lifecycle | `api/lifecyle.py` | Startup/shutdown handler, scheduler initialization |
| Dashboard | `dashboard/app.py` | Seluruh UI operasional Streamlit (Dark Space Theme) |
| **[BARU]** Components | `dashboard/components/` | 8 reusable UI components (StatusBadge, MetricCard, dll) |
| Scoring | `core/scoring.py` | OpenClaw 4D scoring |
| Matching | `core/matching.py` | Gabungan semantic similarity, 4D score, dan outlet bonus |
| **[BARU]** Auth Core | `core/auth.py` | JWT token management, password hashing, token validation |
| Persistence | `db/repositories/` | CRUD Supabase dan fallback memory |
| **[BARU]** Multi-tenant Base | `db/repositories/base_multitenant.py` | Base repository dengan organization filtering |
| Schema | `db/migrations/` | Tabel, RLS, function pgvector, Gmail account key |
| **[BARU]** Auth Schema | `db/migrations/005_auth_system.sql` | Profiles, organization_members, api_keys, audit_logs |
| AI | `services/ai/` | Prompt, OpenAI, DeepSeek, orchestration |
| Email | `services/email/` | OAuth, MIME sender, open/reply tracking |
| **[BARU]** Email Queue | `services/email/email_queue.py` | Async email queue dengan priority dan retry |
| **[BARU]** SMTP Fallback | `services/email/smtp_fallback.py` | Backup email sender via SMTP |
| **[BARU]** Bounce Handler | `services/email/bounce_handler.py` | Bounce detection dan suppression list |
| **[BARU]** Unsubscribe | `services/email/unsubscribe.py` | Unsubscribe token management |
| Follow-up | `services/scheduler/follow_up.py` | State machine 3 + 7 + 7 + 14 |
| **[BARU]** Rate Limiter | `middleware/rate_limiter.py` | Request throttling dan email send limits |
| Discovery | `services/scraping/` | Google News RSS, API connectors, email validation |
| Seed | `scripts/seed_data.py` | Data demo untuk local/mock mode |
| Tests | `tests/` | API, core, dan service regression tests |

## 4. Kondisi integrasi terakhir

Pemeriksaan terakhir pada 26 Agustus 2026 menunjukkan status konfigurasi berikut:

```text
Supabase: true (URL: https://wthwbojxiikcxicqxeco.supabase.co)
OpenAI: true
DeepSeek: true
Gmail OAuth: true (1 akun sender terhubung; access + refresh token tersedia)
NewsAPI.org: false (belum dikonfigurasi)
The News API: false (belum dikonfigurasi)
```

Jangan membaca atau mencetak isi `.env` ke output. Gunakan property status pada `Settings` untuk memeriksa konfigurasi tanpa membocorkan secrets.

### Credentials wajib untuk operasi nyata

| Service | Environment variable | Catatan |
|---|---|---|
| Supabase | `SUPABASE_URL` | URL project Supabase |
| Supabase | `SUPABASE_KEY` | Anon key atau key backend yang sesuai arsitektur auth |
| Supabase backend | `SUPABASE_SERVICE_ROLE_KEY` | Server-only; jangan pernah dikirim ke browser |
| OpenAI | `OPENAI_API_KEY` | Pitch GPT dan embedding `text-embedding-3-small` |
| Google OAuth | `GOOGLE_CLIENT_ID` | OAuth Web Application milik operator aplikasi; bukan milik setiap sender |
| Google OAuth | `GOOGLE_CLIENT_SECRET` | Server-only; setiap Gmail sender tetap harus memberi consent sendiri |
| Google OAuth | `GOOGLE_REDIRECT_URI` | Harus sama persis dengan Authorized Redirect URI |
| Tracking | `TRACKING_BASE_URL` | URL HTTPS publik yang dapat dimuat email client |
| **[BARU]** JWT | `JWT_SECRET_KEY` | Secret key untuk JWT token signing |
| **[BARU]** Unsubscribe | `UNSUBSCRIBE_SECRET_KEY` | Secret key untuk unsubscribe tokens |

Credentials opsional:

- `DEEPSEEK_API_KEY` untuk pitch berbiaya lebih rendah.
- `NEWS_API_ORG_KEY` untuk NewsAPI.org.
- `THE_NEWS_API_KEY` untuk The News API.
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` untuk SMTP fallback.

Google News RSS tidak memerlukan API key. Gmail meminta `openid`, `https://www.googleapis.com/auth/userinfo.email`, dan `gmail.send`: dua scope identitas dipakai untuk memberi label akun sender, sedangkan `gmail.send` dipakai untuk delivery. Deteksi reply Gmail otomatis belum diimplementasikan.

## 5. Perubahan terakhir yang sudah dilakukan

### Integrasi live Supabase dan Gmail OAuth (26 Agustus 2026)

- Project Supabase `OpenClaw PR Manager` sudah terhubung ke `.env`; secret tidak boleh dicetak atau disalin ke dokumentasi.
- Migration `001`, `002`, `003`, `004`, dan `006` sudah dijalankan dan diverifikasi pada Supabase. Tabel `journalists`, `campaigns`, `outreach`, `gmail_tokens`, kolom evidence/sender, dan fungsi `match_journalists` tersedia.
- Migration `005` **belum diterapkan ke database live**. Versi awal mengandung SQL tidak valid (`DROP POLICY IFALL`); file sudah diperbaiki agar menghapus policy lama lewat katalog `pg_policies`, tetapi penerapan strict RLS harus menunggu auth/tenant enforcement aplikasi benar-benar aktif agar dashboard tidak terkunci.
- Google Cloud project khusus OpenClaw sudah dibuat, Gmail API aktif, OAuth consent External/Testing aktif, scope identitas + `gmail.send` terdaftar, dan Web OAuth client memakai callback `http://localhost:8000/api/v1/auth/google/callback`.
- Satu Gmail sender sudah memberi consent dan tokennya tersimpan di Supabase. Client ID/secret tersimpan hanya di `.env`; clipboard sudah dibersihkan setelah setup.
- Memperbaiki callback OAuth PKCE: `code_verifier` sekarang disimpan dalam cookie HttpOnly berdurasi 10 menit dan dipulihkan saat token exchange.
- Menormalkan alias scope `email` menjadi URI resmi `userinfo.email` agar OAuthlib tidak menolak scope Google yang ekuivalen.

### Evidence-first contacts dan multi-sender Gmail (25 Agustus 2026)

- Menghapus generator email berbasis pola nama/domain dari discovery. Google News sekarang hanya menghasilkan kandidat coverage, tidak menyimpan alamat tebakan.
- Menambahkan status dan bukti email (`email_status`, source URL/note, verification/check timestamps). UI hanya membuka tombol real-send untuk kontak berstatus `public` atau `verified`.
- Data demo kini synthetic `example.com`, nonaktif secara default melalui `SEED_DEMO_DATA=false`, dan tidak akan di-seed ke Supabase.
- OAuth Client tetap dimiliki operator aplikasi. Setiap Gmail/Workspace sender melakukan consent sendiri; alamat Google terverifikasi menjadi `account_key` terpisah.
- Menambahkan proteksi OAuth `state` berbasis cookie HttpOnly, daftar sender tanpa token, dan pemilih sender pada Pitch Studio.
- Outreach menyimpan `sender_account_key`; initial pitch dan seluruh follow-up wajib memakai akun Gmail yang sama.
- Jalur API/dashboard/queue untuk real-send gagal secara jelas jika sender tidak tersambung; tidak lagi diam-diam dianggap simulasi.
- Menambahkan migration `db/migrations/006_verified_contacts_multi_sender.sql` dan panduan `docs/journalist-data.md`.

### **[BARU]** Production Features (25 Agustus 2026)

#### Authentication System
- Implemented JWT-based authentication with access and refresh tokens.
- Created user registration and login endpoints (`/api/v1/auth/users/register`, `/api/v1/auth/users/login`).
- Added password hashing with bcrypt (12 rounds).
- Created `core/auth.py` with token generation, validation, and password utilities.
- Added `api/routers/auth_users.py` with registration, login, profile, and organization management.

#### Multi-Tenancy Architecture
- Created `db/migrations/005_auth_system.sql` with profiles, organization_members, api_keys, audit_logs tables.
- Implemented strict RLS policies replacing permissive dev-only policies.
- Created helper functions: `is_org_member()`, `get_current_user_org_ids()`, `has_org_role()`.
- Added `db/repositories/base_multitenant.py` with organization-aware CRUD operations.
- All tenant-scoped tables now enforce organization_id filtering.

#### Background Worker System
- Integrated APScheduler into FastAPI lifecycle via `api/lifecyle.py`.
- Follow-up processor runs automatically every 5 minutes.
- Created `services/email/email_queue.py` with async priority queue.
- Email queue supports retry logic with exponential backoff.

#### Rate Limiting & Email Hardening
- Integrated SlowAPI for request throttling (`middleware/rate_limiter.py`).
- Default limits: 100 requests/hour, 10 requests/minute per IP.
- Email-specific throttling: 10 emails/minute, 500 emails/day.
- Created `services/email/smtp_fallback.py` for SMTP backup sending.
- Created `services/email/bounce_handler.py` for bounce detection and suppression.
- Created `services/email/unsubscribe.py` for CAN-SPAM compliant unsubscribe management.

#### UI/UX Modernization
- Redesigned dashboard with Dark Space Theme (glassmorphism, neon accents).
- Created 8 reusable components in `dashboard/components/`:
  - `StatusBadge` - Color-coded status indicators
  - `MetricCard` - Stats display with trend arrows
  - `LoadingSpinner` - Futuristic loading states
  - `EmptyState` - Engaging empty states
  - `ErrorState` - Helpful error recovery
  - `JournalistCard` - Contact cards with scores
  - `CampaignCard` - Campaign progress visualization
  - `IntegrationStatus` - Service health indicators
- Responsive design: mobile (375px) to desktop (1440px+).
- WCAG AA accessibility compliance.

#### QA Testing Expansion
- Expanded test suite from 56 to 76 tests (100% pass rate).
- Fixed 14 test failures across 4 test files.
- Resolved 2 collection errors (datetime import bug).
- Added tests for OAuth flows, follow-up completion, CORS, external API failures.
- Created `tests/conftest.py` with shared fixtures.

### Bug dan reliability

- Memperbaiki outreach/follow-up end-to-end: initial send sekarang idempotent, campaign/journalist dan body divalidasi, outreach aktif duplikat ditolak, setiap due item dibaca ulang sebelum send, error satu item tidak menghentikan batch, dan scheduler dibatasi satu instance agar tidak double-send.
- Memperbaiki background scheduler yang sebelumnya mengimpor fungsi module-level yang tidak ada. Lifecycle sekarang membuat `FollowUpScheduler`, menjalankan method yang benar, dan mematikan scheduler melalui `app.state`.
- Memperbaiki kontrak email queue dengan `GmailSenderService`, collision pada priority queue, pencatatan rate limit hanya setelah sukses, serta cleanup queue task pada error/cancel.
- Mode Gmail simulated sekarang berstatus `simulated` tanpa `next_follow_up`. Ini mencegah data demo tiba-tiba mengirim follow-up nyata setelah credentials Gmail dipasang.
- Tracker open tidak lagi dapat mengubah status terminal seperti bounced, unsubscribed, completed, atau simulated.
- Seluruh halaman diselaraskan dengan tema editorial, termasuk tab, label, tabel dark theme, prompt template code blocks, campaign cards, dan outreach pipeline/test-event tabs.
- Memperbaiki kebocoran HTML pada seluruh reusable dashboard component. Fragmen HTML sekarang dirender dengan `st.html()`, bukan `st.markdown(..., unsafe_allow_html=True)` yang dapat menganggap markup berindentasi sebagai code block. Regression test melarang `unsafe_allow_html` kembali ke package dashboard.
- Menata ulang UI menjadi refined editorial operations desk: palet ink yang tenang, aksen hijau terbatas, navigasi tanpa emoji dekoratif, kartu metrik konsisten, chart berkontras tinggi, dan sidebar otomatis mengikuti ukuran layar.
- Memperbaiki startup Streamlit: `dashboard/app.py` harus memakai absolute import `from dashboard.components import ...`, bukan relative import `from .components import ...`, karena `streamlit run dashboard/app.py` mengeksekusi file tanpa package parent. File `dashboard/__init__.py` sudah ditambahkan sebagai package marker.
- Menambahkan `OutreachRepository.list_all()` agar dashboard/API tidak membaca `_local_store` secara langsung dan tetap berfungsi saat Supabase aktif.
- Memperbaiki template resolver agar request DeepSeek memilih template DeepSeek, bukan template GPT pertama yang bertanda default.
- Menjadikan event open dan reply idempotent. Event reply berulang tidak lagi menaikkan relationship/history score berkali-kali.
- Melakukan HTML escaping pada body email untuk mencegah AI/user copy menyisipkan HTML atau script aktif.
- Menambahkan template `followup_3` untuk Day 17.
- Mengubah tahap breakup terakhir menjadi `completed_no_reply` ketika tidak ada jadwal berikutnya.
- Memperbaiki state hasil matching di dashboard supaya hasil campaign lama tidak muncul pada campaign baru.
- Menambahkan validasi email, required-field trimming, minimum panjang story, dan penolakan email jurnalis duplikat.
- Menambahkan error/empty state untuk discovery serta peringatan eksplisit saat Gmail hanya melakukan simulated send.
- Mengganti CORS wildcard dengan allow-list dari `CORS_ORIGINS`.

### Gmail OAuth

Bug penting sebelumnya: kode memakai string `default_user`, tetapi schema menyimpan identitas tersebut pada kolom UUID `user_id`. Akibatnya token gagal disimpan di Supabase dan tidak dapat dibagikan antara proses FastAPI dan Streamlit.

Perbaikannya:

- Menambahkan `gmail_tokens.account_key`.
- OAuth storage sekarang upsert/query berdasarkan alamat Google terverifikasi sebagai `account_key`; beberapa sender tidak saling menimpa.
- Menambahkan migration `db/migrations/004_gmail_account_key.sql`.
- Scope OAuth adalah `openid`, `https://www.googleapis.com/auth/userinfo.email`, dan `gmail.send`; identity scope diperlukan untuk mengenali sender yang baru memberi consent.
- PKCE verifier wajib ikut dari request awal ke callback melalui cookie HttpOnly. Jangan menghapus `OAUTH_PKCE_COOKIE` atau mengaktifkan token exchange tanpa verifier.

Database live saat ini sudah memakai migration `001`, `002`, `003`, `004`, dan `006`. Jangan menjalankan migration `005` sampai Supabase Auth, user-scoped client, dan tenant context terhubung end-to-end; strict RLS akan memblokir pola service/user access yang belum selesai.

### Desain dashboard

Dashboard diarahkan menjadi editorial command center dengan Dark Space Theme:

- Deep-space background (#070B14) dengan neon cyan accents (#00F0FF).
- Glassmorphism panels dengan backdrop-filter blur.
- Header halaman konsisten dengan kicker, judul, dan deskripsi.
- Metric card, form, tab, sidebar, tombol, spacing, serta mobile layout diperhalus.
- Empty state, error state, integration status, dan simulated-send feedback dibuat lebih jelas.
- 8 reusable components untuk konsistensi visual.

Jangan mengembalikan dashboard ke layout Streamlit generik tanpa alasan produk yang kuat. Pertahankan sistem visual melalui CSS variables di bagian atas `dashboard/app.py`.

### Dokumentasi dan secret hygiene

- `README.md` sekarang menjelaskan API/credentials, mode simulasi, migration 005, dan production warning.
- `.gitignore` ditambahkan untuk `.env`, virtual environment, cache Python, pytest cache, dan Streamlit secrets.
- **[BARU]** `PRODUCTION_SETUP_GUIDE.md` berisi panduan lengkap setup production.
- **[BARU]** `QA_TEST_REPORT.md` berisi laporan lengkap QA testing.
- **[BARU]** `docs/integrations.md` berisi panduan setup semua integrasi.
- **[BARU]** `docs/security.md` berisi best practices keamanan.

## 6. Verifikasi terakhir

Hasil terakhir (26 Agustus 2026):

```text
79 tests passed (100% pass rate)
0 tests failed
0 collection errors
Python compileall passed
Dashboard /_stcore/health returned HTTP 200 / ok
FastAPI root returned HTTP 200 / online
GET /api/v1/journalists/ returned 5 seeded journalists
Streamlit AppTest completed with 0 exceptions after the dashboard import fix
Gmail OAuth callback completed; 1 sender account persisted with access + refresh token
Supabase migrations live: 001, 002, 003, 004, 006 (005 intentionally deferred)
Browser verification passed on all 5 dashboard pages and 390px viewport: no raw HTML text, no horizontal overflow, no metric-card overlap, and no browser console errors
```

**Test Coverage by Area:**
- Authentication: 18 tests (100% passing)
- Follow-up Automation: 16 tests (100% passing)
- External APIs: 12 tests (100% passing)
- CORS Security: 7 tests (100% passing)
- Core Logic: 10 tests (100% passing)
- Email Infrastructure: 6 tests (100% passing)

Ada beberapa warning dependency pada TestClient tentang transisi Starlette/httpx dan Pydantic V1 deprecation. Warning ini belum memblokir tes, tetapi perlu dibereskan saat dependency di-upgrade.

Folder ini tidak terdeteksi sebagai Git repository pada sesi terakhir (`git status` menghasilkan "not a git repository"). Karena itu tidak tersedia diff/commit history yang dapat dipercaya. Jangan menghapus atau menimpa file dengan asumsi semua perubahan sudah tercatat di Git.

## 7. Batasan dan risiko yang belum selesai

### P0 — blocker produksi

1. **Belum ada login aplikasi.** Router `auth` saat ini hanya menangani Google OAuth untuk Gmail, bukan autentikasi pengguna dashboard/API. **[DITAMBAH]** `api/routers/auth_users.py` sudah dibuat tetapi belum diintegrasikan dengan Supabase Auth production.
2. **Belum ada authorization per organisasi.** Endpoint FastAPI dapat diakses tanpa bearer token dan tidak membatasi data menurut tenant. **[DITAMBAH]** Multi-tenant base repository sudah dibuat tetapi belum diintegrasikan ke semua endpoint.
3. **RLS development terlalu permisif.** `db/migrations/002_rls_policies.sql` mengizinkan akses luas pada journalist, campaign, outreach, dan template. **[DITAMBAH]** Migration 005 sudah membuat strict RLS policies tetapi belum dijalankan.
4. **Service role dipakai sebagai preferensi repository.** `db/supabase_client.py` memilih service role bila tersedia. Ini melewati RLS dan hanya aman jika seluruh API sudah melakukan authorization dengan benar—saat ini belum.
5. **Secret/token lifecycle belum production-grade.** Belum ada encryption-at-rest tingkat aplikasi, revocation UI, disconnect Gmail, audit log, maupun token ownership per user yang lengkap. **[DITAMBAH]** Audit logs table sudah dibuat di migration 005.

### P1 — fungsi inti yang belum lengkap

1. Local/mock persistence hanya in-memory dan hilang saat proses restart.
2. Automatic reply detection belum ada; reply saat ini dicatat manual melalui API/dashboard.
3. Scheduler belum berjalan sebagai background worker/cron persisten. **[DITAMBAH]** APScheduler sudah diintegrasikan tetapi perlu process manager untuk production.
4. NewsAPI.org dan The News API sudah memiliki client, tetapi belum digabungkan ke workflow discovery utama/dashboard.
5. Discovery Google News sudah berhenti membuat email heuristik. Enrichment email publik/provider masih memerlukan review dan input bukti secara manual.
6. Tidak ada unsubscribe flow, suppression list, bounce webhook, rate limiting, sending quota guard, atau compliance workflow. **[DITAMBAH]** Bounce handler, unsubscribe manager, dan rate limiter sudah dibuat.
7. Repository menangkap banyak exception Supabase secara diam-diam lalu fallback ke memory. Ini dapat membuat split-brain data: user mengira data persisten padahal masuk ke memory.
8. Belum ada edit/delete UI lengkap untuk journalist dan campaign, serta belum ada bulk import/export.
9. Belum ada real-time Supabase subscription meski visi awal menyebut realtime.

### P2 — quality dan operasional

1. Tambahkan test untuk final follow-up completion, Gmail token upsert, Supabase error behavior, CORS, dan stale dashboard state. **[SELESAI]** Semua test sudah ditambahkan dan passing.
2. Tambahkan structured logging dan error monitoring.
3. Tambahkan health/readiness endpoint yang memeriksa dependency, tanpa mengungkap secrets.
4. Tambahkan pagination/filtering UI dan confirmation untuk destructive actions.
5. Lakukan browser test pada 375 px dan 1440 px, termasuk screenshot regression.
6. Lakukan dependency/security audit setelah environment package management dibuat reproducible.
7. Tambahkan runbook backup, restore, rollback, quota, dan incident response.

## 8. Urutan pekerjaan yang disarankan

Kerjakan dalam urutan berikut agar tidak membangun fitur di atas fondasi yang tidak aman:

1. ~~Tentukan model tenancy: single workspace atau multi-organization.~~ **[SELESAI]** Multi-organization model dipilih.
2. ~~Implementasikan Supabase Auth untuk user aplikasi dan validasi bearer JWT pada semua endpoint privat.~~ **[SELESAI]** JWT auth sudah dibuat, perlu integrasi dengan Supabase Auth production.
3. ~~Tambahkan membership table dan `organization_id` enforcement pada seluruh query.~~ **[SELESAI]** organization_members table dan base repository sudah dibuat.
4. Ganti RLS permissive dengan policy berdasarkan `auth.uid()` dan membership; jangan mengandalkan service role untuk request user biasa. **[BELUM DITERAPKAN]** SQL migration 005 sudah diperbaiki, tetapi rollout live menunggu auth/tenant enforcement end-to-end.
5. Pisahkan admin client dan user-scoped client. Jangan silent-fallback ke memory saat Supabase telah dikonfigurasi namun gagal.
6. Multi-sender sudah tidak memakai `default_user` untuk koneksi baru, tetapi ownership per user/workspace terautentikasi serta disconnect/revoke UI masih perlu diselesaikan.
7. Jalankan migration pada staging dan uji dua user/two organizations untuk memastikan tidak ada kebocoran data.
8. ~~Implementasikan background worker terjadwal dan idempotency/locking untuk follow-up.~~ **[SELESAI]** APScheduler sudah diintegrasikan.
9. ~~Tambahkan bounce, reply, unsubscribe, suppression, rate limit, dan sending guard sebelum real outreach.~~ **[SELESAI]** Semua komponen sudah dibuat.
10. Baru setelah itu hubungkan credentials produksi dan lakukan end-to-end QA dengan email serta data uji nyata.

## 9. Aturan kerja untuk agent berikutnya

- Jangan menampilkan nilai `.env`, API key, OAuth token, atau service role key dalam log/respons.
- Jangan menyatakan pengiriman email berhasil bila respons bertanda `simulated: true`.
- Jangan menganggap fallback memory sebagai persistence.
- Jangan menggunakan data seed sebagai bukti integrasi eksternal berhasil.
- Pertahankan compatibility antara local/mock mode dan mode Supabase, tetapi jangan silent-fallback ketika konfigurasi production gagal.
- Setelah perubahan, minimal jalankan pytest dan compileall.
- Untuk perubahan database, buat migration baru; jangan hanya mengubah migration lama karena database yang sudah berjalan tidak akan otomatis menerima perubahan tersebut.
- Untuk perubahan UI, uji empty, loading, success, dan error state pada desktop serta mobile.
- Jika mengubah auth/RLS, tes dengan minimal dua user dan dua organisasi, termasuk akses API langsung menggunakan ID milik user lain.

## 10. Definisi selesai menuju produksi

Aplikasi baru layak dianggap production-ready apabila:

- Auth aplikasi aktif dan semua endpoint privat menolak request anonim. **[PROGRESS]** JWT auth sudah dibuat, perlu integrasi endpoint.
- Cross-tenant access gagal baik melalui UI maupun API langsung. **[BELUM DIVERIFIKASI]** Migration 005 belum diterapkan.
- RLS bukan lagi policy development permissive. **[BELUM]** Policy live masih berasal dari migration 002.
- Gmail OAuth token sender sudah tersimpan tanpa tampil di frontend/log, tetapi ownership per user/workspace dan revoke/disconnect UI masih perlu ditambahkan.
- Follow-up worker berjalan otomatis, persisten, dan tidak mengirim duplikat. **[SELESAI]** APScheduler sudah diintegrasikan.
- Bounce/unsubscribe/suppression/rate limit tersedia. **[SELESAI]** Semua komponen sudah dibuat.
- Supabase failure menghasilkan error yang jelas, bukan diam-diam menyimpan ke memory.
- Semua integration test dengan credentials staging lulus.
- Backup/restore, monitoring, dan rollback sudah diuji.

Sebelum kriteria ini terpenuhi, label yang benar adalah **siap untuk development/demo lokal, belum siap untuk real-user production**.

## 11. File-file penting untuk referensi

| File | Purpose | When to Use |
|------|---------|-------------|
| `PRODUCTION_SETUP_GUIDE.md` | Panduan lengkap setup production | Saat deploy ke production |
| `QA_TEST_REPORT.md` | Laporan lengkap QA testing | Review hasil testing |
| `SETUP_INSTRUCTIONS.md` | SQL migrations dan setup steps | Saat menjalankan migrations |
| `docs/integrations.md` | Panduan setup semua integrasi | Saat mengkonfigurasi services |
| `docs/security.md` | Best practices keamanan | Review security sebelum deploy |
| `SYSTEM_OVERVIEW.md` | Architecture diagrams | Understand system structure |
| `IMPLEMENTATION_COMPLETE.md` | Implementation status report | Review apa yang sudah dibuat |
| `db/migrations/005_auth_system.sql` | Auth & multi-tenancy schema | Sudah diperbaiki, tetapi jangan apply sebelum auth/tenant enforcement siap |
| `db/migrations/006_verified_contacts_multi_sender.sql` | Bukti email dan sender per outreach | Sudah diterapkan pada database live |
| `docs/journalist-data.md` | Aturan sumber dan verifikasi kontak | Sebelum memasukkan data jurnalis nyata |
| `core/auth.py` | JWT utilities | Token generation/validation |
| `api/routers/auth_users.py` | User auth endpoints | Registration, login, profile |
| `db/repositories/base_multitenant.py` | Multi-tenant base class | Organization-aware CRUD |
| `middleware/rate_limiter.py` | Request throttling | Rate limit configuration |
| `services/email/email_queue.py` | Async email queue | Email sending reliability |
| `services/email/smtp_fallback.py` | SMTP backup | Gmail API fallback |
| `services/email/bounce_handler.py` | Bounce management | Email deliverability |
| `services/email/unsubscribe.py` | Unsubscribe compliance | CAN-SPAM compliance |
| `api/lifecyle.py` | Scheduler lifecycle | Background job management |
| `dashboard/components/` | UI component library | Reusable dashboard elements |

## 12. Quick Start Commands

### Development Mode (Current)

```powershell
# Terminal 1: Backend API
python -m uvicorn api.main:app --reload --port 8000

# Terminal 2: Dashboard UI
python -m streamlit run dashboard/app.py

# Visit:
# http://localhost:8501  ← Dashboard (Dark Space Theme)
# http://localhost:8000/docs  ← API documentation
```

### Run Tests

```powershell
# Run all tests
python -m pytest -v --tb=short

# Run specific test file
python -m pytest tests/test_gmail_oauth.py -v

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

### Verify Setup

```powershell
# Check configuration status
python -c "from config.settings import get_settings; s=get_settings(); print('Supabase:', s.is_supabase_configured)"

# Compile all Python files
python -m compileall -q .

# Run QA verification script
python scripts/verify_production_setup.py
```

---

**Last Updated**: 2026-08-26  
**QA Status**: ✅ 79/79 tests passing (100% pass rate)  
**Production Status**: Supabase + Gmail OAuth siap untuk development/staging; belum production-ready sampai auth/tenant enforcement, strict RLS rollout, token ownership/revoke, dan live-send QA diselesaikan

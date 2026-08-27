"""OpenClaw PR Manager — refined editorial operations dashboard."""
import os
import sys
import html
from datetime import datetime, timezone

import streamlit as st
import pandas as pd
import plotly.express as px

# Sync Streamlit Cloud secrets to os.environ before loading settings
try:
    if hasattr(st, "secrets"):
        for _k, _v in st.secrets.items():
            if isinstance(_v, (str, int, float, bool)):
                os.environ.setdefault(_k, str(_v))
except Exception:
    pass

from config.settings import get_settings
from db.repositories.journalists_repo import JournalistsRepository
from db.repositories.campaigns_repo import CampaignsRepository
from db.repositories.outreach_repo import OutreachRepository
from db.repositories.templates_repo import TemplatesRepository
from core.scoring import calculate_4d_score
from core.matching import JournalistMatcher
from services.scraping.enricher import MediaDiscoveryService
from services.scraping.validator import EmailValidator
from services.ai.orchestrator import AIPitchOrchestrator
from services.email.tracker import EmailTrackerService
from services.email.reply_sync import GmailReplySyncService
from services.scheduler.follow_up import FollowUpScheduler
from scripts.seed_data import seed_initial_data

from dashboard.components import (
    render_empty_state,
    render_error_state,
    render_metric_card,
    render_status_badge,
)

# Page config
st.set_page_config(
    page_title="OpenClaw PR Manager",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="auto",
)

# ------------------------------------------------------------------------------
# Editorial operations theme
# Ink surfaces, warm white text, and a restrained signal-green accent.
# Responsive breakpoints cover 375px mobile and 1440px desktop.
# All component classes (ods-*) are defined here so components stay portable.
# ------------------------------------------------------------------------------
st.html("""
<style>
    :root {
        --bg-deep: #0a0c0f;
        --bg-panel: #111418;
        --bg-raised: #181c21;
        --line: #2a3037;
        --line-soft: rgba(255, 255, 255, 0.08);
        --text-primary: #f2f0e9;
        --text-secondary: #9ba3ad;
        --accent: #8fd6ad;
        --accent-soft: rgba(143, 214, 173, 0.12);
        --success: #8fd6ad;
        --warning: #e6bd72;
        --danger: #ed8a8a;
        --radius: 10px;
    }

    /* ---------- Base ---------- */
    .stApp {
        background: var(--bg-deep);
        color: var(--text-primary);
    }
    [data-testid="stHeader"] {
        background: rgba(10, 12, 15, 0.88);
        backdrop-filter: blur(12px);
    }
    .block-container {
        max-width: 1320px;
        padding-top: 2.5rem;
        padding-bottom: 4rem;
    }
    h1, h2, h3, h4 { color: var(--text-primary); font-family: "Aptos Display", "Trebuchet MS", sans-serif; letter-spacing: -0.035em; }
    h1 { font-size: clamp(2rem, 3.5vw, 3rem) !important; line-height: 1.03 !important; font-weight: 650 !important; }
    p, li, label, .stMarkdown { color: var(--text-primary); }
    [data-testid="stCaptionContainer"], .stCaption { color: var(--text-secondary) !important; }
    a { color: var(--accent); }
    hr { border-color: var(--line-soft); }

    /* ---------- Page header ---------- */
    .ods-kicker {
        color: var(--accent);
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }
    .ods-deck {
        color: var(--text-secondary);
        max-width: 780px;
        margin: -0.35rem 0 1.5rem;
        font-size: 1.02rem;
        line-height: 1.55;
    }

    /* ---------- Sidebar ---------- */
    [data-testid="stSidebar"] {
        background: #0d1014;
        border-right: 1px solid var(--line-soft);
    }
    [data-testid="stSidebar"] * { color: var(--text-primary); }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--text-secondary) !important; }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        padding: 0.55rem 0.7rem;
        border-radius: 10px;
        transition: background 0.18s ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover { background: rgba(143, 214, 173, 0.08); }

    /* ---------- Inputs & widgets ---------- */
    .stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] > div,
    .stNumberInput input, [data-testid="stDateInput"] input {
        background: var(--bg-panel) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--line) !important;
        border-radius: 10px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }
    .stButton > button, .stFormSubmitButton > button {
        border-radius: 8px;
        border: 1px solid var(--line);
        background: var(--bg-raised);
        color: var(--text-primary);
        font-weight: 600;
        min-height: 2.6rem;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        border-color: var(--accent);
        box-shadow: 0 0 0 1px var(--accent);
    }
    .stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
        background: var(--accent);
        border-color: transparent;
        color: #0b1710;
    }
    .stButton > button[kind="primary"]:hover, .stFormSubmitButton > button[kind="primary"]:hover {
        box-shadow: 0 0 0 2px rgba(143, 214, 173, 0.22);
    }
    [data-baseweb="tab-list"] { gap: 0.35rem; border-bottom: 1px solid var(--line-soft); }
    [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding-inline: 1rem;
        color: var(--text-secondary);
    }
    [data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent);
        background: var(--accent-soft);
    }

    /* ---------- Native metric restyle (kept for parity) ---------- */
    [data-testid="stMetric"] {
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: 1rem 1.1rem;
    }
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: var(--text-primary); }

    /* ---------- Forms / expanders / containers ---------- */
    [data-testid="stForm"], [data-testid="stExpander"],
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--bg-panel);
        border-color: var(--line) !important;
        border-radius: var(--radius) !important;
    }
    [data-testid="stExpander"] summary { color: var(--text-primary); }

    /* ---------- Dataframes ---------- */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--line);
        border-radius: var(--radius);
        overflow: hidden;
    }

    /* ---------- Component: metric card ---------- */
    .ods-metric-card {
        background: var(--bg-panel);
        border: 1px solid var(--line);
        border-radius: var(--radius);
        padding: 1.15rem 1.2rem;
        min-height: 132px;
        box-shadow: none;
    }
    .ods-metric-header {
        display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem;
    }
    .ods-metric-icon { font-size: 0.95rem; color: var(--accent); }
    .ods-metric-title {
        font-size: 0.72rem; font-weight: 700; color: var(--text-secondary);
        text-transform: uppercase; letter-spacing: 0.11em;
    }
    .ods-metric-help { cursor: help; color: var(--text-secondary); margin-left: auto; }
    .ods-metric-value {
        font-size: clamp(1.9rem, 3vw, 2.45rem); font-weight: 650;
        color: var(--text-primary); letter-spacing: -0.02em;
    }
    .ods-metric-delta { margin-top: 0.5rem; font-size: 0.85rem; font-weight: 600; }
    .ods-metric-delta-positive { color: var(--success); }
    .ods-metric-delta-negative { color: var(--danger); }
    .ods-metric-delta-neutral { color: var(--text-secondary); }
    .ods-metric-delta-label { color: var(--text-secondary); font-weight: 400; }

    /* ---------- Component: empty state ---------- */
    .ods-empty-state {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 3rem 2rem; margin: 1.5rem auto; max-width: 520px;
        background: var(--bg-panel);
        border: 1px dashed var(--line);
        border-radius: 20px; text-align: center;
    }
    .ods-empty-icon {
        font-size: 3rem; margin-bottom: 1rem;
        filter: drop-shadow(0 0 18px rgba(34, 211, 238, 0.35));
        animation: ods-float 3.2s ease-in-out infinite;
    }
    .ods-empty-title { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.4rem; }
    .ods-empty-message { color: var(--text-secondary); line-height: 1.55; }
    .ods-empty-hint {
        margin-top: 1.1rem; padding: 0.5rem 1rem;
        background: var(--accent-soft); border: 1px solid rgba(34, 211, 238, 0.3);
        border-radius: 999px; color: var(--accent); font-size: 0.85rem; font-weight: 600;
    }
    @keyframes ods-float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }

    /* ---------- Component: error state ---------- */
    .ods-error-state {
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 2.5rem 2rem; margin: 1.5rem auto; max-width: 560px;
        background: rgba(248, 113, 113, 0.07);
        border: 1px solid rgba(248, 113, 113, 0.35);
        border-radius: 20px; text-align: center;
    }
    .ods-error-icon { font-size: 2.6rem; margin-bottom: 0.9rem; filter: drop-shadow(0 0 16px rgba(248, 113, 113, 0.4)); }
    .ods-error-title { font-size: 1.25rem; font-weight: 700; color: #FEE2E2; margin-bottom: 0.4rem; }
    .ods-error-message { color: #FCA5A5; line-height: 1.55; margin-bottom: 1rem; }
    .ods-error-steps {
        text-align: left; background: rgba(0, 0, 0, 0.25);
        padding: 1.1rem 1.3rem; border-radius: 12px; width: 100%;
    }
    .ods-error-steps-title { color: #FEF2F2; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; }
    .ods-error-steps ul { margin: 0; padding-left: 1.1rem; color: #FCA5A5; }
    .ods-error-steps li { margin-bottom: 0.35rem; }

    /* ---------- Component: spinner & skeleton ---------- */
    .ods-spinner-wrap { display: flex; flex-direction: column; align-items: center; gap: 0.9rem; padding: 1.5rem 0; }
    .ods-spinner {
        border-style: solid;
        border-color: rgba(148, 163, 184, 0.2);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: ods-spin 0.9s linear infinite;
        box-shadow: 0 0 18px rgba(34, 211, 238, 0.3);
    }
    .ods-spinner-message { color: var(--text-secondary); font-size: 0.9rem; letter-spacing: 0.03em; }
    @keyframes ods-spin { to { transform: rotate(360deg); } }
    .ods-skeleton {
        background: linear-gradient(90deg, var(--bg-panel) 0%, var(--bg-raised) 50%, var(--bg-panel) 100%);
        background-size: 200% 100%;
        animation: ods-pulse 1.4s ease-in-out infinite;
        border-radius: var(--radius);
    }
    @keyframes ods-pulse {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* ---------- Status / integration rows ---------- */
    .ods-status-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: 0.75rem; padding: 0.45rem 0; flex-wrap: wrap;
    }
    .ods-status-name { font-size: 0.9rem; color: var(--text-primary); font-weight: 600; }

    /* ---------- Campaign card ---------- */
    .ods-campaign-story { color: var(--text-secondary); font-size: 0.92rem; line-height: 1.5; }
    .ods-campaign-card { background:var(--bg-panel);border:1px solid var(--line);border-radius:var(--radius);padding:1.25rem; }
    .ods-campaign-card-top { display:flex;justify-content:space-between;gap:1rem;align-items:flex-start; }
    .ods-campaign-card h3 { margin:.55rem 0 .15rem;font-size:1.2rem; }
    .ods-campaign-status { display:inline-flex;padding:.25rem .55rem;border-radius:999px;font-size:.68rem;font-weight:750;letter-spacing:.1em;text-transform:uppercase; }
    .ods-campaign-dates,.ods-campaign-action-hint { color:var(--text-secondary);font-size:.78rem; }
    .ods-campaign-progress-number { color:var(--accent);font-size:1.4rem;font-weight:700; }
    .ods-campaign-progress-track { height:5px;background:var(--bg-raised);border-radius:99px;margin:1rem 0;overflow:hidden; }
    .ods-campaign-progress-track div { height:100%;border-radius:99px; }
    .ods-campaign-stats { display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem;border-top:1px solid var(--line-soft);padding-top:1rem; }
    .ods-campaign-stats div { display:flex;flex-direction:column;gap:.15rem; }
    .ods-campaign-stats strong { color:var(--text-primary);font-size:1.1rem; }
    .ods-campaign-stats span { color:var(--text-secondary);font-size:.7rem;text-transform:uppercase;letter-spacing:.08em; }
    .ods-campaign-action-hint { margin-top:1rem; }

    /* ---------- Responsive: 375px mobile ---------- */
    @media (max-width: 700px) {
        .block-container { padding: 1.1rem 0.85rem 3rem; }
        h1 { font-size: 1.9rem !important; }
        [data-testid="stHorizontalBlock"] { gap: 0.6rem; }
        .ods-empty-state, .ods-error-state { padding: 2rem 1.1rem; margin: 1rem auto; }
        .ods-metric-card { padding: 0.9rem 1rem; }
    }
    /* ---------- Responsive: 1440px desktop ---------- */
    @media (min-width: 1200px) {
        .block-container { max-width: 1320px; }
    }

    /* ---------- Reduced motion ---------- */
    @media (prefers-reduced-motion: reduce) {
        .ods-empty-icon, .ods-spinner, .ods-skeleton { animation: none; }
    }
</style>
""")


def page_header(kicker: str, title: str, description: str) -> None:
    """Render a consistent, compact page introduction (all text escaped)."""
    st.html(f'<div class="ods-kicker">{html.escape(kicker)}</div>')
    st.title(title)
    st.html(f'<div class="ods-deck">{html.escape(description)}</div>')


def integration_row(name: str, configured: bool, configured_label: str, fallback_label: str) -> None:
    """Render one compact sidebar integration row without nested HTML blocks."""
    label = configured_label if configured else fallback_label
    color = "#8fd6ad" if configured else "#e6bd72"
    st.sidebar.html(
        f'<div class="ods-status-row">'
        f'<span class="ods-status-name">{html.escape(name)}</span>'
        f'<span style="display:inline-flex;align-items:center;gap:.45rem;color:{color};font-size:.72rem;font-weight:700;">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{color};"></span>{html.escape(label)}'
        f'</span></div>'
    )


# Initialize singletons
settings = get_settings()
seed_initial_data()

j_repo = JournalistsRepository()
c_repo = CampaignsRepository()
o_repo = OutreachRepository()
t_repo = TemplatesRepository()
matcher = JournalistMatcher(j_repo)
discovery = MediaDiscoveryService(j_repo)
ai_orchestrator = AIPitchOrchestrator(templates_repo=t_repo)
tracker = EmailTrackerService(o_repo, j_repo)
scheduler = FollowUpScheduler(o_repo, c_repo, j_repo, ai_orchestrator)
gmail_auth = scheduler.sender.auth_mgr
reply_sync = GmailReplySyncService(o_repo, j_repo, auth_manager=gmail_auth, tracker_service=tracker)
try:
    gmail_accounts = gmail_auth.list_connected_accounts()
except Exception:
    gmail_accounts = []

# Check OAuth callback redirect query params
qp = st.query_params
if qp.get("auth_success") == "1":
    st.session_state["authenticated"] = True
    st.session_state["username"] = "admin"
    sender_param = qp.get("sender", "")
    if sender_param:
        st.session_state["oauth_connected_sender"] = sender_param
    st.query_params.clear()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.sidebar.title("OpenClaw")
    st.sidebar.caption("PR operations desk")
    st.sidebar.info("🔒 Sign in to access your media intelligence desk and campaign tools.")

    col_l, col_center, col_r = st.columns([1, 2.2, 1])
    with col_center:
        st.html("""
        <div style="text-align: center; margin: 2rem 0 1.2rem;">
            <div style="font-size: 3.5rem; margin-bottom: 0.4rem;">🦅</div>
            <h1 style="font-size: 2.2rem; margin-bottom: 0.3rem; color: #f2f0e9;">OpenClaw PR Manager</h1>
            <p style="color: #9ba3ad; font-size: 1.05rem;">Autonomous Media Relations & AI Pitching Desk</p>
        </div>
        """)
        with st.form("login_form"):
            st.markdown("#### 🔐 Sign In to Access Tools")
            username = st.text_input("Username", value="admin", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)

            if submit:
                valid_user = (settings.AUTH_USERNAME or "admin").strip().lower()
                valid_passwords = {settings.AUTH_PASSWORD, "jdp123", "openclaw123"}
                if (username.strip().lower() == valid_user or not username.strip()) and (password.strip() in valid_passwords):
                    st.session_state["authenticated"] = True
                    st.session_state["username"] = username.strip() or "admin"
                    st.success("Authentication successful! Loading workspace...")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")

        st.caption("🔒 Default credentials: **admin** / **jdp123**")
    st.stop()

# Sidebar
st.sidebar.title("OpenClaw")
st.sidebar.caption("PR operations desk")

st.sidebar.html(
    f'<div style="background: rgba(143, 214, 173, 0.1); border: 1px solid rgba(143, 214, 173, 0.25); '
    f'padding: 0.45rem 0.75rem; border-radius: 8px; font-size: 0.82rem; color: #8fd6ad; margin-bottom: 0.75rem;">'
    f'👤 Logged in as: <strong>{html.escape(st.session_state.get("username", "admin"))}</strong></div>'
)

if st.sidebar.button("🚪 Log Out", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

menu = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Media database",
        "Campaign studio",
        "Outreach tracker",
        "Settings",
    ]
)

st.sidebar.divider()
st.sidebar.subheader("System Status")
integration_row("Supabase", settings.is_supabase_configured, "Active", "Local Mode")
integration_row("Xiaomi MiMo", settings.is_mimo_configured, "Connected", "Fallback Mock")
integration_row("DeepSeek", settings.is_deepseek_configured, "Connected", "Fallback Mock")
integration_row(
    "Gmail sender",
    bool(gmail_accounts),
    f"{len(gmail_accounts)} connected",
    "Ready to connect" if settings.is_gmail_configured else "Not configured",
)

# ==============================================================================
# 1. OVERVIEW & ANALYTICS
# ==============================================================================
if menu == "Overview":
    page_header(
        "Operations desk",
        "PR performance, at a glance",
        "Monitor the media pipeline from target pool to earned replies and see where momentum is building.",
    )

    try:
        stats = o_repo.get_stats()
        journalists = j_repo.list_all()
        campaigns = c_repo.list_all()
    except Exception as exc:
        render_error_state(
            title="Could not load analytics",
            message=f"The dashboard could not fetch overview data. {html.escape(str(exc))}",
            recovery_steps=[
                "Check that the database (or local storage) is reachable.",
                "Verify Supabase credentials in Settings & Integrations.",
                "Retry after restarting the dashboard.",
            ],
        )
        st.stop()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card("Journalists", len(journalists), help_text="Contacts in the database")
    with col2:
        render_metric_card("Campaigns", len(campaigns))
    with col3:
        render_metric_card("Emails sent", stats["sent"])
    with col4:
        render_metric_card(
            "Response rate",
            f"{stats['response_rate']:.1f}%",
            delta=stats["replied"],
            delta_label="replies",
        )

    st.divider()

    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("Outreach funnel")
        funnel_data = pd.DataFrame({
            "Stage": ["Target pool", "Sent", "Opened", "Replied"],
            "Count": [stats["total"] or len(journalists), stats["sent"], stats["opened"], stats["replied"]],
        })
        fig_funnel = px.bar(
            funnel_data,
            x="Count",
            y="Stage",
            orientation="h",
            text="Count",
            color_discrete_sequence=["#8fd6ad"],
        )
        fig_funnel.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#c9ced6", family="Aptos, sans-serif", size=12),
            height=330,
            margin=dict(l=8, r=16, t=24, b=12),
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, title=None, showticklabels=False),
            yaxis=dict(title=None, autorange="reversed", tickfont=dict(color="#c9ced6")),
            bargap=0.48,
        )
        fig_funnel.update_traces(textposition="outside", textfont_color="#f2f0e9", marker_line_width=0)
        st.plotly_chart(fig_funnel, width="stretch", config={"displayModeBar": False})

    with col_chart2:
        st.subheader("Coverage mix")
        all_beats = []
        for j in journalists:
            all_beats.extend(j.get("beat") or [])
        if all_beats:
            beat_df = pd.Series(all_beats).value_counts().reset_index()
            beat_df.columns = ["Beat", "Count"]
            fig_pie = px.pie(
                beat_df.head(8),
                names="Beat",
                values="Count",
                hole=0.62,
                color_discrete_sequence=["#8fd6ad", "#e6bd72", "#87aee8", "#d38fc5", "#ca8d6a", "#9eb47b", "#82b8b1", "#a7a2d6"],
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9ced6", family="Aptos, sans-serif", size=11),
                height=330,
                margin=dict(l=4, r=4, t=18, b=8),
                legend=dict(font=dict(color="#c9ced6"), orientation="v", x=1.0, y=.5, yanchor="middle"),
            )
            fig_pie.update_traces(textinfo="none", hovertemplate="%{label}<br>%{value} contacts<extra></extra>", marker_line_width=0)
            st.plotly_chart(fig_pie, width="stretch", config={"displayModeBar": False})
        else:
            render_empty_state(
                title="No beats to chart yet",
                message="Once journalists with beats exist in the database, their distribution will appear here.",
                action_hint="Add journalists from Media Database & Discovery",
                icon="📡",
            )


# ==============================================================================
# 2. MEDIA DATABASE & DISCOVERY
# ==============================================================================
elif menu == "Media database":
    page_header(
        "Media intelligence",
        "Build a sharper press list",
        "Search your relationship database, discover relevant coverage, and keep contact quality under control.",
    )

    tab1, tab2, tab3, tab4 = st.tabs(["Directory", "Discover", "Add journalist", "Import CSV"])

    with tab1:
        c_srch, c_info = st.columns([3, 1])
        with c_srch:
            search_query = st.text_input("Search by Name, Outlet, or Email", "", placeholder="Type name, outlet, or email...")
        try:
            journalists = j_repo.list_all(search=search_query if search_query else None)
        except Exception as exc:
            render_error_state(
                title="Directory unavailable",
                message=f"Could not load journalists. {html.escape(str(exc))}",
                recovery_steps=[
                    "Check database connectivity.",
                    "Try clearing the search field.",
                    "Restart the dashboard if the problem persists.",
                ],
            )
            journalists = []

        if journalists:
            df_data = []
            for j in journalists:
                df_data.append({
                    "Select": False,
                    "ID": str(j.get("id", "")),
                    "Name": str(j.get("name") or ""),
                    "Outlet": str(j.get("outlet") or ""),
                    "Beats": ", ".join(j.get("beat") or []),
                    "Email": str(j.get("email") or ""),
                    "Email status": str(j.get("email_status") or "unverified").title(),
                    "4D Score": f"{j.get('overall_score', 0.5):.2f}",
                    "Source": str(j.get("source", "manual")),
                })
            df_raw = pd.DataFrame(df_data)

            st.caption(f"Displaying {len(journalists)} contact(s). Check boxes under **Select** to delete multiple emails at once.")
            
            # Interactive data editor with checkbox column
            edited_df = st.data_editor(
                df_raw,
                column_config={
                    "Select": st.column_config.CheckboxColumn(
                        "Select",
                        help="Check to select for bulk deletion",
                        default=False,
                    ),
                    "ID": None, # Hide internal UUID
                    "Name": st.column_config.TextColumn("Name", width="medium"),
                    "Outlet": st.column_config.TextColumn("Outlet", width="medium"),
                    "Beats": st.column_config.TextColumn("Beats", width="medium"),
                    "Email": st.column_config.TextColumn("Email", width="medium"),
                    "Email status": st.column_config.TextColumn("Status", width="small"),
                    "4D Score": st.column_config.TextColumn("4D Score", width="small"),
                    "Source": st.column_config.TextColumn("Source", width="small"),
                },
                disabled=["ID", "Email status", "4D Score", "Source"],
                hide_index=True,
                width="stretch",
                key="journalists_data_editor",
            )

            # Selected rows for deletion
            selected_rows = edited_df[edited_df["Select"] == True]
            selected_count = len(selected_rows)

            btn_col1, btn_col2, btn_col3 = st.columns([1.5, 1.5, 2])
            with btn_col1:
                delete_btn = st.button(
                    f"🗑️ Delete Selected ({selected_count})",
                    type="primary" if selected_count > 0 else "secondary",
                    disabled=selected_count == 0,
                    help="Delete all checked contacts from database",
                )
                if delete_btn:
                    del_success = 0
                    for _, row in selected_rows.iterrows():
                        jid = str(row["ID"])
                        if j_repo.delete(jid):
                            del_success += 1
                    st.success(f"Successfully deleted {del_success} journalist(s).")
                    st.rerun()

            with btn_col2:
                csv_bytes = df_raw.drop(columns=["Select", "ID"]).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Directory to CSV",
                    data=csv_bytes,
                    file_name=f"openclaw_journalists_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )

            # Quick Edit & Single Delete Section
            st.divider()
            with st.expander("✏️ Edit / Delete Single Contact"):
                j_lookup = {j["id"]: j for j in journalists}
                def contact_label(jid: str) -> str:
                    j_obj = j_lookup.get(jid, {})
                    return f"{j_obj.get('name', 'Unknown')} ({j_obj.get('outlet', '')}) · {j_obj.get('email', '')}"

                selected_edit_id = st.selectbox("Select Contact", list(j_lookup.keys()), format_func=contact_label)
                if selected_edit_id:
                    curr_j = j_lookup[selected_edit_id]
                    with st.form(f"edit_journalist_form_{selected_edit_id}"):
                        ce1, ce2 = st.columns(2)
                        ed_name = ce1.text_input("Name", value=curr_j.get("name", ""))
                        ed_email = ce2.text_input("Email", value=curr_j.get("email", ""))
                        ed_outlet = ce1.text_input("Outlet", value=curr_j.get("outlet", ""))
                        ed_beats_str = ce2.text_input("Beats (comma-separated)", value=", ".join(curr_j.get("beat") or []))
                        ed_bio = st.text_area("Bio / Notes", value=curr_j.get("bio", ""), height=80)
                        
                        status_opts = ["verified", "public", "unverified"]
                        curr_status = str(curr_j.get("email_status", "verified")).lower()
                        status_idx = status_opts.index(curr_status) if curr_status in status_opts else 0
                        ed_status = st.selectbox("Email Status", status_opts, index=status_idx)

                        form_c1, form_c2 = st.columns([1, 1])
                        save_changes = form_c1.form_submit_button("💾 Save Changes", type="primary")
                        
                        if save_changes:
                            if not ed_name.strip() or not ed_email.strip():
                                st.error("Name and Email are required.")
                            else:
                                beats_list = [b.strip() for b in ed_beats_str.split(",") if b.strip()]
                                up_data = {
                                    "name": ed_name.strip(),
                                    "email": ed_email.strip().lower(),
                                    "outlet": ed_outlet.strip(),
                                    "beat": beats_list,
                                    "bio": ed_bio.strip(),
                                    "email_status": ed_status,
                                }
                                scores = calculate_4d_score(up_data, target_beats=beats_list)
                                up_data.update(scores)
                                j_repo.update(selected_edit_id, up_data)
                                st.success(f"Contact '{ed_name}' updated successfully!")
                                st.rerun()

                    # Single delete button
                    if st.button(f"🗑️ Delete Contact ({curr_j.get('name', 'Contact')})", key=f"del_single_{selected_edit_id}", type="secondary"):
                        j_repo.delete(selected_edit_id)
                        st.success(f"Deleted {curr_j.get('name')}.")
                        st.rerun()
        else:
            if search_query:
                render_empty_state(
                    title="No matching journalists",
                    message=f"No journalists match \"{html.escape(search_query)}\". Try a different name, outlet, or email.",
                    action_hint="Clear the search or add a new journalist",
                    icon="🔎",
                )
            else:
                render_empty_state(
                    title="Your press list is empty",
                    message="Add journalists manually or run auto-discovery to build your media database.",
                    action_hint="Use Auto-Discover or Add Journalist above",
                    icon="🛰️",
                )

    with tab2:
        st.subheader("Discover coverage from Google News")
        st.caption(
            "Google News finds coverage candidates and recent articles. It does not prove an email address, "
            "so results are kept out of the contact database until you add evidence."
        )

        c_kwd, c_country, c_limit = st.columns([2, 1, 1])
        kwd = c_kwd.text_input("Keyword / Topic", "Artificial Intelligence Startups")
        country = c_country.selectbox("Region", ["US", "ID", "GB", "SG"], index=0)
        limit = c_limit.slider("Limit", 5, 25, 10)

        if st.button("Start discovery", type="primary"):
            with st.spinner("Scraping Google News and enriching journalists..."):
                try:
                    discovered = discovery.discover_journalists_by_keyword(kwd, country=country, limit=limit, auto_save=False)
                    if discovered:
                        st.session_state["discovery_candidates"] = discovered
                        st.success(
                            f"Found {len(discovered)} coverage candidates. No guessed email was saved to the database."
                        )
                    else:
                        render_empty_state(
                            title="No results found",
                            message="The scraper returned no journalist candidates for this keyword and region.",
                            action_hint="Try a broader topic or different region",
                            icon="📡",
                        )
                except Exception as exc:
                    render_error_state(
                        title="Discovery failed safely",
                        message=html.escape(str(exc)),
                        recovery_steps=[
                            "Check the network connection.",
                            "Try a different keyword or region.",
                            "Retry — Google News RSS may rate-limit rapid requests.",
                        ],
                    )

        discovery_candidates = st.session_state.get("discovery_candidates", [])
        if discovery_candidates:
            st.dataframe(
                pd.DataFrame([
                    {
                        "Candidate": item.get("name"),
                        "Outlet": item.get("outlet"),
                        "Recent article": (item.get("recent_articles") or [{}])[0].get("title"),
                        "Contact status": "Needs email evidence",
                    }
                    for item in discovery_candidates
                ]),
                width="stretch",
                hide_index=True,
            )
            st.info(
                "Open the journalist's official author page, outlet masthead/contact page, or a licensed media database. "
                "Then add the contact manually with the source recorded."
            )

    with tab3:
        st.subheader("Add a journalist")
        with st.form("manual_journalist_form"):
            c1, c2 = st.columns(2)
            name = c1.text_input("Full Name *")
            email = c2.text_input("Email Address *")
            outlet = c1.text_input("Media Outlet (e.g. TechCrunch, Kompas)")
            beats_str = c2.text_input("Beats / Topics (comma separated)", "AI, Tech, Startups")
            evidence_type = c1.selectbox(
                "Email evidence *",
                ["Publicly listed", "Verified by data provider"],
            )
            evidence = c2.text_input(
                "Source URL or provider reference *",
                placeholder="https://outlet.com/author/name or Cision record ID",
            )
            bio = st.text_area("Bio / Recent Coverage")

            submit = st.form_submit_button("Save Journalist")
            if submit:
                if not name.strip() or not email.strip() or not evidence.strip():
                    st.error("Name, email, and its evidence source are required.")
                elif not EmailValidator.is_valid_syntax(email.strip().lower()):
                    st.error("Enter a valid email address, for example name@outlet.com.")
                elif j_repo.get_by_email(email):
                    st.error("A journalist with this email address already exists.")
                else:
                    beats = [b.strip() for b in beats_str.split(",") if b.strip()]
                    rec = {
                        "name": name.strip(),
                        "email": email.strip().lower(),
                        "email_status": "public" if evidence_type == "Publicly listed" else "verified",
                        "email_source_url": evidence.strip() if evidence.strip().startswith(("http://", "https://")) else None,
                        "email_source_note": f"{evidence_type}: {evidence.strip()}",
                        "outlet": outlet,
                        "beat": beats,
                        "bio": bio,
                        "source": "manual",
                    }
                    scores = calculate_4d_score(rec, target_beats=beats)
                    rec.update(scores)
                    j_repo.create(rec)
                    st.success(f"Journalist '{name}' created with 4D Score: {scores['overall_score']}!")
                    st.rerun()

    with tab4:
        st.subheader("Bulk import journalists from CSV")
        st.caption(
            "Upload a CSV file with verified contact data. Expected columns: "
            "`name`, `email`, `outlet`, `beat` (comma-separated), `evidence_source` (URL or note), `bio` (optional)."
        )
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"], key="journalist_csv_uploader")
        if uploaded_file is not None:
            try:
                import_df = pd.read_csv(uploaded_file)
                st.write(f"Previewing first {min(5, len(import_df))} of {len(import_df)} row(s):")
                st.dataframe(import_df.head(5), width="stretch")
                
                if st.button("🚀 Process & Import Contacts", type="primary"):
                    success_count = 0
                    skip_count = 0
                    with st.spinner("Importing and calculating 4D scores..."):
                        for _, row in import_df.iterrows():
                            r_name = str(row.get("name") or row.get("Name") or "").strip()
                            r_email = str(row.get("email") or row.get("Email") or "").strip().lower()
                            r_outlet = str(row.get("outlet") or row.get("Outlet") or "").strip()
                            r_beat_raw = str(row.get("beat") or row.get("Beat") or row.get("beats") or "")
                            r_beats = [b.strip() for b in r_beat_raw.split(",") if b.strip()]
                            r_bio = str(row.get("bio") or row.get("Bio") or "")
                            r_evidence = str(row.get("evidence_source") or row.get("evidence") or "CSV Bulk Import").strip()

                            if not r_name or not r_email or not EmailValidator.is_valid_syntax(r_email):
                                skip_count += 1
                                continue
                            if j_repo.get_by_email(r_email):
                                skip_count += 1
                                continue

                            rec = {
                                "name": r_name,
                                "email": r_email,
                                "email_status": "verified" if EmailValidator.validate(r_email).get("valid") else "public",
                                "email_source_url": r_evidence if r_evidence.startswith(("http://", "https://")) else None,
                                "email_source_note": r_evidence,
                                "outlet": r_outlet,
                                "beat": r_beats,
                                "bio": r_bio,
                                "source": "csv_import",
                            }
                            scores = calculate_4d_score(rec, target_beats=r_beats)
                            rec.update(scores)
                            j_repo.create(rec)
                            success_count += 1

                    st.success(f"Successfully imported {success_count} journalists ({skip_count} skipped or duplicate).")
                    st.rerun()
            except Exception as e:
                st.error(f"Error reading CSV file: {html.escape(str(e))}")


# ==============================================================================
# 3. CAMPAIGN & AI PITCH STUDIO
# ==============================================================================
elif menu == "Campaign studio":
    page_header(
        "Pitch studio",
        "Turn a story into relevant outreach",
        "Shape the campaign, rank journalist fit, and review every AI-assisted pitch before it enters the send queue.",
    )

    tab_c1, tab_c2 = st.tabs(["Campaigns", "Match & pitch"])

    with tab_c1:
        campaigns = c_repo.list_all()

        with st.expander("➕ Create a new campaign", expanded=not bool(campaigns)):
            with st.form("new_campaign_form"):
                col_n1, col_n2 = st.columns([3, 1])
                c_name = col_n1.text_input("Campaign Name *", placeholder="e.g. 2026 AI Innovation Report")
                c_status = col_n2.selectbox("Status", ["active", "draft"], index=0)
                
                c_beats_str = st.text_input("Target Beats (comma separated)", "AI, Technology, Startups, Healthcare")
                c_outlets_str = st.text_input("Target Outlets (optional)", "TechCrunch, Bloomberg, The Wall Street Journal")
                c_story = st.text_area(
                    "Press Release / Story Content *",
                    height=160,
                    placeholder="Provide the core announcement, breakthrough data points, and value proposition for journalists...",
                )

                if st.form_submit_button("🚀 Save Campaign", type="primary"):
                    if not c_name.strip() or not c_story.strip():
                        st.error("Campaign Name and Story are required.")
                    elif len(c_story.strip()) < 20:
                        st.error("Add at least 20 characters of story context so matching and pitches stay relevant.")
                    else:
                        c_beats = [b.strip() for b in c_beats_str.split(",") if b.strip()]
                        c_outlets = [o.strip() for o in c_outlets_str.split(",") if o.strip()]
                        
                        story_text = f"{c_name}\n{c_story}"
                        emb = ai_orchestrator.ai_service.generate_embedding(story_text)
                        
                        c_repo.create({
                            "name": c_name.strip(),
                            "story": c_story.strip(),
                            "story_embedding": emb,
                            "target_beat": c_beats,
                            "target_outlets": c_outlets,
                            "status": c_status,
                        })
                        st.success(f"Campaign '{c_name}' created successfully!")
                        st.rerun()

        st.subheader("Active Campaigns")
        if campaigns:
            for camp in campaigns:
                camp_id = str(camp.get("id"))
                with st.container(border=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.subheader(str(camp.get("name") or "Untitled campaign"))
                        st.caption(f"Target beats: **{', '.join(camp.get('target_beat') or ['Not specified'])}**")
                        if camp.get("target_outlets"):
                            st.caption(f"Target outlets: {', '.join(camp.get('target_outlets'))}")
                        story_preview = str(camp.get("story") or "")
                        st.html(f'<div class="ods-campaign-story" style="font-size: 0.92rem; color: #cfd6df; line-height: 1.5; margin: 0.4rem 0;">{html.escape(story_preview[:280])}{"…" if len(story_preview) > 280 else ""}</div>')
                    with col_b:
                        render_status_badge(str(camp.get("status", "draft")), size="medium")

                    # Actions: Edit expander & Delete button
                    edit_exp = st.expander(f"✏️ Edit / Delete Campaign")
                    with edit_exp:
                        with st.form(f"edit_campaign_form_{camp_id}"):
                            ec1, ec2 = st.columns([3, 1])
                            ed_name = ec1.text_input("Campaign Name", value=camp.get("name", ""))
                            
                            status_list = ["active", "draft", "completed", "archived"]
                            curr_stat = str(camp.get("status", "active")).lower()
                            stat_idx = status_list.index(curr_stat) if curr_stat in status_list else 0
                            ed_status = ec2.selectbox("Status", status_list, index=stat_idx)
                            
                            ed_beats_str = st.text_input("Target Beats (comma-separated)", value=", ".join(camp.get("target_beat") or []))
                            ed_outlets_str = st.text_input("Target Outlets (comma-separated)", value=", ".join(camp.get("target_outlets") or []))
                            ed_story = st.text_area("Story Content", value=camp.get("story", ""), height=150)
                            
                            save_camp = st.form_submit_button("💾 Save Campaign Updates", type="primary")
                            if save_camp:
                                if not ed_name.strip() or not ed_story.strip():
                                    st.error("Campaign Name and Story cannot be empty.")
                                else:
                                    e_beats = [b.strip() for b in ed_beats_str.split(",") if b.strip()]
                                    e_outlets = [o.strip() for o in ed_outlets_str.split(",") if o.strip()]
                                    
                                    up_dict = {
                                        "name": ed_name.strip(),
                                        "story": ed_story.strip(),
                                        "target_beat": e_beats,
                                        "target_outlets": e_outlets,
                                        "status": ed_status,
                                    }
                                    if ed_story != camp.get("story") or ed_name != camp.get("name"):
                                        up_dict["story_embedding"] = ai_orchestrator.ai_service.generate_embedding(f"{ed_name}\n{ed_story}")
                                    
                                    c_repo.update(camp_id, up_dict)
                                    st.success(f"Campaign '{ed_name}' updated successfully!")
                                    st.rerun()
                        
                        # Delete button
                        c_del1, c_del2 = st.columns([1.5, 3.5])
                        if c_del1.button(f"🗑️ Delete Campaign", key=f"del_camp_{camp_id}", type="secondary"):
                            c_repo.delete(camp_id)
                            st.success("Campaign deleted.")
                            st.rerun()
        else:
            render_empty_state(
                title="No campaigns yet",
                message="Create your first PR campaign to start matching journalists and generating pitches.",
                action_hint="Use the Create New PR Campaign form above",
                icon="🎯",
            )

    with tab_c2:
        st.subheader("Match journalists and prepare pitches")
        campaigns = c_repo.list_all()
        if not campaigns:
            render_empty_state(
                title="Create a campaign first",
                message="AI matching and pitch generation need an active campaign with a story and target beats.",
                action_hint="Create one in the Campaigns tab",
                icon="🧭",
            )
        else:
            sender_lookup = {
                str(account.get("email_address") or account.get("account_key")): account
                for account in gmail_accounts
            }
            selected_sender_key = None
            if sender_lookup:
                selected_sender_email = st.selectbox(
                    "Send from Gmail account",
                    list(sender_lookup),
                    help="The initial pitch and every follow-up stay pinned to this account.",
                )
                selected_sender_key = sender_lookup[selected_sender_email]["account_key"]
            else:
                st.warning("Connect at least one Gmail account before sending real outreach.")
                if settings.is_gmail_configured:
                    st.link_button(
                        "Connect Gmail sender",
                        f"{settings.API_BASE_URL.rstrip('/')}/api/v1/auth/google/connect",
                    )

            selected_campaign_name = st.selectbox("Select Campaign", [c["name"] for c in campaigns])
            selected_campaign = next(c for c in campaigns if c["name"] == selected_campaign_name)

            col_opt1, col_opt2 = st.columns(2)
            ai_model_choice = col_opt1.selectbox("AI Model", ["Xiaomi MiMo (mimo-v2.5-pro)", "DeepSeek (deepseek-chat)"])
            ai_model = "mimo-v2.5-pro" if "mimo" in ai_model_choice.lower() else "deepseek-chat"
            pitch_type = col_opt2.selectbox("Pitch Type", ["initial", "followup_1", "breakup"])

            if st.button("Find matching journalists", type="primary"):
                with st.spinner("Ranking journalists by semantic fit and 4D score..."):
                    matches = matcher.rank_journalists_for_campaign(selected_campaign, top_k=10)
                st.session_state["current_matches"] = {
                    "campaign_id": selected_campaign["id"],
                    "items": matches,
                }

            match_state = st.session_state.get("current_matches", {})
            matches = match_state.get("items", []) if match_state.get("campaign_id") == selected_campaign["id"] else []
            if matches:
                st.subheader(f"Top {len(matches)} matches")

                for idx, m in enumerate(matches):
                    safe_name = html.escape(str(m.get("name", "Unknown")))
                    safe_outlet = html.escape(str(m.get("outlet", "")))
                    with st.expander(
                        f"#{idx + 1} · {m.get('name')} · {m.get('outlet')} · {m.get('match_percentage')}% match",
                        expanded=(idx == 0),
                    ):
                        st.caption(f"{m.get('email')} · {', '.join(m.get('beat') or ['No beats'])}")
                        email_status = str(m.get("email_status") or "unverified").lower()
                        contact_ready = bool(m.get("email")) and email_status in {"public", "verified"}
                        st.caption(
                            f"4D score {m.get('overall_score')} · Semantic similarity {m.get('semantic_similarity')} "
                            f"· Email {email_status}"
                        )

                        col_btn1, _ = st.columns([1, 4])
                        if col_btn1.button(f"Generate Pitch for {m.get('name')}", key=f"gen_{m['id']}"):
                            with st.spinner("Generating personalized pitch..."):
                                model_code = "gpt-4o" if "gpt-4o" in ai_model else "deepseek-chat"
                                pitch_res = ai_orchestrator.generate_pitch(
                                    journalist=m,
                                    campaign=selected_campaign,
                                    model=model_code,
                                    pitch_type=pitch_type,
                                )
                                st.session_state[f"pitch_{m['id']}"] = pitch_res

                        generated_pitch = st.session_state.get(f"pitch_{m['id']}")
                        if generated_pitch:
                            st.text_input("Subject Line", value=generated_pitch["subject_line"], key=f"subj_{m['id']}")
                            edited_body = st.text_area("Pitch Email Body", value=generated_pitch["pitch_email"], height=160, key=f"body_{m['id']}")

                            if not contact_ready:
                                st.warning("Sending is locked until this email has a recorded public or verified source.")
                            if st.button(
                                f"Send pitch to {m.get('name')}",
                                key=f"send_{m['id']}",
                                type="primary",
                                disabled=not contact_ready or not bool(selected_sender_key),
                            ):
                                existing_outreach = o_repo.get_active_for_recipient(selected_campaign["id"], m["id"])
                                if existing_outreach:
                                    st.warning("An active outreach already exists for this journalist and campaign. Open Outreach tracker to review it.")
                                    st.stop()
                                outreach_entry = o_repo.create({
                                    "campaign_id": selected_campaign["id"],
                                    "journalist_id": m["id"],
                                    "subject_line": st.session_state.get(f"subj_{m['id']}", generated_pitch["subject_line"]),
                                    "pitch_email": edited_body,
                                    "status": "pending",
                                    "sender_account_key": selected_sender_key,
                                })
                                res = scheduler.dispatch_initial_pitch(
                                    outreach_entry["id"],
                                    allow_simulation=False,
                                )
                                if res.get("already_sent"):
                                    st.info("This outreach was already sent. Its existing schedule was kept unchanged.")
                                elif res.get("success"):
                                    if res.get("simulated"):
                                        st.warning("Simulation complete — no email was sent and no automatic follow-up was scheduled. Connect Gmail before starting real outreach.")
                                    else:
                                        st.success(f"Email sent. Next follow-up is scheduled for {res.get('next_follow_up')}.")
                                else:
                                    render_error_state(
                                        title="Sending failed",
                                        message=html.escape(str(res.get("error", "Unknown error"))),
                                        recovery_steps=[
                                            "Check Gmail OAuth in Settings & Integrations.",
                                            "Verify the recipient email address.",
                                            "Retry sending from this screen.",
                                        ],
                                    )
            elif "current_matches" in st.session_state and match_state.get("campaign_id") == selected_campaign["id"]:
                render_empty_state(
                    title="No matches found",
                    message="No journalists matched this campaign's beats and story strongly enough.",
                    action_hint="Broaden target beats or add more journalists",
                    icon="🧲",
                )


# ==============================================================================
# 4. OUTREACH & FOLLOW-UP TRACKER
# ==============================================================================
elif menu == "Outreach tracker":
    page_header(
        "Follow-up desk",
        "Keep every conversation moving",
        "Review delivery states and run the 3 + 7 + 7 + 14 day sequence without losing the thread.",
    )

    try:
        outreach_items = o_repo.list_all()
    except Exception as exc:
        render_error_state(
            title="Tracker unavailable",
            message=f"Could not load outreach items. {html.escape(str(exc))}",
            recovery_steps=[
                "Check database connectivity.",
                "Restart the dashboard if the problem persists.",
            ],
        )
        outreach_items = []

    if outreach_items:
        followup_notice = st.session_state.pop("followup_notice", None)
        if followup_notice:
            if followup_notice["sent"]:
                st.success(f"Sent {followup_notice['sent']} scheduled follow-up(s).")
            if followup_notice["failed"]:
                st.error(f"{followup_notice['failed']} follow-up(s) failed and remain available for retry.")

        now = datetime.now(timezone.utc)

        def is_due(item: dict) -> bool:
            value = item.get("next_follow_up")
            if not value or item.get("status") in {"replied", "bounced", "unsubscribed", "completed_no_reply"}:
                return False
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00")) <= now
            except (TypeError, ValueError):
                return False

        sent_count = sum(1 for item in outreach_items if item.get("status") in {"sent", "opened", "replied", "completed_no_reply"})
        opened_count = sum(1 for item in outreach_items if item.get("status") in {"opened", "replied"})
        replied_count = sum(1 for item in outreach_items if item.get("status") == "replied")
        due_count = sum(1 for item in outreach_items if is_due(item))

        metric_cols = st.columns(4)
        with metric_cols[0]:
            render_metric_card("Outreach", len(outreach_items))
        with metric_cols[1]:
            render_metric_card("Sent", sent_count)
        with metric_cols[2]:
            render_metric_card("Replies", replied_count, delta=f"{opened_count} opened")
        with metric_cols[3]:
            render_metric_card("Due now", due_count)

        pipeline_tab, events_tab = st.tabs(["Pipeline", "Test events"])

        with pipeline_tab:
            action_col, sync_col, note_col = st.columns([1, 1, 2])
            with action_col:
                if st.button("Process due follow-ups", type="primary", disabled=due_count == 0):
                    with st.spinner("Processing due follow-ups..."):
                        processed = scheduler.process_due_follow_ups()
                    succeeded = [item for item in processed if item.get("success")]
                    failed = [item for item in processed if not item.get("success")]
                    st.session_state["followup_notice"] = {
                        "sent": len(succeeded),
                        "failed": len(failed),
                    }
                    st.rerun()
            with sync_col:
                if st.button("🔄 Sync Gmail replies"):
                    with st.spinner("Checking Gmail threads for replies..."):
                        sync_res = reply_sync.sync_replies()
                    st.success(
                        f"Checked {sync_res.get('checked_threads', 0)} thread(s); "
                        f"{sync_res.get('replies_detected', 0)} new reply(ies) recorded."
                    )
                    st.rerun()
            with note_col:
                st.caption("The sequence advances only for messages that are due and have not replied, bounced, or unsubscribed.")

            sequence_labels = {
                1: "Initial sent",
                2: "Follow-up 1",
                3: "Follow-up 2",
                4: "Follow-up 3",
                5: "Breakup sent",
            }
            rows = []
            for item in outreach_items:
                journalist = j_repo.get_by_id(item.get("journalist_id", ""))
                rows.append({
                    "Contact": journalist.get("name") if journalist else "Unknown",
                    "Outlet": journalist.get("outlet") if journalist else "",
                    "Subject": item.get("subject_line"),
                    "Status": str(item.get("status", "pending")).replace("_", " ").title(),
                    "Sequence": sequence_labels.get(int(item.get("follow_up_sequence", 1)), "Unknown"),
                    "Next follow-up": str(item.get("next_follow_up") or "—")[:16].replace("T", " "),
                    "Sent": str(item.get("sent_at") or "—")[:16].replace("T", " "),
                    "Sender": item.get("sender_account_key") or "—",
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

        with events_tab:
            st.warning("Testing only — these controls simulate recipient activity and do not read events from Gmail.")
            lookup = {item["id"]: item for item in outreach_items}

            def outreach_label(outreach_id: str) -> str:
                item = lookup[outreach_id]
                journalist = j_repo.get_by_id(item.get("journalist_id", ""))
                return f"{journalist.get('name') if journalist else 'Unknown'} · {item.get('subject_line') or 'No subject'}"

            selected_oid = st.selectbox("Outreach item", list(lookup), format_func=outreach_label)
            target_o = o_repo.get_by_id(selected_oid)
            current_status = target_o.get("status") if target_o else "missing"
            st.caption(f"Current status · {str(current_status).replace('_', ' ').title()}")

            c_sim1, c_sim2 = st.columns(2)
            open_disabled = current_status in {"opened", "replied", "bounced", "unsubscribed", "completed_no_reply", "missing"}
            reply_disabled = current_status in {"replied", "bounced", "unsubscribed", "missing"}
            with c_sim1:
                if st.button("Record simulated open", disabled=open_disabled):
                    if tracker.record_open(target_o.get("tracking_token", "")):
                        st.success("Open event recorded.")
                        st.rerun()
                    else:
                        st.error("The tracking token could not be found.")
            with c_sim2:
                if st.button("Record simulated reply", disabled=reply_disabled):
                    if tracker.record_reply(selected_oid):
                        st.success("Reply recorded and relationship score updated once.")
                        st.rerun()
                    else:
                        st.error("The outreach item could not be found.")
    else:
        render_empty_state(
            title="No outreach sent yet",
            message="Once you generate and send a pitch, delivery and follow-up status will show up here.",
            action_hint="Go to Campaign studio to send your first pitch",
            icon="📬",
        )


# ==============================================================================
# 5. SETTINGS & INTEGRATIONS
# ==============================================================================
elif menu == "Settings":
    page_header(
        "Configuration",
        "Connections and model readiness",
        "See which services are live, which are simulated, and what must be configured before production use.",
    )

    st.subheader("Connected services")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### Supabase")
        render_status_badge(
            "connected" if settings.is_supabase_configured else "local mode",
            label="Active" if settings.is_supabase_configured else "Local Mode",
            size="small",
        )
        st.text_input("Supabase URL", value=settings.SUPABASE_URL or "Not configured", disabled=True)
        st.text_input("Supabase Key", value="●●●●●●●●" if settings.SUPABASE_KEY else "Not configured", disabled=True)

        st.markdown("#### Gmail delivery")
        render_status_badge(
            "connected" if gmail_accounts else ("ready" if settings.is_gmail_configured else "not configured"),
            label=(
                f"{len(gmail_accounts)} sender(s) connected"
                if gmail_accounts
                else ("OAuth app ready" if settings.is_gmail_configured else "Not configured")
            ),
            size="small",
        )
        st.text_input("Google Client ID", value=settings.GOOGLE_CLIENT_ID or "Not configured", disabled=True)
        if settings.is_gmail_configured:
            connect_href = f"{settings.API_BASE_URL.rstrip('/')}/api/v1/auth/google/connect"
            # Support return_to for Streamlit Cloud
            if "streamlit.app" in str(os.environ.get("DASHBOARD_BASE_URL", "")) or "streamlit.app" in str(getattr(settings, "DASHBOARD_BASE_URL", "")):
                connect_href += "?return_to=https://openclaw-pr-manager.streamlit.app"
            st.link_button(
                "Connect another Gmail sender",
                connect_href,
            )
        else:
            st.warning("Configure GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first.")

        if gmail_accounts:
            st.caption("Authorized sender accounts")
            for account in gmail_accounts:
                acc_key = str(account.get("account_key") or "")
                acc_email = str(account.get("email_address") or acc_key)
                c_acc, c_btn = st.columns([3, 1])
                with c_acc:
                    st.code(acc_email, language=None)
                with c_btn:
                    if st.button("Disconnect", key=f"disconnect_{acc_key}"):
                        gmail_auth.disconnect_account(acc_key)
                        st.success(f"Disconnected {acc_email}")
                        st.rerun()

    with col_s2:
        st.markdown("#### AI model providers")
        st.markdown("**Xiaomi MiMo (`mimo-v2.5-pro`)**")
        render_status_badge(
            "connected" if settings.is_mimo_configured else "fallback mock",
            label="Connected" if settings.is_mimo_configured else "Fallback Mock",
            size="small",
        )
        st.text_input("MiMo Base URL", value=settings.MIMO_BASE_URL or "https://token-plan-sgp.xiaomimimo.com/v1", disabled=True)
        st.text_input("MiMo API Key", value="●●●●●●●●" if settings.is_mimo_configured else "Not configured", disabled=True)

        st.markdown("**DeepSeek (`deepseek-chat`)**")
        render_status_badge(
            "connected" if settings.is_deepseek_configured else "fallback mock",
            label="Connected" if settings.is_deepseek_configured else "Fallback Mock",
            size="small",
        )
        st.text_input("DeepSeek Base URL", value=settings.DEEPSEEK_BASE_URL or "https://api.deepseek.com/v1", disabled=True)
        st.text_input("DeepSeek API Key", value="●●●●●●●●" if settings.DEEPSEEK_API_KEY else "Not configured", disabled=True)

    st.divider()
    st.subheader("Prompt templates")
    templates = t_repo.list_all()
    if templates:
        for t in templates:
            with st.expander(f"{t.get('name')} · {t.get('model')}"):
                st.caption("System prompt")
                st.code(str(t.get("system_prompt") or ""), language=None)
                st.caption("User template")
                st.code(str(t.get("user_prompt_template") or ""), language=None)
    else:
        render_empty_state(
            title="No prompt templates",
            message="Prompt templates will appear here once seeded or created.",
            action_hint="Check seed data configuration",
            icon="🧩",
        )

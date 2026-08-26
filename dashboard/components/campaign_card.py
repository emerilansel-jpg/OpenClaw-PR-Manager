"""Accessible, visual-only campaign summary card."""

import html

import streamlit as st


def render_campaign_card(
    title: str,
    status: str = "planning",
    total_journalists: int = 0,
    sent_count: int = 0,
    opened_count: int = 0,
    replied_count: int = 0,
    start_date: str = None,
    end_date: str = None,
    on_action_click: callable = None,
    action_label: str = "View campaign",
) -> None:
    """Render a campaign summary; actions remain native Streamlit widgets."""
    del on_action_click  # Visual component only; callers render native buttons.

    safe_title = html.escape(str(title or "Untitled campaign"))
    safe_status = html.escape(str(status).replace("_", " ").title())
    safe_action = html.escape(str(action_label))
    safe_dates = ""
    if start_date and end_date:
        safe_dates = f"{html.escape(str(start_date))} — {html.escape(str(end_date))}"

    total = max(0, int(total_journalists or 0))
    sent = max(0, int(sent_count or 0))
    opened = max(0, int(opened_count or 0))
    replied = max(0, int(replied_count or 0))
    progress = min(100.0, sent / total * 100) if total else 0.0
    open_rate = opened / sent * 100 if sent else 0.0
    reply_rate = replied / sent * 100 if sent else 0.0

    palette = {
        "active": ("#2dd4bf", "rgba(45,212,191,.12)"),
        "completed": ("#86efac", "rgba(134,239,172,.12)"),
        "paused": ("#fbbf24", "rgba(251,191,36,.12)"),
        "draft": ("#a8b3c7", "rgba(168,179,199,.10)"),
        "cancelled": ("#fb7185", "rgba(251,113,133,.12)"),
    }
    accent, badge_bg = palette.get(str(status).lower(), palette["draft"])
    dates_html = f'<div class="ods-campaign-dates">{safe_dates}</div>' if safe_dates else ""

    st.html(
        f"""
        <article class="ods-campaign-card" aria-label="Campaign {safe_title}">
            <div class="ods-campaign-card-top">
                <div>
                    <div class="ods-campaign-status" style="color:{accent};background:{badge_bg};">{safe_status}</div>
                    <h3>{safe_title}</h3>
                    {dates_html}
                </div>
                <div class="ods-campaign-progress-number">{progress:.0f}%</div>
            </div>
            <div class="ods-campaign-progress-track" aria-label="Progress {progress:.0f}%">
                <div style="width:{progress:.1f}%;background:{accent};"></div>
            </div>
            <div class="ods-campaign-stats">
                <div><strong>{total}</strong><span>Targets</span></div>
                <div><strong>{sent}</strong><span>Sent</span></div>
                <div><strong>{open_rate:.0f}%</strong><span>Open rate</span></div>
                <div><strong>{reply_rate:.0f}%</strong><span>Reply rate</span></div>
            </div>
            <div class="ods-campaign-action-hint">{safe_action}</div>
        </article>
        """
    )

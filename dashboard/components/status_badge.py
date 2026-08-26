"""Status Badge Component.

Color-coded status indicators for outreach states, integration health, and
campaign status, following the Dark Space theme. All dynamic label text is
HTML-escaped.
"""

import html
from typing import Optional

import streamlit as st

_STATUS_COLORS = {
    # Outreach states
    "pending": {"dot": "#94A3B8", "bg": "rgba(148, 163, 184, 0.16)", "text": "#E2E8F0"},
    "draft": {"dot": "#94A3B8", "bg": "rgba(148, 163, 184, 0.16)", "text": "#E2E8F0"},
    "scheduled": {"dot": "#FBBF24", "bg": "rgba(251, 191, 36, 0.16)", "text": "#FDE68A"},
    "sent": {"dot": "#22D3EE", "bg": "rgba(34, 211, 238, 0.16)", "text": "#CFFAFE"},
    "opened": {"dot": "#34D399", "bg": "rgba(52, 211, 153, 0.16)", "text": "#D1FAE5"},
    "replied": {"dot": "#34D399", "bg": "rgba(52, 211, 153, 0.16)", "text": "#D1FAE5"},
    "bounced": {"dot": "#F87171", "bg": "rgba(248, 113, 113, 0.16)", "text": "#FEE2E2"},
    "completed_no_reply": {"dot": "#9CA3AF", "bg": "rgba(156, 163, 175, 0.16)", "text": "#E5E7EB"},
    # Integration states
    "active": {"dot": "#34D399", "bg": "rgba(52, 211, 153, 0.16)", "text": "#D1FAE5"},
    "inactive": {"dot": "#9CA3AF", "bg": "rgba(156, 163, 175, 0.16)", "text": "#E5E7EB"},
    "connected": {"dot": "#34D399", "bg": "rgba(52, 211, 153, 0.16)", "text": "#D1FAE5"},
    "disconnected": {"dot": "#F87171", "bg": "rgba(248, 113, 113, 0.16)", "text": "#FEE2E2"},
    "configuring": {"dot": "#FBBF24", "bg": "rgba(251, 191, 36, 0.16)", "text": "#FDE68A"},
    "local mode": {"dot": "#FBBF24", "bg": "rgba(251, 191, 36, 0.16)", "text": "#FDE68A"},
    "fallback mock": {"dot": "#FBBF24", "bg": "rgba(251, 191, 36, 0.16)", "text": "#FDE68A"},
    "simulated": {"dot": "#FBBF24", "bg": "rgba(251, 191, 36, 0.16)", "text": "#FDE68A"},
    # Campaign states
    "planning": {"dot": "#94A3B8", "bg": "rgba(148, 163, 184, 0.16)", "text": "#E2E8F0"},
    "active_campaign": {"dot": "#22D3EE", "bg": "rgba(34, 211, 238, 0.16)", "text": "#CFFAFE"},
    "paused": {"dot": "#FBBF24", "bg": "rgba(251, 191, 36, 0.16)", "text": "#FDE68A"},
    "completed": {"dot": "#34D399", "bg": "rgba(52, 211, 153, 0.16)", "text": "#D1FAE5"},
    "cancelled": {"dot": "#F87171", "bg": "rgba(248, 113, 113, 0.16)", "text": "#FEE2E2"},
}

_DEFAULT = {"dot": "#94A3B8", "bg": "rgba(148, 163, 184, 0.16)", "text": "#E2E8F0"}

_SIZES = {
    "small": {"dot_size": "8px", "gap": "6px", "font_size": "0.75rem", "padding": "3px 10px"},
    "medium": {"dot_size": "9px", "gap": "8px", "font_size": "0.8125rem", "padding": "4px 12px"},
    "large": {"dot_size": "11px", "gap": "10px", "font_size": "0.9375rem", "padding": "6px 14px"},
}


def render_status_badge(
    status: str,
    label: Optional[str] = None,
    size: str = "medium",
) -> None:
    """Render a status badge with an accessible color + text indicator.

    Color is never the sole indicator: the label text is always rendered.

    Args:
        status: Status identifier (e.g., "sent", "opened", "connected").
        label: Optional custom label; defaults to a title-cased status.
        size: One of "small", "medium", or "large".
    """
    config = _STATUS_COLORS.get(str(status).lower(), _DEFAULT)
    size_config = _SIZES.get(size, _SIZES["medium"])
    label_text = label if label is not None else str(status).replace("_", " ").title()
    safe_label = html.escape(str(label_text))
    safe_status = html.escape(str(status), quote=True)

    st.html(
        f"""
        <span
            class="ods-status-badge"
            data-status="{safe_status}"
            role="status"
            aria-label="Status: {safe_label}"
            style="
                display:inline-flex;align-items:center;gap:{size_config['gap']};
                padding:{size_config['padding']};
                background:{config['bg']};
                border:1px solid {config['dot']}44;
                border-radius:9999px;
                font-size:{size_config['font_size']};
                color:{config['text']};
                font-weight:600;
                letter-spacing:0.02em;
                white-space:nowrap;
            "
        >
            <span
                aria-hidden="true"
                style="
                    display:inline-block;
                    width:{size_config['dot_size']};height:{size_config['dot_size']};
                    background:{config['dot']};
                    border-radius:50%;
                    box-shadow:0 0 8px {config['dot']};
                "
            ></span>
            {safe_label}
        </span>
        """
    )

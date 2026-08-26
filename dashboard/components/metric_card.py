"""Metric Card Component.

Stats display with trend indicators for dashboard metrics, following the
Dark Space theme. Uses class-based CSS (defined in app.py) rather than
pseudo-element inline styles, which browsers ignore. All dynamic content
is HTML-escaped.
"""

import html
from typing import Optional, Union

import streamlit as st


def _delta_direction(delta: object) -> str:
    """Classify a delta value as positive, negative, or neutral."""
    if delta is None:
        return "neutral"
    text = str(delta).strip()
    if text.startswith("-") or text.startswith("▼"):
        return "negative"
    if text.startswith("+") or text.startswith("▲"):
        return "positive"
    # Try numeric interpretation for bare numbers like "12%" or "0.4"
    try:
        numeric = float(text.replace("%", "").replace(",", ""))
        if numeric < 0:
            return "negative"
        if numeric > 0:
            return "positive"
    except (TypeError, ValueError):
        pass
    return "neutral"


def render_metric_card(
    title: str,
    value: Union[str, int, float],
    delta: Optional[Union[str, int, float]] = None,
    delta_label: str = "",
    icon: Optional[str] = None,
    help_text: Optional[str] = None,
) -> None:
    """Render a metric card showing a stat with an optional trend indicator.

    Args:
        title: Card label (e.g., "Total Journalists").
        value: Main value displayed prominently.
        delta: Optional change indicator (e.g., "+12%", "-5%").
        delta_label: Label for the delta (e.g., "replies").
        icon: Optional emoji icon before the title.
        help_text: Optional tooltip text rendered as a title attribute.
    """
    safe_title = html.escape(str(title))
    safe_value = html.escape(str(value))
    safe_icon = html.escape(str(icon)) if icon else ""
    safe_help = html.escape(str(help_text), quote=True) if help_text else ""

    icon_html = (
        f'<span class="ods-metric-icon" aria-hidden="true">{safe_icon}</span>'
        if safe_icon
        else ""
    )
    help_html = (
        f'<span class="ods-metric-help" title="{safe_help}" aria-label="{safe_help}">ⓘ</span>'
        if safe_help
        else ""
    )

    delta_html = ""
    if delta is not None:
        direction = _delta_direction(delta)
        arrow = {"positive": "▲", "negative": "▼", "neutral": "●"}[direction]
        safe_delta = html.escape(str(delta))
        safe_delta_label = html.escape(str(delta_label))
        delta_html = (
            f'<div class="ods-metric-delta ods-metric-delta-{direction}">'
            f'<span aria-hidden="true">{arrow}</span> {safe_delta}'
            f'<span class="ods-metric-delta-label"> {safe_delta_label}</span>'
            f"</div>"
        )

    st.html(
        f"""
        <div class="ods-metric-card">
            <div class="ods-metric-header">
                {icon_html}
                <span class="ods-metric-title">{safe_title}</span>
                {help_html}
            </div>
            <div class="ods-metric-value">{safe_value}</div>
            {delta_html}
        </div>
        """
    )

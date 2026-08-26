"""Integration Status Component - Visual Only.

Renders a service connection status card without fake action buttons.
Use native Streamlit widgets for configure/connect/disconnect actions in app.py.
All dynamic text is HTML-escaped.
"""

import html

import streamlit as st


def render_integration_status(
    service_name: str,
    icon: str,
    is_configured: bool,
    is_connected: bool = None,
    last_check: str = None,
    error_message: str = None,
) -> None:
    """Render an integration status card (visual only).

    Args:
        service_name: Display name (e.g., "Supabase", "Gmail OAuth").
        icon: Emoji or icon (e.g., "🗄️", "📧").
        is_configured: Whether credentials are configured in .env.
        is_connected: Connection status (True/False), optional.
        last_check: Last check timestamp string.
        error_message: Optional error text to display.
    """
    safe_service = html.escape(str(service_name))
    safe_icon = html.escape(str(icon))
    safe_last = html.escape(str(last_check)) if last_check else ""
    safe_error = html.escape(str(error_message)) if error_message else ""

    has_error = bool(safe_error)

    # Determine state colors
    if has_error:
        border_color = "#F87171"
        bg_color = "rgba(248, 113, 113, 0.06)"
        status_label = "ERROR"
        status_icon = "⚠️"
    elif is_configured:
        if is_connected is True:
            border_color = "#34D399"
            bg_color = "rgba(52, 211, 153, 0.08)"
            status_label = "CONNECTED"
            status_icon = "✅"
        elif is_connected is False:
            border_color = "#F59E0B"
            bg_color = "rgba(245, 158, 11, 0.08)"
            status_label = "NOT CONNECTED"
            status_icon = "⏸️"
        else:
            border_color = "#34D399"
            bg_color = "rgba(52, 211, 153, 0.08)"
            status_label = "CONFIGURED"
            status_icon = "✓"
    else:
        border_color = "#94A3B8"
        bg_color = "rgba(148, 163, 184, 0.08)"
        status_label = "NOT CONFIGURED"
        status_icon = "❌"

    safe_border = html.escape(border_color)

    error_html = ""
    if has_error:
        error_html = (
            f'<div style="margin-top:12px;font-size:0.85rem;color:#FCA5A5;background:rgba(248,113,113,0.1);padding:12px;border-radius:12px;'
            f'border-left:3px solid {safe_border};">{safe_error}</div>'
        )

    last_check_html = ""
    if last_check:
        last_check_html = (
            f'<div style="margin-top:8px;font-size:0.75rem;color:#64748B;">Last checked: {safe_last}</div>'
        )

    st.html(
        f"""
        <div role="region" aria-label="{html.escape(str(service_name))} integration status"
             style="display:flex;align-items:center;gap:20px;background:{bg_color};backdrop-filter:blur(12px);border:1px solid {safe_border}44;border-radius:20px;padding:24px;box-shadow:0 8px 32px rgba(0,0,0,0.3);">
            <span style="font-size:2.5rem;filter:drop-shadow(0 0 12px {safe_border}44);">{safe_icon}</span>
            <div style="flex-grow:1;">
                <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                    <h3 style="margin:0;font-size:1.1rem;font-weight:700;color:#E2E8F0;">{safe_service}</h3>
                </div>
                <div style="display:inline-flex;align-items:center;gap:8px;padding:6px 12px;background:{safe_border}22;border:1px solid {safe_border}66;border-radius:9999px;font-size:0.8rem;color:{safe_border};font-weight:600;text-transform:uppercase;letter-spacing:0.05em;">
                    <span>{status_icon}</span><span>{status_label}</span>
                </div>
                {error_html}
                {last_check_html}
            </div>
        </div>
        """
    )

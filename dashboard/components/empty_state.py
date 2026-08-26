"""Empty State Component.

Engaging placeholder UI when no data exists. Follows the Dark Space theme
with an encouraging call-to-action hint. Never renders fake HTML buttons;
any action must be a native Streamlit widget rendered by the caller.
"""

import html

import streamlit as st


def render_empty_state(
    title: str,
    message: str = "There's nothing here yet.",
    action_hint: str = None,
    icon: str = "🛰️",
) -> None:
    """Render an attractive empty state with optional CTA hint text.

    Args:
        title: Main heading (e.g., "No journalists found").
        message: Descriptive text explaining the state.
        action_hint: Plain-text guidance for what to do next (no fake button).
        icon: Emoji icon to display.
    """
    safe_title = html.escape(str(title))
    safe_message = html.escape(str(message))
    safe_hint = html.escape(str(action_hint)) if action_hint else ""
    safe_icon = html.escape(str(icon))

    hint_html = (
        f'<div class="ods-empty-hint">{safe_hint}</div>' if safe_hint else ""
    )

    st.html(
        f"""
        <div class="ods-empty-state" role="status" aria-live="polite">
            <div class="ods-empty-icon" aria-hidden="true">{safe_icon}</div>
            <div class="ods-empty-title">{safe_title}</div>
            <div class="ods-empty-message">{safe_message}</div>
            {hint_html}
        </div>
        """
    )

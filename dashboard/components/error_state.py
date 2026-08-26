"""Error State Component.

Helpful error messages with recovery steps, following the Dark Space theme
with clear visual hierarchy. Never renders fake HTML buttons; any retry or
recovery action must be a native Streamlit widget rendered by the caller.
"""

import html
from typing import Iterable, Optional

import streamlit as st


def render_error_state(
    title: str = "Something went wrong",
    message: str = "We encountered an unexpected error.",
    recovery_steps: Optional[Iterable[str]] = None,
    icon: str = "⚠️",
) -> None:
    """Render an informative error state with recovery guidance.

    Args:
        title: Error heading.
        message: Descriptive error explanation.
        recovery_steps: Suggested actions the user can take.
        icon: Emoji icon for visual emphasis.
    """
    safe_title = html.escape(str(title))
    safe_message = html.escape(str(message))
    safe_icon = html.escape(str(icon))

    steps_html = ""
    steps = [html.escape(str(s)) for s in (recovery_steps or []) if str(s).strip()]
    if steps:
        items = "".join(f"<li>{s}</li>" for s in steps)
        steps_html = (
            '<div class="ods-error-steps">'
            '<div class="ods-error-steps-title">Suggested actions</div>'
            f"<ul>{items}</ul>"
            "</div>"
        )

    st.html(
        f"""
        <div class="ods-error-state" role="alert">
            <div class="ods-error-icon" aria-hidden="true">{safe_icon}</div>
            <div class="ods-error-title">{safe_title}</div>
            <div class="ods-error-message">{safe_message}</div>
            {steps_html}
        </div>
        """
    )

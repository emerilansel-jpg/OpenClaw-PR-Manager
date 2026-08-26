"""Loading Spinner Component.

Animated spinner and skeleton placeholders for async operations, following
the Dark Space theme with neon glow effects. All dynamic text is escaped.
"""

import html

import streamlit as st


def render_loading_spinner(message: str = "Loading...", size: str = "medium") -> None:
    """Render a loading spinner with a message.

    Args:
        message: Text displayed below the spinner.
        size: One of "small", "medium", or "large".
    """
    sizes = {
        "small": {"size": "24px", "border_width": "3px"},
        "medium": {"size": "40px", "border_width": "4px"},
        "large": {"size": "60px", "border_width": "5px"},
    }
    config = sizes.get(size, sizes["medium"])
    safe_message = html.escape(str(message))

    st.html(
        f"""
        <div class="ods-spinner-wrap" role="status" aria-live="polite">
            <div
                class="ods-spinner"
                style="width:{config['size']};height:{config['size']};border-width:{config['border_width']};"
                aria-hidden="true"
            ></div>
            <span class="ods-spinner-message">{safe_message}</span>
        </div>
        """
    )


def render_skeleton_card(width: str = "100%", height: str = "200px") -> None:
    """Render a skeleton loading placeholder with a pulsing animation."""
    safe_width = html.escape(str(width), quote=True)
    safe_height = html.escape(str(height), quote=True)

    st.html(
        f"""
        <div
            class="ods-skeleton"
            style="width:{safe_width};height:{safe_height};"
            role="status"
            aria-label="Loading content"
        ></div>
        """
    )

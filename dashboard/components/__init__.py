"""Dashboard components for the OpenClaw PR Manager Dark Space theme.

All components render visual-only UI with HTML-escaped dynamic content.
Actions (buttons, callbacks) must use native Streamlit widgets in app.py.

Both plain function names (render_*) and legacy class-style aliases are
exported so existing imports keep working.
"""

from .status_badge import render_status_badge
from .metric_card import render_metric_card
from .loading_spinner import render_loading_spinner, render_skeleton_card
from .empty_state import render_empty_state
from .error_state import render_error_state
from .journalist_card import render_journalist_card
from .integration_status import render_integration_status
from .campaign_card import render_campaign_card

# Legacy class-style aliases (kept for backward compatibility).
StatusBadge = render_status_badge
MetricCard = render_metric_card
LoadingSpinner = render_loading_spinner
EmptyState = render_empty_state
ErrorState = render_error_state
JournalistCard = render_journalist_card
IntegrationStatus = render_integration_status
CampaignCard = render_campaign_card

__all__ = [
    "render_status_badge",
    "render_metric_card",
    "render_loading_spinner",
    "render_skeleton_card",
    "render_empty_state",
    "render_error_state",
    "render_journalist_card",
    "render_integration_status",
    "render_campaign_card",
    "StatusBadge",
    "MetricCard",
    "LoadingSpinner",
    "EmptyState",
    "ErrorState",
    "JournalistCard",
    "IntegrationStatus",
    "CampaignCard",
]

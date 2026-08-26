"""Regression checks for the Streamlit HTML rendering boundary."""

from pathlib import Path
from unittest.mock import patch

from dashboard.components.metric_card import render_metric_card
from dashboard.components.status_badge import render_status_badge


def test_dashboard_does_not_use_unsafe_markdown_for_html_fragments():
    dashboard_root = Path(__file__).parents[1] / "dashboard"
    for source in dashboard_root.rglob("*.py"):
        assert "unsafe_allow_html" not in source.read_text(encoding="utf-8"), source


def test_html_components_use_streamlit_html_renderer():
    with patch("dashboard.components.metric_card.st.html") as metric_html:
        render_metric_card("Replies", 12, delta="+2")
        markup = metric_html.call_args.args[0]
        assert 'class="ods-metric-card"' in markup

    with patch("dashboard.components.status_badge.st.html") as badge_html:
        render_status_badge("connected", label="Active")
        markup = badge_html.call_args.args[0]
        assert 'class="ods-status-badge"' in markup

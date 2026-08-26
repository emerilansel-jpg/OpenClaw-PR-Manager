"""Journalist Card Component - Visual Only.

Renders a journalist card showing name, outlet, beats, email, and 4D score.
No fake HTML buttons are included; all actions must be native Streamlit widgets.
All dynamic content is HTML-escaped.
"""

import html

import streamlit as st


def render_journalist_card(
    name: str,
    outlet: str,
    email: str = None,
    beat: list = None,
    score: float = None,
) -> None:
    """Render a journalist information card.

    Args:
        name: Journalist full name.
        outlet: Media outlet/publication name.
        email: Email address (optional).
        beat: List of beats/coverage areas.
        score: Overall 4D score (0-100).
    """
    safe_name = html.escape(str(name))
    safe_outlet = html.escape(str(outlet))
    safe_email = html.escape(str(email)) if email else ""
    safe_score_label = ""
    safe_score_value = ""

    # Score badge
    if score is not None:
        if score >= 80:
            color = "#34D399"
            label_text = "High Match"
        elif score >= 60:
            color = "#FBBF24"
            label_text = "Good Match"
        elif score >= 40:
            color = "#F59E0B"
            label_text = "Moderate"
        else:
            color = "#EF4444"
            label_text = "Low Match"
        safe_color = html.escape(color)
        safe_score_value = f"{score:.1f}"
        safe_score_label = html.escape(label_text)
        score_badge_html = (
            f'<div style="position:absolute;top:12px;right:12px;'
            f'background:{safe_color}22;border:1px solid {safe_color}66;'
            f'border-radius:20px;padding:6px 12px;font-size:0.7rem;'
            f'font-weight:700;color:{safe_color};box-shadow:0 2px 12px {safe_color}33;">'
            f'{safe_score_value} • {safe_score_label}</div>'
        )
    else:
        score_badge_html = ""

    # Avatar initials
    initials = "".join([n[0] for n in safe_name.split() if n]).upper()[:2]
    avatar_html = (
        '<div style="width:48px;height:48px;border-radius:50%;'
        'background:linear-gradient(135deg,#22D3EE 0%,#6366F1 100%);'
        'display:flex;align-items:center;justify-content:center;'
        'font-weight:700;font-size:1.2rem;color:#0A0E27;"'
        f'>{initials}</div>'
    )

    # Beats tags
    beats_html = ""
    if beat and len(beat) > 0:
        tags = []
        for b in beat[:5]:
            safe_b = html.escape(str(b))
            tags.append(
                f'<span style="display:inline-block;padding:3px 10px;background:rgba(34,211,238,0.1)'
                f';border:1px solid rgba(34,211,238,0.2);border-radius:12px;font-size:0.7rem;color:#22D3EE;margin-right:6px;margin-bottom:6px;">'
                f"{safe_b}</span>"
            )
        beats_html = ''.join(tags)

    # Email link
    email_html = ""
    if email:
        email_html = (
            f'<a href="mailto:{html.escape(safe_email)}" '
            f'style="font-size:0.85rem;color:#E2E8F0;text-decoration:none;">'
            f'{safe_email}</a>'
        )

    st.html(
        f"""
        <div role="region" aria-label="{html.escape(str(name))} card"
             style="display:flex;gap:20px;background:rgba(13,21,38,0.8);backdrop-filter:blur(12px);border:1px solid rgba(34,48,77,0.4);border-radius:20px;padding:20px;box-shadow:0 8px 32px rgba(0,0,0,0.4);position:relative;">
            {score_badge_html}
            <div style="flex-shrink:0;">{avatar_html}</div>
            <div style="flex-grow:1;">
                <h3 style="margin:0 0 6px 0;font-size:1.1rem;font-weight:700;color:#E2E8F0;line-height:1.3;">{safe_name}</h3>
                <div style="font-size:0.9rem;color:#22D3EE;font-weight:500;margin-bottom:12px;display:flex;align-items:center;gap:6px;"><span>✦</span><span>{safe_outlet}</span></div>
                {'<div style="margin-top:12px;"><div style="font-size:0.7rem;color:#64748B;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;">Beats</div>' + beats_html + '</div>' if beats_html else ''}
                {'<div style="margin-top:12px;"><div style="font-size:0.7rem;color:#64748B;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;">Email</div>' + email_html + '</div>' if email_html else ''}
            </div>
        </div>
        """
    )

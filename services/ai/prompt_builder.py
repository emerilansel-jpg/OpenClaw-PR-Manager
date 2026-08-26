"""Prompt template renderer for AI PR pitches."""
from typing import Dict, Any
from jinja2 import Template


class PromptBuilder:
    """Renders dynamic variables inside system and user prompt templates."""

    @classmethod
    def render(cls, template_str: str, context: Dict[str, Any]) -> str:
        """Render variables in template string."""
        if not template_str:
            return ""

        # Normalize context lists to comma-separated strings
        formatted_context = {}
        for k, v in context.items():
            if isinstance(v, list):
                formatted_context[k] = ", ".join(str(i) for i in v)
            elif v is None:
                formatted_context[k] = ""
            else:
                formatted_context[k] = str(v)

        try:
            jinja_template = Template(template_str)
            return jinja_template.render(**formatted_context)
        except Exception:
            # Fallback simple replacement
            result = template_str
            for k, v in formatted_context.items():
                result = result.replace(f"{{{{{k}}}}}", str(v))
            return result

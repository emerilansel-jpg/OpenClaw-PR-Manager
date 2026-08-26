"""Templates repository for managing AI prompt templates."""
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from db.supabase_client import get_supabase_client

DEFAULT_TEMPLATES = [
    {
        "id": "default-mimo-initial",
        "name": "Standard PR Pitch (Xiaomi MiMo)",
        "model": "mimo-v2.5-pro",
        "pitch_type": "initial",
        "system_prompt": (
            "You are an elite, concise Public Relations and Communications Strategist. "
            "Write highly personalized, punchy, and compelling email pitches to journalists. "
            "Never sound like generic spam. Lead with a newsworthy hook, connect with their recent work or beat, "
            "and end with a clear, low-friction call-to-action (e.g. exclusive quote, embargoed press kit, or quick 5-min interview)."
        ),
        "user_prompt_template": (
            "Journalist Name: {{journalist_name}}\n"
            "Outlet: {{outlet}}\n"
            "Beat/Topics: {{beat}}\n"
            "Recent Articles/Bio: {{bio}}\n\n"
            "Story/Press Release Content:\n{{story}}\n\n"
            "Please generate:\n"
            "1. A catchy, high-open-rate Subject Line (no emojis, professional yet intriguing)\n"
            "2. A concise 3-4 paragraph pitch email tailored specifically to this journalist."
        ),
        "is_default": True,
    },
    {
        "id": "default-deepseek-initial",
        "name": "Fast Direct Pitch (DeepSeek)",
        "model": "deepseek-chat",
        "pitch_type": "initial",
        "system_prompt": (
            "You are a direct, impactful PR outreach assistant. Your goal is to write short, highly relevant "
            "email pitches directly addressing why the story matters to the journalist's readers today."
        ),
        "user_prompt_template": (
            "Journalist: {{journalist_name}} at {{outlet}} (Beat: {{beat}})\n"
            "Story: {{story}}\n\n"
            "Draft a sharp pitch under 150 words with a compelling subject line."
        ),
        "is_default": True,
    },
    {
        "id": "default-followup-1",
        "name": "Quick Bump Follow-up (Day 3)",
        "model": "mimo-v2.5-pro",
        "pitch_type": "followup_1",
        "system_prompt": (
            "You are follow-up specialist. Write a polite, ultra-brief 2-sentence follow-up referencing the previous pitch "
            "adding one fresh data point or angle."
        ),
        "user_prompt_template": (
            "Journalist: {{journalist_name}}\n"
            "Original Subject: {{subject_line}}\n"
            "Original Pitch: {{pitch_email}}\n"
            "Story Context: {{story}}\n\n"
            "Write a brief reply-in-thread email."
        ),
        "is_default": True,
    },
    {
        "id": "default-followup-3",
        "name": "Alternative Angle Follow-up (Day 17)",
        "model": "mimo-v2.5-pro",
        "pitch_type": "followup_3",
        "system_prompt": (
            "Write a concise follow-up that offers one genuinely different angle, useful data point, "
            "or expert source. Do not repeat the original pitch and do not manufacture facts."
        ),
        "user_prompt_template": (
            "Journalist: {{journalist_name}} at {{outlet}}\n"
            "Original Subject: {{subject_line}}\n"
            "Story Context: {{story}}\n\n"
            "Write a brief reply-in-thread email with an alternative editorial angle."
        ),
        "is_default": True,
    },
    {
        "id": "default-breakup",
        "name": "Polite Breakup / Final Notice (Day 31)",
        "model": "mimo-v2.5-pro",
        "pitch_type": "breakup",
        "system_prompt": (
            "Write a polite, no-pressure final follow-up letting the journalist know we are moving on "
            "while leaving the door open for future relevant stories."
        ),
        "user_prompt_template": (
            "Journalist: {{journalist_name}}\n"
            "Original Subject: {{subject_line}}\n\n"
            "Write a very brief (2-3 sentences) breakup note."
        ),
        "is_default": True,
    }
]


class TemplatesRepository:
    """Repository for AI prompt templates."""

    _local_store: Dict[str, Dict[str, Any]] = {t["id"]: t for t in DEFAULT_TEMPLATES}

    def __init__(self):
        self.client = get_supabase_client()

    def list_all(self) -> List[Dict[str, Any]]:
        """List all prompt templates."""
        if self.client:
            try:
                res = self.client.table("prompt_templates").select("*").execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        return list(self._local_store.values())

    def get_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get template by ID."""
        if self.client:
            try:
                res = self.client.table("prompt_templates").select("*").eq("id", template_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        return self._local_store.get(template_id)

    def get_default(self, pitch_type: str = "initial", model: str = "gpt-4o") -> Dict[str, Any]:
        """Get default template for given pitch type and model."""
        templates = self.list_all()
        for t in templates:
            if t.get("pitch_type") == pitch_type and t.get("model") == model:
                return t
        for t in templates:
            if t.get("pitch_type") == pitch_type and t.get("is_default"):
                return t
        return DEFAULT_TEMPLATES[0]

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom template."""
        tid = data.get("id") or str(uuid.uuid4())
        record = {
            "id": tid,
            "name": data.get("name", "Custom Template"),
            "model": data.get("model", "gpt-4o"),
            "pitch_type": data.get("pitch_type", "initial"),
            "system_prompt": data.get("system_prompt", ""),
            "user_prompt_template": data.get("user_prompt_template", ""),
            "is_default": data.get("is_default", False),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.client:
            try:
                res = self.client.table("prompt_templates").insert(record).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass

        self._local_store[tid] = record
        return record

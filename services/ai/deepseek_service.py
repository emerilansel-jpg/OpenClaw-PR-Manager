"""DeepSeek Service for Cost-Effective Bulk Pitch Generation."""
import logging
from typing import Dict, Any, Optional
from openai import OpenAI
from config.settings import get_settings

logger = logging.getLogger(__name__)


class DeepSeekService:
    """Client for DeepSeek-Chat API (using OpenAI-compatible SDK)."""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.DEEPSEEK_MODEL

        self._client = None
        if self.api_key:
            try:
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                logger.error("Failed to initialize DeepSeek client: %s", e)

    def generate_pitch(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7
    ) -> Dict[str, str]:
        """Generate pitch via DeepSeek-Chat."""
        if self._client:
            try:
                res = self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                )
                raw_text = res.choices[0].message.content or ""
                return self._parse_generated_pitch(raw_text)
            except Exception as e:
                logger.error("DeepSeek chat completion failed: %s", e)

        # Fallback output
        return {
            "subject_line": "Quick Pitch: New Milestone in Tech & Innovation",
            "pitch_email": (
                "Hi there,\n\n"
                "Reaching out with a quick, relevant update regarding recent industry developments:\n\n"
                f"{user_prompt[:250]}...\n\n"
                "Let me know if you'd like the full press release and interview details.\n\n"
                "Best,\nMedia Relations"
            )
        }

    @staticmethod
    def _parse_generated_pitch(raw_text: str) -> Dict[str, str]:
        """Extract subject line and pitch body."""
        lines = raw_text.strip().split("\n")
        subject = "Relevant Story Pitch"
        body_lines = []

        for line in lines:
            clean_line = line.strip()
            if clean_line.lower().startswith(("subject:", "subject line:")):
                subject = clean_line.split(":", 1)[1].strip().strip('"').strip("'")
            elif clean_line.lower().startswith(("1. subject:", "1. subject line:")):
                subject = clean_line.split(":", 1)[1].strip().strip('"').strip("'")
            else:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()
        if not body:
            body = raw_text.strip()

        return {
            "subject_line": subject,
            "pitch_email": body
        }

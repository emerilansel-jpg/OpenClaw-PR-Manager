"""OpenAI Service for Embeddings and GPT-4o Pitch Generation."""
import logging
import math
import random
from typing import List, Dict, Any, Optional
from openai import OpenAI, AsyncOpenAI
from config.settings import get_settings

logger = logging.getLogger(__name__)


class OpenAIService:
    """Client for OpenAI GPT and text-embedding models."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL
        
        if self.api_key:
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self._client = OpenAI(**client_kwargs)
        else:
            self._client = None

    def generate_embedding(self, text: str) -> List[float]:
        """Generate 1536-dimensional vector embedding for text."""
        if not text:
            return [0.0] * 1536

        if self._client:
            try:
                res = self._client.embeddings.create(
                    model=self.embedding_model,
                    input=text.strip()
                )
                return res.data[0].embedding
            except Exception as e:
                logger.error("OpenAI embedding generation failed: %s", e)

        # Deterministic pseudo-embedding fallback for offline/local testing
        seed = sum(ord(c) for c in text)
        random.seed(seed)
        vec = [random.gauss(0, 1) for _ in range(1536)]
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec]

    def generate_pitch(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7
    ) -> Dict[str, str]:
        """Generate subject line and pitch body via GPT-4o."""
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
                logger.error("OpenAI chat completion failed: %s", e)

        # Fallback template output
        return {
            "subject_line": "Exclusive Story: Breakthrough Innovation & Industry Impact",
            "pitch_email": (
                "Hi there,\n\n"
                "I have been following your insightful reporting and wanted to share an exclusive story "
                "that directly aligns with your beat.\n\n"
                f"{user_prompt[:300]}...\n\n"
                "Would you be open to an exclusive look or a quick 5-minute chat with our leadership this week?\n\n"
                "Best regards,\nPR Team"
            )
        }

    @staticmethod
    def _parse_generated_pitch(raw_text: str) -> Dict[str, str]:
        """Extract subject line and pitch body from model output."""
        lines = raw_text.strip().split("\n")
        subject = "Exclusive Story Pitch"
        body_lines = []

        for i, line in enumerate(lines):
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

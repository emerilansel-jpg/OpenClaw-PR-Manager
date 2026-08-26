from typing import Dict, Any, Optional, List
from services.ai.mimo_service import XiaomiMiMoService
from services.ai.openai_service import OpenAIService
from services.ai.deepseek_service import DeepSeekService
from services.ai.prompt_builder import PromptBuilder
from db.repositories.templates_repo import TemplatesRepository


class AIPitchOrchestrator:
    """Coordinates multi-model AI pitch generation (Xiaomi MiMo & DeepSeek)."""

    def __init__(
        self,
        mimo_service: Optional[XiaomiMiMoService] = None,
        deepseek_service: Optional[DeepSeekService] = None,
        templates_repo: Optional[TemplatesRepository] = None,
        openai_service: Optional[OpenAIService] = None,
    ):
        self.openai = openai_service or mimo_service or XiaomiMiMoService()
        self.mimo = mimo_service or self.openai
        self.deepseek = deepseek_service or DeepSeekService()
        self.templates_repo = templates_repo or TemplatesRepository()

    def generate_pitch(
        self,
        journalist: Dict[str, Any],
        campaign: Dict[str, Any],
        model: str = "mimo-v2.5-pro",
        pitch_type: str = "initial",
        custom_template_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generate personalized pitch email."""
        if custom_template_id:
            tpl = self.templates_repo.get_by_id(custom_template_id)
        else:
            tpl = self.templates_repo.get_default(pitch_type=pitch_type, model=model)

        system_prompt = tpl.get("system_prompt", "")
        user_template = tpl.get("user_prompt_template", "")

        context = {
            "journalist_name": journalist.get("name", "Journalist"),
            "outlet": journalist.get("outlet", "News Outlet"),
            "beat": journalist.get("beat", []),
            "bio": journalist.get("bio", ""),
            "story": campaign.get("story", ""),
            "campaign_name": campaign.get("name", ""),
            "subject_line": journalist.get("subject_line", ""),
            "pitch_email": journalist.get("pitch_email", ""),
        }

        rendered_system = PromptBuilder.render(system_prompt, context)
        rendered_user = PromptBuilder.render(user_template, context)

        if "deepseek" in model.lower():
            result = self.deepseek.generate_pitch(rendered_system, rendered_user)
        elif "mimo" in model.lower():
            result = self.mimo.generate_pitch(rendered_system, rendered_user)
        else:
            result = self.openai.generate_pitch(rendered_system, rendered_user)

        return {
            "journalist_id": journalist.get("id"),
            "journalist_name": journalist.get("name"),
            "email": journalist.get("email"),
            "outlet": journalist.get("outlet"),
            "subject_line": result.get("subject_line", "Story Pitch"),
            "pitch_email": result.get("pitch_email", ""),
            "model_used": model,
            "pitch_type": pitch_type,
        }

    def generate_bulk_pitches(
        self,
        journalists: List[Dict[str, Any]],
        campaign: Dict[str, Any],
        model: str = "deepseek-chat",
    ) -> List[Dict[str, str]]:
        """Generate personalized pitches for a list of journalists."""
        results = []
        for j in journalists:
            res = self.generate_pitch(j, campaign, model=model)
            results.append(res)
        return results

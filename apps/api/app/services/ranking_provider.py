from app.core.config import get_settings
from app.services.gemini_ranking import GeminiRankingService
from app.services.openai_ranking import OpenAIRankingService
from app.services.ranking import AIRankingService


class UnsupportedRankingProviderError(ValueError):
    """Raised when the configured AI ranking provider is not supported."""


def get_ranking_service() -> AIRankingService:
    provider = get_settings().ai_ranking_provider.strip().lower()
    if provider == "gemini":
        return GeminiRankingService()
    if provider == "openai":
        return OpenAIRankingService()
    raise UnsupportedRankingProviderError(
        f"Unsupported AI ranking provider: {provider or '<empty>'}"
    )
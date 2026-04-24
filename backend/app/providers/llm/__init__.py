from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini import GeminiProvider


class NoopLLMProvider:
	async def complete_json(self, prompt: str) -> dict:
		return {}


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
	if settings.gemini_api_key:
		return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
	return NoopLLMProvider()


from typing import Protocol


class LLMProvider(Protocol):
    async def complete_json(self, prompt: str) -> dict: ...

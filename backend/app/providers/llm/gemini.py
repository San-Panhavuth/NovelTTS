from __future__ import annotations

import asyncio
import json
import re
from typing import Any


def _extract_json(raw_text: str) -> dict[str, Any]:
    stripped = raw_text.strip()
    if not stripped:
        return {}

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", stripped)
        if not match:
            return {}
        payload = json.loads(match.group(0))

    if isinstance(payload, dict):
        return payload
    if isinstance(payload, list):
        return {"items": payload}
    return {}


class GeminiProvider:
    def __init__(self, api_key: str, model_name: str) -> None:
        try:
            import google.generativeai as genai
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("google-generativeai is not installed") from exc

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model_name=model_name)

    async def complete_json(self, prompt: str) -> dict:
        def _invoke() -> str:
            response = self._model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"},
            )
            return getattr(response, "text", "") or ""

        raw_text = await asyncio.to_thread(_invoke)
        return _extract_json(raw_text)

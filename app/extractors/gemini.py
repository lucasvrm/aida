from __future__ import annotations

import json
from typing import Any, Type

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import settings
from app.core.errors import UpstreamError

class GeminiClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def generate_structured(self, prompt: str, schema_model: Type[BaseModel]) -> dict[str, Any]:
        schema = schema_model.model_json_schema()
        cfg = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_json_schema=schema,
        )
        try:
            resp = self.client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=cfg,
            )
        except Exception as e:
            raise UpstreamError("Falha ao chamar Gemini.", details=str(e))

        raw = getattr(resp, "text", None) or ""
        raw = raw.strip()
        if not raw:
            try:
                raw = resp.candidates[0].content.parts[0].text.strip()  # type: ignore
            except Exception:
                raw = ""

        if not raw:
            raise UpstreamError("Gemini retornou vazio.", details={"model": settings.GEMINI_MODEL})

        try:
            data = json.loads(raw)
        except Exception as e:
            raise UpstreamError("Gemini retornou JSON inválido.", details={"err": str(e), "raw": raw[:1200]})

        try:
            obj = schema_model.model_validate(data)
        except Exception as e:
            raise UpstreamError("Gemini retornou payload fora do schema.", details=str(e))

        return obj.model_dump()

from __future__ import annotations

import io
import pdfplumber
from app.extractors.base import ExtractResult

def extract_pdf_text(content: bytes) -> ExtractResult:
    warnings: list[str] = []
    text_parts: list[str] = []

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            try:
                t = page.extract_text() or ""
            except Exception:
                t = ""
            if t.strip():
                text_parts.append(t)

    full = "\n".join(text_parts).strip()
    if not full:
        warnings.append("PDF sem texto extraível (provável scan/imagem).")
    return ExtractResult(payload={"text": full}, warnings=warnings)

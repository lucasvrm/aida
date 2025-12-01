"""Hook futuro para OCR.

Hoje: TODO.
Ideia: plugar Tesseract / Vision / Textract / etc.
"""
from __future__ import annotations
from app.core.errors import ExtractionError

def ocr_pdf_or_images(_content: bytes) -> str:
    raise ExtractionError(
        "OCR não implementado.",
        details={"todo": "Integrar OCR e reprocessar PDF scan."},
    )

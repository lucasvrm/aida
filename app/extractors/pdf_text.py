from __future__ import annotations

import io
import pdfplumber
from app.extractors.base import ExtractResult
# Importamos a função de OCR que acabamos de criar
from app.extractors.pdf_ocr_stub import ocr_pdf_or_images

def extract_pdf_text(content: bytes) -> ExtractResult:
    warnings: list[str] = []
    text_parts: list[str] = []

    # 1. Tenta extração nativa (rápida, para PDFs de texto digital)
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                try:
                    t = page.extract_text() or ""
                except Exception:
                    t = ""
                if t.strip():
                    text_parts.append(t)
    except Exception:
        # Se pdfplumber falhar miseravelmente, apenas ignoramos e tentamos OCR abaixo
        pass

    full_text = "\n".join(text_parts).strip()

    # 2. Heurística: Se tiver muito pouco texto (< 50 chars), assumimos que é Scan/Imagem
    if len(full_text) < 50:
        try:
            # Tenta OCR
            ocr_text = ocr_pdf_or_images(content)
            
            # Se o OCR trouxe mais conteúdo que a extração nativa, usamos ele
            if len(ocr_text) > len(full_text):
                full_text = ocr_text
                warnings.append("Texto extraído via OCR (PDF era imagem/scan).")
            else:
                warnings.append("OCR rodou mas não encontrou texto legível.")
                
        except Exception as e:
            warnings.append(f"Falha ao tentar OCR de fallback: {str(e)}")

    if not full_text:
        warnings.append("Documento vazio ou ilegível mesmo após OCR.")

    return ExtractResult(payload={"text": full_text}, warnings=warnings)
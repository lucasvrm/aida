from __future__ import annotations
import pytesseract
from pdf2image import convert_from_bytes
from app.core.errors import ExtractionError

def ocr_pdf_or_images(content: bytes) -> str:
    """
    Converte PDF (bytes) em imagens e executa OCR (Tesseract) em cada página.
    Retorna o texto consolidado.
    """
    try:
        # Converte PDF em lista de imagens (PIL Images)
        # fmt="jpeg" geralmente é mais rápido que ppm padrão
        images = convert_from_bytes(content, fmt="jpeg")
        
        extracted_text = []
        
        for i, img in enumerate(images):
            # lang='por' usa o pacote tesseract-ocr-por instalado no Dockerfile
            text = pytesseract.image_to_string(img, lang='por')
            if text.strip():
                extracted_text.append(f"--- PÁGINA {i+1} (OCR) ---\n{text}")
        
        full_text = "\n".join(extracted_text)
        return full_text.strip()

    except Exception as e:
        # Se falhar (ex: arquivo corrompido, falta de memória), lançamos erro específico
        raise ExtractionError(
            "Falha ao realizar OCR no documento.",
            details={"error": str(e)}
        )
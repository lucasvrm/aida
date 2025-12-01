FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: 
# - build-essential/curl: padrão
# - tesseract-ocr + tesseract-ocr-por: engine de OCR e idioma PT-BR
# - poppler-utils: necessário para converter PDF em imagem (pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-por \
    poppler-utils \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT
ENV PORT=8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
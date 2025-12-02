# AIDA (FastAPI + Supabase + Gemini)

Microserviço Python (Render) para:
1) baixar docs do Supabase Storage,
2) extrair/normalizar (heurística + Gemini com output estruturado),
3) consolidar payload canônico KOA,
4) gerar XLSX final a partir do template,
5) subir no bucket de saída e devolver signed URL.

## Setup local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edite .env com SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, INTERNAL_API_TOKEN ...
```

Suba a API:
```bash
uvicorn app.main:app --reload --port 8000
```

Healthcheck:
```bash
curl http://localhost:8000/health
```

## Deploy no Render

Opção A (Docker):
- Crie um Render Web Service apontando para este repo
- Setar env vars (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY, INTERNAL_API_TOKEN)
- Health Check Path: `/health`

Opção B (Start Command):
- Build: `pip install -r requirements.txt`
- Start:
```bash
gunicorn -c gunicorn.conf.py app.main:app
```

## Banco (Supabase) - migrations

Execute o SQL:
- `sql/001_init.sql`

## API (contrato)

### POST /v1/jobs
Auth: `Authorization: Bearer INTERNAL_API_TOKEN`

Exemplo:
```bash
curl -X POST "http://localhost:8000/v1/jobs"   -H "Authorization: Bearer change-me-please"   -H "Content-Type: application/json"   -d '{
    "project_name": "Projeto Exemplo",
    "documents": [
      {
        "doc_type": "RECEBIVEIS",
        "storage_bucket": "koa-uploads",
        "storage_path": "projects/demo/recebiveis.xlsx",
        "original_filename": "recebiveis.xlsx",
        "notes": "export do ERP"
      }
    ]
  }'
```

## Nota importante sobre o template.xlsx
Este repositório inclui um `resources/template.xlsx` *mínimo* (skeleton) só para o pipeline e testes rodarem.
Troque pelo template KOA real assim que possível — o spec de KV (`resources/kv_spec.json`) é gerado automaticamente
a partir da aba **Geral**.

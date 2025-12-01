from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.errors import BadRequest, Conflict, NotFound, ExtractionError
from app.core.utils import safe_filename
from app.extractors.pdf_text import extract_pdf_text
from app.extractors.tabular import extract_tabular
from app.extractors.gemini import GeminiClient
from app.models.enums import DocType
from app.models.payload import ConsolidatedPayload
from app.models.schemas import (
    CreateJobRequest,
    CreateJobResponse,
    JobStatusResponse,
    JobDocProgress,
    ProjectResponse,
    OutputUrlResponse,
    PdfExtractionResponse,
)
from app.services.consolidation import consolidate
from app.supabase.db import DB
from app.supabase.storage import Storage
from app.template.writer import write_filled_xlsx

class JobService:
    def __init__(self):
        self.db = DB()
        self.storage = Storage()

    async def create_job(self, req: CreateJobRequest) -> CreateJobResponse:
        if req.project_id:
            project = self.db.get_project(req.project_id)
            if not project:
                raise NotFound("project_id não existe.")
            project_id = req.project_id
        else:
            project = self.db.create_project(req.project_name or "Sem nome")
            project_id = project["id"]

        self.db.update_project(project_id, {"status": "processing"})

        job = self.db.create_job(project_id)
        job_id = job["id"]
        self.db.append_job_log(job_id, _evt("info", "job_created", {"project_id": project_id}))

        for d in req.documents:
            doc = self.db.create_document(project_id, d.doc_type.value, d.storage_path, d.original_filename)
            self.db.update_document(doc["id"], {"status": "queued"})

        self.db.update_job(job_id, {"status": "processing"})
        return CreateJobResponse(job_id=job_id, project_id=project_id, status="processing")

    async def kickoff_job(self, job_id: str) -> None:
        asyncio.create_task(run_in_threadpool(self._process_job_sync, job_id))

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        job = self.db.get_job(job_id)
        if not job:
            raise NotFound("Job não existe.")
        project_id = job["project_id"]
        docs = self.db.list_documents_by_project(project_id)

        return JobStatusResponse(
            job_id=job["id"],
            project_id=project_id,
            status=job["status"],
            logs=job.get("logs") or [],
            documents=[
                JobDocProgress(
                    document_id=d["id"],
                    doc_type=d["doc_type"],
                    storage_path=d["storage_path"],
                    status=d["status"],
                    error=d.get("error"),
                )
                for d in docs
            ],
        )

    async def get_project(self, project_id: str) -> ProjectResponse:
        p = self.db.get_project(project_id)
        if not p:
            raise NotFound("Projeto não existe.")
        out_url = None
        if p.get("status") == "ready" and p.get("output_xlsx_path"):
            out_url = self.storage.signed_url(
                settings.SUPABASE_OUTPUTS_BUCKET,
                p["output_xlsx_path"],
                settings.SIGNED_URL_TTL_SECONDS,
            )

        return ProjectResponse(
            project_id=p["id"],
            name=p["name"],
            status=p["status"],
            consolidated_payload=p.get("consolidated_payload"),
            output_xlsx_path=p.get("output_xlsx_path"),
            output_signed_url=out_url,
        )

    async def get_project_output_url(self, project_id: str) -> OutputUrlResponse:
        p = self.db.get_project(project_id)
        if not p:
            raise NotFound("Projeto não existe.")
        if p.get("status") != "ready" or not p.get("output_xlsx_path"):
            raise Conflict("Projeto ainda não está pronto.")
        url = self.storage.signed_url(settings.SUPABASE_OUTPUTS_BUCKET, p["output_xlsx_path"], settings.SIGNED_URL_TTL_SECONDS)
        return OutputUrlResponse(project_id=project_id, signed_url=url)

    def _process_job_sync(self, job_id: str) -> None:
        job = self.db.get_job(job_id)
        if not job:
            return
        project_id = job["project_id"]
        project = self.db.get_project(project_id)
        if not project:
            return

        try:
            self.db.append_job_log(job_id, _evt("info", "job_processing_started"))
            docs = self.db.list_documents_by_project(project_id)

            extracted_docs: list[dict] = []

            for d in docs:
                doc_id = d["id"]
                doc_type = DocType(d["doc_type"])
                storage_bucket = settings.SUPABASE_UPLOADS_BUCKET
                storage_path = d["storage_path"]

                self.db.update_document(doc_id, {"status": "processing", "error": None})
                self.db.append_job_log(job_id, _evt("info", "doc_processing", {"doc_id": doc_id, "doc_type": doc_type.value}))

                content = self.storage.download(storage_bucket, storage_path)
                ext = Path(d["original_filename"]).suffix.lower()

                if ext in (".xlsx", ".xlsm", ".csv"):
                    res = extract_tabular(doc_type, content, ext)
                    extracted_docs.append(res.payload)
                    self.db.update_document(doc_id, {"status": "done", "extracted_payload": res.payload})
                    if res.warnings:
                        self.db.append_job_log(job_id, _evt("warn", "doc_warnings", {"doc_id": doc_id, "warnings": res.warnings}))
                    continue

                if ext == ".pdf":
                    text_res = extract_pdf_text(content)
                    text = (text_res.payload.get("text") or "").strip()
                    if not text:
                        raise ExtractionError(
                            "PDF sem texto extraível (scan). OCR não implementado.",
                            details={"doc_id": doc_id, "path": storage_path},
                        )

                    client = GeminiClient()
                    prompt = _build_pdf_prompt(doc_type, text)
                    patch = client.generate_structured(prompt, PdfExtractionResponse)

                    kv = patch.get("kv") or {}
                    if kv:
                        extracted_docs.append({"kv": kv})

                    for t in patch.get("tables") or []:
                        table_name = t.get("table")
                        rows = t.get("rows") or []
                        if table_name and rows:
                            extracted_docs.append({"table": table_name, "rows": rows})

                    self.db.update_document(doc_id, {"status": "done", "extracted_payload": patch})
                    if text_res.warnings:
                        self.db.append_job_log(job_id, _evt("warn", "doc_warnings", {"doc_id": doc_id, "warnings": text_res.warnings}))
                    continue

                raise BadRequest(f"Extensão não suportada: {ext}", details={"doc_id": doc_id})

            consolidated: ConsolidatedPayload = consolidate(extracted_docs)
            consolidated_public = consolidated.to_public_dict()
            self.db.update_project(project_id, {"consolidated_payload": consolidated_public})

            project_name = project["name"]
            safe_name = safe_filename(project_name)
            out_filename = f"Planilha KOA PE - {safe_name}.xlsx"
            out_local = f"/tmp/{project_id}_{out_filename}"
            write_filled_xlsx(consolidated, project_name=project_name, out_path=out_local)

            out_storage_path = f"{project_id}/{out_filename}"
            content_out = Path(out_local).read_bytes()
            self.storage.upload(
                settings.SUPABASE_OUTPUTS_BUCKET,
                out_storage_path,
                content_out,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            self.db.update_project(project_id, {"status": "ready", "output_xlsx_path": out_storage_path})
            self.db.update_job(job_id, {"status": "ready"})
            self.db.append_job_log(job_id, _evt("info", "job_ready", {"output_path": out_storage_path}))

        except Exception as e:
            self.db.update_project(project_id, {"status": "failed"})
            self.db.update_job(job_id, {"status": "failed"})
            self.db.append_job_log(job_id, _evt("error", "job_failed", {"error": str(e)}))

            for d in self.db.list_documents_by_project(project_id):
                if d["status"] in ("queued", "processing", "created"):
                    self.db.update_document(d["id"], {"status": "failed", "error": str(e)})

def _evt(level: str, event: str, extra: dict | None = None) -> dict:
    d = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
    }
    if extra:
        d.update(extra)
    return d

def _build_pdf_prompt(doc_type: DocType, text: str) -> str:
    expected_table = {
        DocType.ENDIVIDAMENTO: "Endividamento",
        DocType.RECEBIVEIS: "Recebíveis",
        DocType.TIPOLOGIA: "Tipologia",
        DocType.LANDBANK: "Landbank",
        DocType.FATURAMENTO: "Viabilidade Financeira",
    }.get(doc_type)

    rules = [
        "Retorne JSON estritamente válido.",
        "Não invente dados.",
        "Para tabelas, use como keys as LETRAS das colunas do template (ex.: 'B','C',...).",
        "Para valores BRL, devolva número decimal (1234567.89).",
        "Para datas, devolva ISO 'YYYY-MM-DD' quando possível.",
        "Se não encontrar uma tabela com segurança, deixe tables vazio e use kv (Geral/Projeto) só quando tiver certeza.",
    ]

    hint = f"DocType informado: {doc_type.value}."
    if expected_table:
        hint += f" Tente produzir patch para a tabela '{expected_table}'."
        hint += " Se tiver colunas duplicadas (ex.: Recebíveis), escolha a letra correta explicitamente."

    return f"""Você é um extrator de dados pt-BR para planilha KOA.

{hint}

REGRAS:
- {chr(10).join(rules)}

TEXTO EXTRAÍDO (delimitado):
<<<
{text[:180000]}
>>>
"""

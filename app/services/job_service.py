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
from app.extractors.prompts import get_prompt_for_doc_type
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
    def __init__(self, db: DB | None = None, storage: Storage | None = None):
        self.db = db or DB()
        self.storage = storage or Storage()

    async def create_job(self, req: CreateJobRequest) -> CreateJobResponse:
        if req.project_id:
            project = self.db.get_project(req.project_id)
            if not project:
                raise NotFound("project_id não existe.")
            project_id = req.project_id
        else:
            project = self.db.create_project(req.project_name or "Sem nome")
            project_id = project["aida_id"]

        # Atualiza status do projeto para processing e limpa estado consolidado anterior
        self.db.update_project(
            project_id,
            {
                "aida_status": "processing",
                "aida_consolidated_payload": None,
                "aida_output_xlsx_path": None,
            },
        )

        run_number = self.db.get_next_run_number(project_id)

        job = self.db.create_job(project_id, run_number=run_number)
        job_id = job["aida_id"]

        self.db.append_job_log(job_id, _evt("info", "job_created", {"project_id": project_id, "run_number": run_number}))

        for d in req.documents:
            doc = self.db.create_document(project_id, d.doc_type.value, d.storage_path, d.original_filename)
            # Atualiza status do documento para queued
            self.db.update_document(doc["aida_id"], {"aida_status": "queued"})

        # Atualiza status do job para processing
        self.db.update_job(job_id, {"aida_status": "processing"})

        return CreateJobResponse(job_id=job_id, project_id=project_id, status="processing", run_number=run_number)

    async def reprocess_project(self, project_id: str) -> CreateJobResponse:
        project = self.db.get_project(project_id)
        if not project:
            raise NotFound("Projeto não existe.")

        documents = self.db.list_documents_by_project(project_id)
        if not documents:
            raise Conflict("Projeto não possui documentos para reprocessar.")

        run_number = self.db.get_next_run_number(project_id)

        # Reset state for new run
        self.db.update_project(
            project_id,
            {
                "aida_status": "processing",
                "aida_consolidated_payload": None,
                "aida_output_xlsx_path": None,
            },
        )

        for doc in documents:
            self.db.update_document(
                doc["aida_id"],
                {"aida_status": "queued", "aida_error": None, "aida_extracted_payload": None},
            )

        job = self.db.create_job(project_id, run_number=run_number)
        job_id = job["aida_id"]

        self.db.append_job_log(
            job_id,
            _evt("info", "job_reprocess_requested", {"project_id": project_id, "run_number": run_number}),
        )
        self.db.update_job(job_id, {"aida_status": "processing"})

        return CreateJobResponse(job_id=job_id, project_id=project_id, status="processing", run_number=run_number)

    async def kickoff_job(self, job_id: str) -> None:
        asyncio.create_task(run_in_threadpool(self._process_job_sync, job_id))

    async def get_job_status(self, job_id: str) -> JobStatusResponse:
        job = self.db.get_job(job_id)
        if not job:
            raise NotFound("Job não existe.")
        
        project_id = job["aida_project_id"]
        docs = self.db.list_documents_by_project(project_id)

        return JobStatusResponse(
            job_id=job["aida_id"],
            project_id=project_id,
            status=job["aida_status"],
            run_number=job.get("aida_run_number"),
            logs=job.get("aida_logs") or [],
            documents=[
                JobDocProgress(
                    document_id=d["aida_id"],
                    doc_type=d["aida_doc_type"],
                    storage_path=d["aida_storage_path"],
                    status=d["aida_status"],
                    error=d.get("aida_error"),
                )
                for d in docs
            ],
        )

    async def get_project(self, project_id: str) -> ProjectResponse:
        p = self.db.get_project(project_id)
        if not p:
            raise NotFound("Projeto não existe.")
        
        out_url = None
        # Verifica status e path usando prefixo aida_
        if p.get("aida_status") == "ready" and p.get("aida_output_xlsx_path"):
            out_url = self.storage.signed_url(
                settings.SUPABASE_OUTPUTS_BUCKET,
                p["aida_output_xlsx_path"],
                settings.SIGNED_URL_TTL_SECONDS,
            )

        return ProjectResponse(
            project_id=p["aida_id"],
            name=p["aida_name"],
            status=p["aida_status"],
            consolidated_payload=p.get("aida_consolidated_payload"),
            output_xlsx_path=p.get("aida_output_xlsx_path"),
            output_signed_url=out_url,
        )

    async def get_project_output_url(self, project_id: str) -> OutputUrlResponse:
        p = self.db.get_project(project_id)
        if not p:
            raise NotFound("Projeto não existe.")
            
        if p.get("aida_status") != "ready" or not p.get("aida_output_xlsx_path"):
            raise Conflict("Projeto ainda não está pronto.")
            
        url = self.storage.signed_url(
            settings.SUPABASE_OUTPUTS_BUCKET, 
            p["aida_output_xlsx_path"], 
            settings.SIGNED_URL_TTL_SECONDS
        )
        return OutputUrlResponse(project_id=project_id, signed_url=url)

    def _process_job_sync(self, job_id: str) -> None:
        job = self.db.get_job(job_id)
        if not job:
            return
        
        project_id = job["aida_project_id"]
        project = self.db.get_project(project_id)
        if not project:
            return

        try:
            self.db.append_job_log(job_id, _evt("info", "job_processing_started"))
            docs = self.db.list_documents_by_project(project_id)

            extracted_docs: list[dict] = []

            for d in docs:
                doc_id = d["aida_id"]
                doc_type_str = d["aida_doc_type"]
                doc_type = DocType(doc_type_str)
                
                storage_bucket = settings.SUPABASE_UPLOADS_BUCKET
                storage_path = d["aida_storage_path"]

                self.db.update_document(doc_id, {"aida_status": "processing", "aida_error": None})
                self.db.append_job_log(job_id, _evt("info", "doc_processing", {"doc_id": doc_id, "doc_type": doc_type_str}))

                content = self.storage.download(storage_bucket, storage_path)
                ext = Path(d["aida_original_filename"]).suffix.lower()

                # --- Extração: Planilhas ---
                if ext in (".xlsx", ".xlsm", ".csv"):
                    res = extract_tabular(doc_type, content, ext)
                    extracted_docs.append(res.payload)
                    self.db.update_document(doc_id, {"aida_status": "done", "aida_extracted_payload": res.payload})
                    if res.warnings:
                        self.db.append_job_log(job_id, _evt("warn", "doc_warnings", {"doc_id": doc_id, "warnings": res.warnings}))
                    continue

                # --- Extração: PDFs ---
                if ext == ".pdf":
                    text_res = extract_pdf_text(content)
                    text = (text_res.payload.get("text") or "").strip()
                    
                    if not text:
                        raise ExtractionError(
                            "PDF sem texto extraível (nem OCR funcionou).",
                            details={"doc_id": doc_id, "path": storage_path},
                        )

                    client = GeminiClient()
                    
                    # Usa o novo sistema de prompts "cérebro"
                    prompt = get_prompt_for_doc_type(doc_type, text)
                    
                    patch = client.generate_structured(prompt, PdfExtractionResponse)

                    # Consolida partes do JSON do Gemini
                    kv = patch.get("kv") or {}
                    if kv:
                        extracted_docs.append({"kv": kv})

                    for t in patch.get("tables") or []:
                        table_name = t.get("table")
                        rows = t.get("rows") or []
                        if table_name and rows:
                            extracted_docs.append({"table": table_name, "rows": rows})

                    self.db.update_document(doc_id, {"aida_status": "done", "aida_extracted_payload": patch})
                    if text_res.warnings:
                        self.db.append_job_log(job_id, _evt("warn", "doc_warnings", {"doc_id": doc_id, "warnings": text_res.warnings}))
                    continue

                raise BadRequest(f"Extensão não suportada: {ext}", details={"doc_id": doc_id})

            # Consolidação Final
            consolidated: ConsolidatedPayload = consolidate(extracted_docs)
            consolidated_public = consolidated.to_public_dict()
            
            self.db.update_project(project_id, {"aida_consolidated_payload": consolidated_public})

            project_name = project["aida_name"]
            safe_name = safe_filename(project_name)
            out_filename = f"Planilha KOA PE - {safe_name}.xlsx"
            out_local = f"/tmp/{project_id}_run-{job.get('aida_run_number') or 1}_{out_filename}"
            
            write_filled_xlsx(consolidated, project_name=project_name, out_path=out_local)

            out_storage_path = self._build_output_storage_path(project_id, job.get("aida_run_number"), out_filename)
            content_out = Path(out_local).read_bytes()
            self.storage.upload(
                settings.SUPABASE_OUTPUTS_BUCKET,
                out_storage_path,
                content_out,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

            self.db.update_project(project_id, {"aida_status": "ready", "aida_output_xlsx_path": out_storage_path})
            self.db.update_job(job_id, {"aida_status": "ready"})
            self.db.append_job_log(job_id, _evt("info", "job_ready", {"output_path": out_storage_path}))

        except Exception as e:
            # Em caso de falha, atualiza tudo para failed
            self.db.update_project(project_id, {"aida_status": "failed"})
            self.db.update_job(job_id, {"aida_status": "failed"})
            self.db.append_job_log(job_id, _evt("error", "job_failed", {"error": str(e)}))

            # Atualiza documentos pendentes para failed
            for d in self.db.list_documents_by_project(project_id):
                if d["aida_status"] in ("queued", "processing", "created"):
                    self.db.update_document(d["aida_id"], {"aida_status": "failed", "aida_error": str(e)})

    @staticmethod
    def _build_output_storage_path(project_id: str, run_number: int | None, filename: str) -> str:
        run = run_number or 1
        return f"{project_id}/run-{run}/{filename}"

def _evt(level: str, event: str, extra: dict | None = None) -> dict:
    d = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "event": event,
    }
    if extra:
        d.update(extra)
    return d
    
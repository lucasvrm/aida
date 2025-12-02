from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.supabase.client import supabase_client

class DB:
    def __init__(self):
        self.sb = supabase_client()

    def create_project(self, name: str, project_id: str | None = None) -> dict[str, Any]:
        pid = project_id or str(uuid4())
        # Tabela: aida_projects
        payload = {
            "aida_id": pid,
            "aida_name": name,
            "aida_status": "created"
        }
        res = self.sb.table("aida_projects").insert(payload).execute()
        return res.data[0]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        res = self.sb.table("aida_projects").select("*").eq("aida_id", project_id).limit(1).execute()
        return res.data[0] if res.data else None

    def update_project(self, project_id: str, patch: dict[str, Any]) -> None:
        # Patch deve conter chaves com prefixo aida_ (ex: aida_status)
        self.sb.table("aida_projects").update(patch).eq("aida_id", project_id).execute()

    def create_job(self, project_id: str, run_number: int | None = None) -> dict[str, Any]:
        # Tabela: aida_jobs
        payload = {
            "aida_project_id": project_id,
            "aida_status": "created",
            "aida_run_number": run_number or 1,
        }
        res = self.sb.table("aida_jobs").insert(payload).execute()
        return res.data[0]

    def list_jobs_by_project(self, project_id: str) -> list[dict[str, Any]]:
        res = (
            self.sb.table("aida_jobs")
            .select("*")
            .eq("aida_project_id", project_id)
            .execute()
        )
        return res.data or []

    def get_next_run_number(self, project_id: str) -> int:
        res = (
            self.sb.table("aida_jobs")
            .select("aida_run_number")
            .eq("aida_project_id", project_id)
            .order("aida_run_number", desc=True)
            .limit(1)
            .execute()
        )
        latest = res.data[0]["aida_run_number"] if res.data else 0
        return (latest or 0) + 1

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        res = self.sb.table("aida_jobs").select("*").eq("aida_id", job_id).limit(1).execute()
        return res.data[0] if res.data else None

    def update_job(self, job_id: str, patch: dict[str, Any]) -> None:
        self.sb.table("aida_jobs").update(patch).eq("aida_id", job_id).execute()

    def append_job_log(self, job_id: str, event: dict[str, Any]) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        # Coluna: aida_logs
        logs = job.get("aida_logs") or []
        if not isinstance(logs, list):
            logs = []
        logs.append(event)
        self.update_job(job_id, {"aida_logs": logs})

    def create_document(
        self,
        project_id: str,
        doc_type: str,
        storage_path: str,
        original_filename: str,
    ) -> dict[str, Any]:
        # Tabela: aida_documents
        payload = {
            "aida_project_id": project_id,
            "aida_doc_type": doc_type,
            "aida_storage_path": storage_path,
            "aida_original_filename": original_filename,
            "aida_status": "created",
        }
        res = self.sb.table("aida_documents").insert(payload).execute()
        return res.data[0]

    def update_document(self, doc_id: str, patch: dict[str, Any]) -> None:
        self.sb.table("aida_documents").update(patch).eq("aida_id", doc_id).execute()

    def list_documents_by_project(self, project_id: str) -> list[dict[str, Any]]:
        # Busca por aida_project_id
        res = self.sb.table("aida_documents").select("*").eq("aida_project_id", project_id).execute()
        return res.data or []
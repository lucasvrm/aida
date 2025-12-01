from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.supabase.client import supabase_client

class DB:
    def __init__(self):
        self.sb = supabase_client()

    def create_project(self, name: str, project_id: str | None = None) -> dict[str, Any]:
        pid = project_id or str(uuid4())
        payload = {"id": pid, "name": name, "status": "created"}
        res = self.sb.table("projects").insert(payload).execute()
        return res.data[0]

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        res = self.sb.table("projects").select("*").eq("id", project_id).limit(1).execute()
        return res.data[0] if res.data else None

    def update_project(self, project_id: str, patch: dict[str, Any]) -> None:
        self.sb.table("projects").update(patch).eq("id", project_id).execute()

    def create_job(self, project_id: str) -> dict[str, Any]:
        res = self.sb.table("jobs").insert({"project_id": project_id, "status": "created"}).execute()
        return res.data[0]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        res = self.sb.table("jobs").select("*").eq("id", job_id).limit(1).execute()
        return res.data[0] if res.data else None

    def update_job(self, job_id: str, patch: dict[str, Any]) -> None:
        self.sb.table("jobs").update(patch).eq("id", job_id).execute()

    def append_job_log(self, job_id: str, event: dict[str, Any]) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        logs = job.get("logs") or []
        if not isinstance(logs, list):
            logs = []
        logs.append(event)
        self.update_job(job_id, {"logs": logs})

    def create_document(
        self,
        project_id: str,
        doc_type: str,
        storage_path: str,
        original_filename: str,
    ) -> dict[str, Any]:
        res = self.sb.table("documents").insert({
            "project_id": project_id,
            "doc_type": doc_type,
            "storage_path": storage_path,
            "original_filename": original_filename,
            "status": "created",
        }).execute()
        return res.data[0]

    def update_document(self, doc_id: str, patch: dict[str, Any]) -> None:
        self.sb.table("documents").update(patch).eq("id", doc_id).execute()

    def list_documents_by_project(self, project_id: str) -> list[dict[str, Any]]:
        res = self.sb.table("documents").select("*").eq("project_id", project_id).execute()
        return res.data or []

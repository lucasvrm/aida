from __future__ import annotations

from typing import Any

from supabase import Client

from app.models.schemas import MetricsResponse, StatusCounts
from app.supabase.client import supabase_client


class MetricsService:
    def __init__(self, client: Client | None = None):
        self.sb = client or supabase_client()

    def _count(self, table: str, status: str | None = None) -> int:
        query = self.sb.table(table).select("aida_id", count="exact")
        if status:
            query = query.eq("aida_status", status)
        res = query.execute()
        return res.count or 0

    def _status_counts(self, table: str) -> StatusCounts:
        created = self._count(table, "created")
        processing = self._count(table, "processing")
        ready = self._count(table, "ready")
        failed = self._count(table, "failed")
        total = self._count(table)
        return StatusCounts(
            total=total,
            created=created,
            processing=processing,
            ready=ready,
            failed=failed,
        )

    def _recent_logs(self, limit: int = 20) -> list[dict[str, Any]]:
        res = (
            self.sb.table("aida_jobs")
            .select("aida_id,aida_project_id,aida_logs,aida_updated_at")
            .order("aida_updated_at", desc=True)
            .limit(limit)
            .execute()
        )

        logs: list[dict[str, Any]] = []
        for job in res.data or []:
            job_id = job.get("aida_id")
            project_id = job.get("aida_project_id")
            for entry in job.get("aida_logs") or []:
                enriched = {**entry, "job_id": job_id, "project_id": project_id}
                logs.append(enriched)

        logs.sort(key=lambda item: item.get("ts", ""), reverse=True)
        return logs[:limit]

    def fetch_metrics(self) -> MetricsResponse:
        projects = self._status_counts("aida_projects")
        jobs = self._status_counts("aida_jobs")
        documents_total = self._count("aida_documents")

        return MetricsResponse(
            projects=projects,
            jobs=jobs,
            documents=documents_total,
            recent_logs=self._recent_logs(),
        )

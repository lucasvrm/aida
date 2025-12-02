from uuid import uuid4

import pytest

from app.models.enums import DocType
from app.models.schemas import CreateJobRequest, DocumentIn
from app.services.job_service import JobService


class FakeStorage:
    def signed_url(self, bucket: str, path: str, ttl: int) -> str:  # pragma: no cover - not used in assertions
        return f"signed://{bucket}/{path}?ttl={ttl}"

    def download(self, bucket: str, path: str) -> bytes:  # pragma: no cover - not needed for these tests
        raise NotImplementedError

    def upload(self, bucket: str, path: str, content: bytes, content_type: str) -> None:  # pragma: no cover
        return None


class FakeDB:
    def __init__(self):
        self.projects: dict[str, dict] = {}
        self.documents: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}

    def create_project(self, name: str, project_id: str | None = None) -> dict:
        pid = project_id or str(uuid4())
        project = {
            "aida_id": pid,
            "aida_name": name,
            "aida_status": "created",
            "aida_consolidated_payload": None,
            "aida_output_xlsx_path": None,
        }
        self.projects[pid] = project
        return project

    def get_project(self, project_id: str):
        return self.projects.get(project_id)

    def update_project(self, project_id: str, patch: dict) -> None:
        self.projects[project_id].update(patch)

    def create_job(self, project_id: str, run_number: int | None = None) -> dict:
        jid = str(uuid4())
        job = {
            "aida_id": jid,
            "aida_project_id": project_id,
            "aida_status": "created",
            "aida_logs": [],
            "aida_run_number": run_number or 1,
        }
        self.jobs[jid] = job
        return job

    def get_job(self, job_id: str):
        return self.jobs.get(job_id)

    def update_job(self, job_id: str, patch: dict) -> None:
        self.jobs[job_id].update(patch)

    def append_job_log(self, job_id: str, event: dict) -> None:
        self.jobs[job_id].setdefault("aida_logs", []).append(event)

    def create_document(self, project_id: str, doc_type: str, storage_path: str, original_filename: str) -> dict:
        did = str(uuid4())
        doc = {
            "aida_id": did,
            "aida_project_id": project_id,
            "aida_doc_type": doc_type,
            "aida_storage_path": storage_path,
            "aida_original_filename": original_filename,
            "aida_status": "created",
            "aida_extracted_payload": None,
            "aida_error": None,
        }
        self.documents[did] = doc
        return doc

    def update_document(self, doc_id: str, patch: dict) -> None:
        self.documents[doc_id].update(patch)

    def list_documents_by_project(self, project_id: str):
        return [d for d in self.documents.values() if d["aida_project_id"] == project_id]

    def list_jobs_by_project(self, project_id: str):
        jobs = [j for j in self.jobs.values() if j["aida_project_id"] == project_id]
        return sorted(jobs, key=lambda j: j.get("aida_run_number") or 0)

    def get_next_run_number(self, project_id: str) -> int:
        jobs = self.list_jobs_by_project(project_id)
        if not jobs:
            return 1
        return (jobs[-1].get("aida_run_number") or 0) + 1


def _fake_service():
    db = FakeDB()
    svc = JobService(db=db, storage=FakeStorage())
    return svc, db


@pytest.mark.anyio
async def test_reprocess_increments_run_and_resets_state():
    svc, db = _fake_service()
    req = CreateJobRequest(
        project_name="Projeto Teste",
        documents=[
            DocumentIn(
                doc_type=DocType.ENDIVIDAMENTO,
                storage_path="uploads/doc1.pdf",
                original_filename="doc1.pdf",
            )
        ],
    )

    first_job = await svc.create_job(req)
    first_job_id = first_job.job_id
    project_id = first_job.project_id

    # Simula um estado pronto prévio
    db.append_job_log(first_job_id, {"event": "manual_log"})
    db.update_project(
        project_id,
        {
            "aida_status": "ready",
            "aida_consolidated_payload": {"old": True},
            "aida_output_xlsx_path": "old/path.xlsx",
        },
    )
    for doc in db.list_documents_by_project(project_id):
        db.update_document(doc["aida_id"], {"aida_status": "done", "aida_error": "old", "aida_extracted_payload": {"old": True}})

    reproc_job = await svc.reprocess_project(project_id)

    assert reproc_job.run_number == 2
    project = db.get_project(project_id)
    assert project["aida_status"] == "processing"
    assert project["aida_consolidated_payload"] is None
    assert project["aida_output_xlsx_path"] is None

    # Documentos voltam para a fila e sem payloads/erros
    for doc in db.list_documents_by_project(project_id):
        assert doc["aida_status"] == "queued"
        assert doc["aida_error"] is None
        assert doc.get("aida_extracted_payload") is None

    # Logs anteriores permanecem intocados
    assert len(db.get_job(first_job_id)["aida_logs"]) == 2  # job_created + manual_log
    assert db.get_job(first_job_id)["aida_logs"][0]["event"] == "job_created"


@pytest.mark.anyio
async def test_multiple_reprocesses_keep_run_history_and_logs():
    svc, db = _fake_service()
    req = CreateJobRequest(
        project_name="Projeto Histórico",
        documents=[
            DocumentIn(
                doc_type=DocType.RECEBIVEIS,
                storage_path="uploads/doc2.pdf",
                original_filename="doc2.pdf",
            )
        ],
    )

    first = await svc.create_job(req)
    second = await svc.reprocess_project(first.project_id)
    third = await svc.reprocess_project(first.project_id)

    assert first.run_number == 1
    assert second.run_number == 2
    assert third.run_number == 3

    history = [j.get("aida_run_number") for j in db.list_jobs_by_project(first.project_id)]
    assert history == [1, 2, 3]

    assert db.get_job(first.job_id)["aida_logs"][0]["event"] == "job_created"
    assert db.get_job(second.job_id)["aida_logs"][0]["event"] == "job_reprocess_requested"
    assert db.get_job(third.job_id)["aida_logs"][0]["event"] == "job_reprocess_requested"


def test_output_path_is_run_scoped():
    assert JobService._build_output_storage_path("proj", 4, "file.xlsx") == "proj/run-4/file.xlsx"
    assert JobService._build_output_storage_path("proj", None, "file.xlsx") == "proj/run-1/file.xlsx"

import asyncio

import pytest

from app.core.errors import Conflict, NotFound
from app.models.enums import DocType
from app.models.schemas import CreateJobRequest, DocumentIn
from app.services.job_service import JobService
from app.supabase.db import DB


def test_create_document_with_invalid_project(monkeypatch):
    response = type("Resp", (), {"data": [], "error": "Foreign key violation"})()

    class FakeTable:
        def insert(self, payload):
            self.payload = payload
            return self

        def execute(self):
            return response

    class FakeSupabase:
        def table(self, name):
            assert name == "aida_documents"
            return FakeTable()

    monkeypatch.setattr("app.supabase.db.supabase_client", lambda: FakeSupabase())
    db = DB()

    with pytest.raises(NotFound):
        db.create_document("missing", "OUTRO", "some/path", "doc.pdf")


def test_create_job_rejects_processing_project():
    class FakeDB:
        def get_project(self, project_id):
            return {"aida_id": project_id, "aida_status": "processing"}

    svc = JobService()
    svc.db = FakeDB()

    req = CreateJobRequest(
        project_id="123e4567-e89b-12d3-a456-426614174000",
        documents=[DocumentIn(doc_type=DocType.OUTRO, storage_path="p", original_filename="f.pdf")],
    )

    with pytest.raises(Conflict):
        asyncio.run(svc.create_job(req))


def test_process_job_aborts_when_project_deleted():
    class FakeDB:
        def __init__(self):
            self.updated_jobs = []
            self.logs = []
            self.list_called = False

        def get_job(self, job_id):
            return {"aida_id": job_id, "aida_project_id": "proj-1"}

        def get_project(self, project_id):
            return None

        def update_job(self, job_id, patch):
            self.updated_jobs.append(patch)

        def append_job_log(self, job_id, event):
            self.logs.append(event)

        def list_documents_by_project(self, project_id):
            self.list_called = True
            return []

    class DummyStorage:
        pass

    db = FakeDB()
    svc = JobService()
    svc.db = db
    svc.storage = DummyStorage()

    svc._process_job_sync("job-1")

    assert db.updated_jobs[-1]["aida_status"] == "failed"
    assert any(log.get("event") == "job_aborted" for log in db.logs)
    assert db.list_called is False


def test_kickoff_job_aborts_when_project_failed(monkeypatch):
    class FakeDB:
        def __init__(self):
            self.updated_jobs = []
            self.logs = []

        def get_job(self, job_id):
            return {"aida_id": job_id, "aida_project_id": "proj-1"}

        def get_project(self, project_id):
            return {"aida_id": project_id, "aida_status": "failed"}

        def update_job(self, job_id, patch):
            self.updated_jobs.append(patch)

        def append_job_log(self, job_id, event):
            self.logs.append(event)

    tasks_created: list[asyncio.Task] = []

    def fake_create_task(coro):
        tasks_created.append(coro)
        return asyncio.Future()

    monkeypatch.setattr(asyncio, "create_task", fake_create_task)

    svc = JobService()
    svc.db = FakeDB()

    asyncio.run(svc.kickoff_job("job-1"))

    assert not tasks_created
    assert any(update.get("aida_status") == "failed" for update in svc.db.updated_jobs)
    assert any(log.get("event") == "job_aborted" for log in svc.db.logs)

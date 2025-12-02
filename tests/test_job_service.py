from types import SimpleNamespace
from pathlib import Path

import pytest

from app.services.job_service import JobService
from app.models.enums import DocType
from app.services import job_service

pytestmark = pytest.mark.unit


class FakeDB:
    def __init__(self, project, job, documents):
        self.project = project
        self.job = job
        self.documents = {d["aida_id"]: d for d in documents}

    def get_job(self, job_id):
        return self.job if self.job.get("aida_id") == job_id else None

    def get_project(self, project_id):
        return self.project if self.project.get("aida_id") == project_id else None

    def update_project(self, project_id, patch):
        self.project.update(patch)

    def update_job(self, job_id, patch):
        self.job.update(patch)

    def append_job_log(self, job_id, event):
        logs = self.job.setdefault("aida_logs", [])
        logs.append(event)

    def list_documents_by_project(self, project_id):
        return [d for d in self.documents.values() if d["aida_project_id"] == project_id]

    def update_document(self, doc_id, patch):
        self.documents[doc_id].update(patch)


class FakeStorage:
    def __init__(self, download_data=b"data", fail_download=False, fail_upload=False):
        self.download_data = download_data
        self.fail_download = fail_download
        self.fail_upload = fail_upload
        self.uploaded = []

    def download(self, bucket, path):
        if self.fail_download:
            raise RuntimeError("download failed")
        return self.download_data

    def upload(self, bucket, path, content, content_type):
        if self.fail_upload:
            raise RuntimeError("upload failed")
        self.uploaded.append((bucket, path, content, content_type))

    def signed_url(self, bucket, path, ttl):
        return f"https://signed/{bucket}/{path}?ttl={ttl}"


@pytest.fixture

def base_entities():
    project = {"aida_id": "proj-1", "aida_name": "Projeto", "aida_status": "processing"}
    job = {"aida_id": "job-1", "aida_project_id": project["aida_id"], "aida_status": "processing", "aida_logs": []}
    documents = []
    return project, job, documents


def make_service(project, job, documents, storage):
    svc = JobService()
    svc.db = FakeDB(project, job, documents)
    svc.storage = storage
    return svc


def patch_tabular(monkeypatch, payload=None, warnings=None):
    class Result:
        def __init__(self, payload, warnings):
            self.payload = payload
            self.warnings = warnings or []

    monkeypatch.setattr(job_service, "extract_tabular", lambda doc_type, content, ext: Result(payload or {"table": "rows"}, warnings))


def patch_consolidate(monkeypatch, public_payload=None):
    class Consolidated:
        def __init__(self, payload):
            self.payload = payload

        def to_public_dict(self):
            return self.payload

    monkeypatch.setattr(job_service, "consolidate", lambda docs: Consolidated(public_payload or {"docs": docs}))


def patch_write_xlsx(monkeypatch):
    def _write(consolidated, project_name, out_path):
        Path(out_path).write_bytes(b"xlsx")

    monkeypatch.setattr(job_service, "write_filled_xlsx", _write)


def patch_pdf(monkeypatch):
    class Result:
        def __init__(self):
            self.payload = {"kv": {}}
            self.warnings = []

    monkeypatch.setattr(job_service, "extract_pdf_text", lambda content: Result())
    monkeypatch.setattr(job_service, "GeminiClient", lambda: SimpleNamespace(generate_structured=lambda prompt, model: {}))
    monkeypatch.setattr(job_service, "get_prompt_for_doc_type", lambda doc_type, text: "prompt")


def test_process_job_without_documents(base_entities, monkeypatch, tmp_path):
    project, job, documents = base_entities
    storage = FakeStorage()
    svc = make_service(project, job, documents, storage)

    patch_tabular(monkeypatch)
    patch_consolidate(monkeypatch, {"docs": []})
    patch_write_xlsx(monkeypatch)

    svc._process_job_sync(job["aida_id"])

    assert svc.db.job["aida_status"] == "ready"
    assert svc.db.project["aida_status"] == "ready"
    assert svc.db.project["aida_output_xlsx_path"].startswith(project["aida_id"])
    assert storage.uploaded


def test_process_job_with_invalid_extension(monkeypatch, base_entities):
    project, job, _ = base_entities
    documents = [
        {
            "aida_id": "doc-1",
            "aida_project_id": project["aida_id"],
            "aida_doc_type": DocType.OUTRO.value,
            "aida_storage_path": "uploads/file.txt",
            "aida_original_filename": "file.txt",
            "aida_status": "queued",
        }
    ]
    storage = FakeStorage()
    svc = make_service(project, job, documents, storage)

    patch_tabular(monkeypatch)
    patch_consolidate(monkeypatch)
    patch_write_xlsx(monkeypatch)

    svc._process_job_sync(job["aida_id"])

    assert svc.db.job["aida_status"] == "failed"
    assert svc.db.project["aida_status"] == "failed"
    assert svc.db.documents["doc-1"]["aida_status"] == "failed"
    assert svc.db.job["aida_logs"][-1]["event"] == "job_failed"


def test_process_job_download_failure(monkeypatch, base_entities):
    project, job, documents = base_entities
    documents.append(
        {
            "aida_id": "doc-1",
            "aida_project_id": project["aida_id"],
            "aida_doc_type": DocType.OUTRO.value,
            "aida_storage_path": "uploads/file.csv",
            "aida_original_filename": "file.csv",
            "aida_status": "queued",
        }
    )
    storage = FakeStorage(fail_download=True)
    svc = make_service(project, job, documents, storage)

    patch_tabular(monkeypatch)
    patch_consolidate(monkeypatch)
    patch_write_xlsx(monkeypatch)

    svc._process_job_sync(job["aida_id"])

    assert svc.db.job["aida_status"] == "failed"
    assert svc.db.project["aida_status"] == "failed"
    assert svc.db.documents["doc-1"]["aida_status"] == "failed"


def test_process_job_upload_failure(monkeypatch, base_entities):
    project, job, documents = base_entities
    documents.append(
        {
            "aida_id": "doc-1",
            "aida_project_id": project["aida_id"],
            "aida_doc_type": DocType.OUTRO.value,
            "aida_storage_path": "uploads/file.csv",
            "aida_original_filename": "file.csv",
            "aida_status": "queued",
        }
    )
    storage = FakeStorage(fail_upload=True)
    svc = make_service(project, job, documents, storage)

    patch_tabular(monkeypatch)
    patch_consolidate(monkeypatch)
    patch_write_xlsx(monkeypatch)

    svc._process_job_sync(job["aida_id"])

    assert svc.db.job["aida_status"] == "failed"
    assert svc.db.project["aida_status"] == "failed"
    assert svc.db.documents["doc-1"]["aida_status"] == "done"


def test_process_job_happy_path(monkeypatch, base_entities):
    project, job, documents = base_entities
    documents.append(
        {
            "aida_id": "doc-1",
            "aida_project_id": project["aida_id"],
            "aida_doc_type": DocType.OUTRO.value,
            "aida_storage_path": "uploads/file.csv",
            "aida_original_filename": "file.csv",
            "aida_status": "queued",
        }
    )
    storage = FakeStorage(download_data=b"name,value\n1,2")
    svc = make_service(project, job, documents, storage)

    patch_tabular(monkeypatch, payload={"table": "rows"})
    patch_consolidate(monkeypatch, public_payload={"table": "rows"})
    patch_write_xlsx(monkeypatch)

    svc._process_job_sync(job["aida_id"])

    assert svc.db.job["aida_status"] == "ready"
    assert svc.db.project["aida_status"] == "ready"
    assert svc.db.project["aida_output_xlsx_path"].startswith(project["aida_id"])
    assert storage.uploaded

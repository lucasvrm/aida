from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.supabase import db as db_module
from app.supabase.db import DB

pytestmark = pytest.mark.unit


class TableQuery:
    def __init__(self, name, store):
        self.name = name
        self.store = store
        self._filter = None
        self._patch = None
        self._payload = None
        self._limit = None

    def insert(self, payload):
        if "aida_id" not in payload:
            payload = {**payload, "aida_id": str(uuid4())}
        self._payload = payload
        return self

    def select(self, fields):
        return self

    def update(self, patch):
        self._patch = patch
        return self

    def eq(self, field, value):
        self._filter = (field, value)
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        if self._payload is not None:
            self.store.setdefault(self.name, []).append(self._payload)
            return SimpleNamespace(data=[self._payload])

        rows = self.store.get(self.name, [])
        if self._patch is not None and self._filter:
            field, value = self._filter
            for row in rows:
                if row.get(field) == value:
                    row.update(self._patch)

        field, value = self._filter if self._filter else (None, None)
        filtered = rows if field is None else [r for r in rows if r.get(field) == value]
        if self._limit is not None:
            filtered = filtered[: self._limit]
        return SimpleNamespace(data=filtered)


class SupabaseStub:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        return TableQuery(name, self.store)


@pytest.fixture
def supabase_store():
    return {}


@pytest.fixture
def supabase_client(monkeypatch, supabase_store):
    stub = SupabaseStub(supabase_store)
    monkeypatch.setattr(db_module, "supabase_client", lambda: stub)
    return stub


def test_create_and_get_project_supplies_aida_fields(supabase_client, supabase_store):
    database = DB()

    project = database.create_project("Projeto Teste", project_id="proj-1")
    fetched = database.get_project(project["aida_id"])

    assert project["aida_name"] == "Projeto Teste"
    assert project["aida_id"].startswith("proj-")
    assert fetched == project
    assert supabase_store["aida_projects"][0] == project


def test_update_project_enforces_prefixes(supabase_client, supabase_store):
    database = DB()
    supabase_store["aida_projects"] = [{"aida_id": "proj-1", "aida_status": "created"}]

    database.update_project("proj-1", {"aida_status": "ready"})

    assert supabase_store["aida_projects"][0]["aida_status"] == "ready"


def test_job_and_document_queries_propagate_errors(monkeypatch):
    class FailingClient:
        def table(self, name):
            raise RuntimeError("boom")

    monkeypatch.setattr(db_module, "supabase_client", lambda: FailingClient())

    database = DB()

    with pytest.raises(RuntimeError):
        database.create_job("proj-1")

    with pytest.raises(RuntimeError):
        database.list_documents_by_project("proj-1")


def test_job_and_document_lifecycle(supabase_client, supabase_store):
    database = DB()
    supabase_store["aida_documents"] = []

    job = database.create_job("proj-1")
    fetched_job = database.get_job(job["aida_id"]).copy()
    database.update_job(job["aida_id"], {"aida_status": "processing"})

    document = database.create_document("proj-1", "OUTRO", "uploads/doc.csv", "doc.csv")
    database.update_document(document["aida_id"], {"aida_status": "done"})
    docs = database.list_documents_by_project("proj-1")

    assert fetched_job["aida_status"] == "created"
    assert job["aida_project_id"] == "proj-1"
    assert supabase_store["aida_jobs"][0]["aida_status"] == "processing"
    assert docs[0]["aida_status"] == "done"

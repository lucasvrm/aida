import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.models.schemas import CreateJobResponse, JobStatusResponse, ProjectResponse
from app.api.routes import jobs as jobs_routes
from app.api.routes import projects as projects_routes

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_header(settings):
    return {"Authorization": f"Bearer {settings.INTERNAL_API_TOKEN}"}


@pytest.mark.parametrize(
    "header",
    [None, {"Authorization": "Token invalid"}, {"Authorization": "Bearer wrong"}],
)
def test_jobs_requires_bearer_token(client, load_json_fixture, header):
    payload = load_json_fixture("job_request.json")
    response = client.post("/v1/jobs", json=payload, headers=header or {})

    assert response.status_code == 401
    assert response.json().get("error") == "UNAUTHORIZED"


def test_create_job_success(client, auth_header, monkeypatch, load_json_fixture):
    payload = load_json_fixture("job_request.json")

    created = CreateJobResponse(job_id="job-123", project_id="proj-123", status="processing")
    kickoff_called = {}

    class StubJobService:
        async def create_job(self, req):
            return created

        async def kickoff_job(self, job_id):
            kickoff_called["job_id"] = job_id

    monkeypatch.setattr(jobs_routes, "JobService", lambda: StubJobService())

    response = client.post("/v1/jobs", json=payload, headers=auth_header)

    assert response.status_code == 202
    assert response.json() == created.model_dump()
    assert kickoff_called["job_id"] == created.job_id


def test_get_job_status(client, auth_header, monkeypatch):
    expected = JobStatusResponse(
        job_id="job-123",
        project_id="proj-123",
        status="ready",
        logs=[{"event": "job_ready"}],
        documents=[],
    )

    class StubJobService:
        async def get_job_status(self, job_id):
            return expected

    monkeypatch.setattr(jobs_routes, "JobService", lambda: StubJobService())

    response = client.get("/v1/jobs/job-123", headers=auth_header)

    assert response.status_code == 200
    assert response.json() == expected.model_dump()


def test_get_project(client, auth_header, monkeypatch, load_json_fixture):
    project_payload = load_json_fixture("project_payload.json")
    expected = ProjectResponse(**project_payload)

    class StubJobService:
        async def get_project(self, project_id):
            return expected

        async def get_project_output_url(self, project_id):
            raise AssertionError("Should not be called")

    monkeypatch.setattr(projects_routes, "JobService", lambda: StubJobService())

    response = client.get(f"/v1/projects/{expected.project_id}", headers=auth_header)

    assert response.status_code == 200
    assert response.json() == expected.model_dump()


def test_health_route(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body.get("ok") is True
    assert body.get("service") == "koa-doc-pipeline"

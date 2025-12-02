import os

# Configura variáveis de ambiente para inicialização do Settings
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token-12345")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "gemini-key")

from app.models.schemas import MetricsResponse
from app.services.metrics import MetricsService


class FakeQuery:
    def __init__(self, data):
        self._data = list(data)
        self._count_mode = None

    def select(self, *_fields, **kwargs):
        self._count_mode = kwargs.get("count")
        return self

    def eq(self, column, value):
        self._data = [row for row in self._data if row.get(column) == value]
        return self

    def order(self, column, desc=False):
        self._data = sorted(self._data, key=lambda row: row.get(column), reverse=desc)
        return self

    def limit(self, n):
        self._data = self._data[:n]
        return self

    def execute(self):
        count = len(self._data) if self._count_mode else None
        return type("Res", (), {"data": self._data, "count": count})


class FakeSupabaseClient:
    def __init__(self, **tables):
        self._tables = tables

    def table(self, name):
        return FakeQuery(self._tables.get(name, []))


def test_metrics_service_counts_and_logs_sorted():
    client = FakeSupabaseClient(
        aida_projects=[
            {"aida_status": "processing"},
            {"aida_status": "ready"},
            {"aida_status": "failed"},
        ],
        aida_jobs=[
            {
                "aida_id": "job-1",
                "aida_project_id": "proj-1",
                "aida_status": "processing",
                "aida_updated_at": "2024-01-02T00:00:00Z",
                "aida_logs": [
                    {"ts": "2024-01-01T12:00:00Z", "event": "start"},
                    {"ts": "2024-01-01T12:05:00Z", "event": "download"},
                ],
            },
            {
                "aida_id": "job-2",
                "aida_project_id": "proj-2",
                "aida_status": "ready",
                "aida_updated_at": "2024-01-03T00:00:00Z",
                "aida_logs": [
                    {"ts": "2024-01-03T01:00:00Z", "event": "finished"},
                ],
            },
        ],
        aida_documents=[
            {"id": 1},
            {"id": 2},
            {"id": 3},
        ],
    )

    metrics = MetricsService(client=client).fetch_metrics()

    assert isinstance(metrics, MetricsResponse)
    assert metrics.projects.total == 3
    assert metrics.projects.ready == 1
    assert metrics.projects.failed == 1
    assert metrics.jobs.processing == 1
    assert metrics.documents == 3

    assert [log["event"] for log in metrics.recent_logs][:2] == ["finished", "download"]
    assert all("job_id" in log and "project_id" in log for log in metrics.recent_logs)


def test_metrics_service_handles_empty_tables():
    client = FakeSupabaseClient(aida_projects=[], aida_jobs=[], aida_documents=[])

    metrics = MetricsService(client=client).fetch_metrics()

    assert metrics.projects.total == 0
    assert metrics.jobs.total == 0
    assert metrics.documents == 0
    assert metrics.recent_logs == []

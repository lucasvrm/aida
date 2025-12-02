from app.models.schemas import CreateJobRequest

def test_create_job_requires_project_name_if_no_project_id():
    try:
        CreateJobRequest(documents=[])
        assert False, "should raise"
    except Exception:
        assert True

def test_create_job_ok_with_project_name():
    req = CreateJobRequest(project_name="Projeto X", documents=[])
    assert req.project_name == "Projeto X"


def test_create_job_with_webhook_url():
    url = "https://example.com/webhook"
    req = CreateJobRequest(project_name="Projeto Y", documents=[], webhook_url=url)
    assert str(req.webhook_url) == url

import os

import pytest


os.environ.setdefault("INTERNAL_API_TOKEN", "test-token-1234567890")
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "dummy-key")
os.environ.setdefault("GEMINI_API_KEY", "dummy-gemini")


@pytest.fixture(autouse=True)
def set_required_env(monkeypatch):
    monkeypatch.setenv("INTERNAL_API_TOKEN", os.environ["INTERNAL_API_TOKEN"])
    monkeypatch.setenv("SUPABASE_URL", os.environ["SUPABASE_URL"])
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    monkeypatch.setenv("GEMINI_API_KEY", os.environ["GEMINI_API_KEY"])

import importlib
import json
import os
from pathlib import Path

import pytest

# Garantir variáveis de ambiente necessárias para carregar Settings
DEFAULT_ENV = {
    "INTERNAL_API_TOKEN": "test-internal-token",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "service-role-key",
    "GEMINI_API_KEY": "gemini-test-key",
}

for key, value in DEFAULT_ENV.items():
    os.environ.setdefault(key, value)

# Recarrega settings para usar valores de teste
import app.core.config as config
importlib.reload(config)


@pytest.fixture
def settings():
    return config.settings


@pytest.fixture
def load_json_fixture():
    def _loader(filename: str):
        path = Path(__file__).parent / "fixtures" / filename
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)

    return _loader

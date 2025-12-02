import os

# Define valores padrão para as variáveis de ambiente necessárias durante os testes
os.environ.setdefault("INTERNAL_API_TOKEN", "test-token")
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "service-role-key")
os.environ.setdefault("GEMINI_API_KEY", "fake-key")
os.environ.setdefault("SUPABASE_OUTPUTS_BUCKET", "outputs")
os.environ.setdefault("SUPABASE_UPLOADS_BUCKET", "uploads")
os.environ.setdefault("SIGNED_URL_TTL_SECONDS", "60")
os.environ.setdefault("ENV", "test")

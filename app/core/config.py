from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENV: str = "local"
    LOG_LEVEL: str = "info"

    INTERNAL_API_TOKEN: str = Field(min_length=10)

    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str
    SUPABASE_UPLOADS_BUCKET: str = "koa-uploads"
    SUPABASE_OUTPUTS_BUCKET: str = "koa-outputs"

    TEMPLATE_PATH: str = "./resources/template.xlsx"
    KV_SPEC_PATH: str = "./resources/kv_spec.json"

    SIGNED_URL_TTL_SECONDS: int = 3600
    MAX_DOCUMENT_BYTES: int = 25_000_000
    MAX_TABLE_ROWS: int = 5_000

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS: int = 45

settings = Settings()

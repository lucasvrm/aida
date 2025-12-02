from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Literal
from uuid import UUID

from app.models.enums import DocType
from app.core.utils import normalize_whitespace

class DocumentIn(BaseModel):
    doc_type: DocType
    storage_bucket: str = "koa-uploads"
    storage_path: str
    original_filename: str
    notes: str | None = None

    @field_validator("storage_path", "original_filename")
    @classmethod
    def non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must be non-empty")
        return v

    @field_validator("notes")
    @classmethod
    def norm_notes(cls, v: str | None) -> str | None:
        return normalize_whitespace(v) if v else v

class CreateJobRequest(BaseModel):
    project_id: str | None = None
    project_name: str | None = None
    documents: list[DocumentIn]

    @field_validator("project_id")
    @classmethod
    def validate_project_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        UUID(v)
        return v

    @field_validator("project_name")
    @classmethod
    def norm_project_name(cls, v: str | None) -> str | None:
        return normalize_whitespace(v) if v else v

    @model_validator(mode="after")
    def check_name_or_id(self):
        if not self.project_id and not self.project_name:
            raise ValueError("project_name é obrigatório se project_id não vier.")
        return self

class CreateJobResponse(BaseModel):
    job_id: str
    project_id: str
    status: Literal["processing"]
    run_number: int

class JobDocProgress(BaseModel):
    document_id: str
    doc_type: str
    storage_path: str
    status: str
    error: str | None = None

class JobStatusResponse(BaseModel):
    job_id: str
    project_id: str
    status: str
    run_number: int | None = None
    logs: list[dict[str, Any]] = Field(default_factory=list)
    documents: list[JobDocProgress] = Field(default_factory=list)

class ProjectResponse(BaseModel):
    project_id: str
    name: str
    status: str
    consolidated_payload: dict[str, Any] | None = None
    output_xlsx_path: str | None = None
    output_signed_url: str | None = None

class OutputUrlResponse(BaseModel):
    project_id: str
    signed_url: str

class PdfTablePatch(BaseModel):
    table: str
    rows: list[dict[str, Any]] = Field(default_factory=list)

class PdfExtractionResponse(BaseModel):
    kv: dict[str, dict[str, Any]] = Field(default_factory=dict)  # {"Geral": {...}, "Projeto": {...}}
    tables: list[PdfTablePatch] = Field(default_factory=list)
    notes: str | None = None


class StatusCounts(BaseModel):
    total: int
    created: int
    processing: int
    ready: int
    failed: int


class MetricsResponse(BaseModel):
    projects: StatusCounts
    jobs: StatusCounts
    documents: int
    recent_logs: list[dict[str, Any]] = Field(default_factory=list)

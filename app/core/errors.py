from dataclasses import dataclass
from typing import Any

@dataclass
class AppError(Exception):
    code: str
    message: str
    status_code: int = 400
    details: Any | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "status_code": self.status_code, "details": self.details}

class Unauthorized(AppError):
    def __init__(self, message: str = "Unauthorized.", details: Any | None = None):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401, details=details)

class NotFound(AppError):
    def __init__(self, message: str = "Not found.", details: Any | None = None):
        super().__init__(code="NOT_FOUND", message=message, status_code=404, details=details)

class Conflict(AppError):
    def __init__(self, message: str = "Conflict.", details: Any | None = None):
        super().__init__(code="CONFLICT", message=message, status_code=409, details=details)

class BadRequest(AppError):
    def __init__(self, message: str = "Bad request.", details: Any | None = None):
        super().__init__(code="BAD_REQUEST", message=message, status_code=400, details=details)

class UpstreamError(AppError):
    def __init__(self, message: str = "Upstream error.", details: Any | None = None):
        super().__init__(code="UPSTREAM_ERROR", message=message, status_code=502, details=details)

class ExtractionError(AppError):
    def __init__(self, message: str = "Falha na extração.", details: Any | None = None):
        super().__init__(code="EXTRACTION_ERROR", message=message, status_code=422, details=details)

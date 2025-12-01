from fastapi import Header
from app.core.config import settings
from app.core.errors import Unauthorized

def verify_internal_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization:
        raise Unauthorized("Missing Authorization header.")
    if not authorization.lower().startswith("bearer "):
        raise Unauthorized("Invalid Authorization scheme.")
    token = authorization.split(" ", 1)[1].strip()
    if token != settings.INTERNAL_API_TOKEN:
        raise Unauthorized("Invalid token.")

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.projects import router as projects_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import get_logger, set_request_id
from app.template.bootstrap import ensure_template_ready

log = get_logger("app")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id")
        set_request_id(rid)
        response = await call_next(request)
        if rid:
            response.headers["x-request-id"] = rid
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="koa-doc-pipeline", version="0.1.0")

    ensure_template_ready()

    # --- ConfiguraÃ§Ã£o de CORS (Atualizado para ProduÃ§Ã£o) ---
    # Utiliza regex para aceitar qualquer origem localhost ou subdomÃ­nio vercel.app
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"https?://.*(localhost|vercel\.app).*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # -------------------------------------------------------

    app.add_middleware(RequestIdMiddleware)

    @app.exception_handler(AppError)
    async def app_error_handler(_req: Request, exc: AppError):
        log.error("app_error", extra={"err": exc.to_dict()})
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message, "details": exc.details},
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_req: Request, exc: Exception):
        log.exception("unhandled_exception")
        return JSONResponse(
            status_code=500,
            content={"error": "INTERNAL_ERROR", "message": "Erro interno.", "details": str(exc)},
        )

    app.include_router(health_router)
    app.include_router(jobs_router, prefix="/v1")
    app.include_router(projects_router, prefix="/v1")

    return app


app = create_app()


@app.get("/")
def root():
    return {"service": "koa-doc-pipeline", "env": settings.ENV}
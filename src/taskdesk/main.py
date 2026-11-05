import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response

from taskdesk.config import get_settings
from taskdesk.logging_config import configure_logging
from taskdesk.routes import router

logger = structlog.get_logger()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_json)

    app = FastAPI(title="Taskdesk", version="0.1.0")

    @app.get("/", tags=["Health"])
    def root() -> dict[str, str]:
        return {
            "message": "Welcome to TaskDesk API",
            "status": "running",
            "documentation": "/docs",
        }

    @app.get("/health", tags=["Health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", uuid4().hex)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        started = time.perf_counter()
        response = await call_next(request)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((time.perf_counter() - started) * 1000, 2),
        )

        response.headers["x-request-id"] = request_id
        return response

    app.include_router(router)

    return app


app = create_app()

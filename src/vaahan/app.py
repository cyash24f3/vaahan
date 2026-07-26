from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import RequestResponseEndpoint

from vaahan import __version__
from vaahan.backends.base import InferenceBackend
from vaahan.backends.llama_server import LlamaServerBackend
from vaahan.config import Settings
from vaahan.logging_config import configure_logging
from vaahan.manifest import ReleaseManifest, load_manifest
from vaahan.metrics import RuntimeMetrics
from vaahan.rate_limit import SlidingWindowLimiter
from vaahan.schema import AnalyzeRequest, AnalyzeResponse, ErrorBody
from vaahan.service import AnalysisService, InvalidModelOutputError, QueueFullError

logger = logging.getLogger("vaahan.api")


def create_app(
    settings: Settings | None = None,
    backend: InferenceBackend | None = None,
    manifest: ReleaseManifest | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    manifest = manifest or load_manifest(settings.manifest_path)
    metrics = RuntimeMetrics()
    limiter = SlidingWindowLimiter(settings.rate_limit_per_minute)
    runtime_backend = backend or LlamaServerBackend(settings, manifest)
    service = AnalysisService(
        runtime_backend,
        manifest,
        metrics,
        settings.queue_timeout_seconds,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await runtime_backend.start()
        metrics.model_ready.set(1)
        try:
            yield
        finally:
            metrics.model_ready.set(0)
            await runtime_backend.stop()

    app = FastAPI(
        title="VAHAAN",
        summary="Portable serving and release engineering for SETU",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
    )
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    async def require_key(x_api_key: str | None = Header(default=None)) -> None:
        if settings.api_key is not None and x_api_key != settings.api_key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")

    @app.middleware("http")
    async def request_context(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        client = request.client.host if request.client else "unknown"
        if request.url.path.startswith("/v1/") and not limiter.allow(client):
            metrics.requests.labels(outcome="rate_limited").inc()
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content=ErrorBody(
                    code="rate_limited",
                    message="request limit exceeded",
                    request_id=request_id,
                ).model_dump(),
                headers={"X-Request-ID": request_id},
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s latency_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    @app.exception_handler(QueueFullError)
    async def queue_full(request: Request, _: QueueFullError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorBody(
                code="queue_full",
                message="The model is busy. Retry shortly.",
                request_id=request.state.request_id,
            ).model_dump(),
        )

    @app.exception_handler(InvalidModelOutputError)
    async def invalid_output(request: Request, _: InvalidModelOutputError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorBody(
                code="invalid_model_output",
                message="The model returned an invalid structured response.",
                request_id=request.state.request_id,
            ).model_dump(),
        )

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health/live", tags=["operations"])
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["operations"])
    async def ready() -> JSONResponse:
        code = status.HTTP_200_OK if runtime_backend.ready else status.HTTP_503_SERVICE_UNAVAILABLE
        return JSONResponse(status_code=code, content={"ready": runtime_backend.ready})

    @app.get("/v1/version", dependencies=[Depends(require_key)], tags=["release"])
    async def version() -> dict[str, str]:
        return {
            "service_version": __version__,
            "release": manifest.release,
            "model": manifest.model_id,
            "quantization": manifest.quantization,
            "schema_version": manifest.schema_version,
            "prompt_version": manifest.prompt_version,
            "llama_cpp_revision": manifest.runtime.llama_cpp_revision,
        }

    @app.post(
        "/v1/analyze",
        response_model=AnalyzeResponse,
        dependencies=[Depends(require_key)],
        responses={
            429: {"model": ErrorBody},
            502: {"model": ErrorBody},
            503: {"model": ErrorBody},
        },
        tags=["inference"],
    )
    async def analyze(payload: AnalyzeRequest, request: Request) -> AnalyzeResponse:
        if payload.request_id is None:
            payload.request_id = request.state.request_id
        return await service.analyze(payload)

    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics() -> Response:
        return Response(metrics.render(), media_type="text/plain; version=0.0.4")

    return app


app = create_app()


def run() -> None:
    configure_logging()
    uvicorn.run("vaahan.app:app", host="0.0.0.0", port=7860, workers=1)

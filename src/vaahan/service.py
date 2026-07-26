from __future__ import annotations

import asyncio
import json
import time
import uuid

from pydantic import ValidationError

from vaahan.backends.base import InferenceBackend
from vaahan.manifest import ReleaseManifest
from vaahan.metrics import RuntimeMetrics
from vaahan.prompting import build_prompt
from vaahan.schema import AnalyzeRequest, AnalyzeResponse, ResponseMetadata, SetuOutput


class QueueFullError(RuntimeError):
    pass


class InvalidModelOutputError(RuntimeError):
    pass


class AnalysisService:
    def __init__(
        self,
        backend: InferenceBackend,
        manifest: ReleaseManifest,
        metrics: RuntimeMetrics,
        queue_timeout_seconds: float,
    ) -> None:
        self.backend = backend
        self.manifest = manifest
        self.metrics = metrics
        self.queue_timeout_seconds = queue_timeout_seconds
        self._semaphore = asyncio.Semaphore(manifest.runtime.parallel)

    async def analyze(self, request: AnalyzeRequest) -> AnalyzeResponse:
        request_id = request.request_id or str(uuid.uuid4())
        try:
            await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.queue_timeout_seconds,
            )
        except TimeoutError as exc:
            self.metrics.requests.labels(outcome="queue_full").inc()
            raise QueueFullError("model queue is full") from exc

        started = time.perf_counter()
        self.metrics.inflight.inc()
        try:
            raw = await self.backend.complete(
                build_prompt(request.message),
                self.manifest.runtime.max_output_tokens,
            )
            try:
                payload = json.loads(raw)
                result = SetuOutput.model_validate(payload)
            except (json.JSONDecodeError, ValidationError) as exc:
                self.metrics.requests.labels(outcome="invalid_model_output").inc()
                raise InvalidModelOutputError("model output failed strict validation") from exc
            latency_ms = (time.perf_counter() - started) * 1000
            self.metrics.requests.labels(outcome="ok").inc()
            self.metrics.latency.observe(latency_ms / 1000)
            return AnalyzeResponse(
                result=result,
                metadata=ResponseMetadata(
                    request_id=request_id,
                    release=self.manifest.release,
                    model=self.manifest.model_id,
                    quantization=self.manifest.quantization,
                    schema_version=self.manifest.schema_version,
                    prompt_version=self.manifest.prompt_version,
                    latency_ms=round(latency_ms, 1),
                ),
            )
        finally:
            self.metrics.inflight.dec()
            self._semaphore.release()

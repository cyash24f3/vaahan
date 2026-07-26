from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class RuntimeMetrics:
    def __init__(self) -> None:
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "vaahan_requests_total",
            "Requests by outcome",
            ["outcome"],
            registry=self.registry,
        )
        self.latency = Histogram(
            "vaahan_request_duration_seconds",
            "End-to-end request duration",
            registry=self.registry,
        )
        self.inflight = Gauge(
            "vaahan_inflight_requests",
            "Requests currently executing",
            registry=self.registry,
        )
        self.model_ready = Gauge(
            "vaahan_model_ready",
            "Whether the model backend is ready",
            registry=self.registry,
        )

    def render(self) -> bytes:
        return generate_latest(self.registry)

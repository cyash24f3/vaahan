from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from vaahan.config import Settings
from vaahan.manifest import ReleaseManifest, load_manifest


@pytest.fixture
def manifest() -> ReleaseManifest:
    return load_manifest(Path(__file__).parents[1] / "release" / "manifest.yaml")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        manifest_path=Path(__file__).parents[1] / "release" / "manifest.yaml",
        llama_binary="llama-server",
        backend_host="127.0.0.1",
        backend_port=18082,
        model_cache=tmp_path,
        api_key=None,
        rate_limit_per_minute=30,
        queue_timeout_seconds=0.05,
        startup_timeout_seconds=1,
    )


class FakeBackend:
    def __init__(self, output: str) -> None:
        self.output = output
        self._ready = False
        self.prompts: list[str] = []

    @property
    def ready(self) -> bool:
        return self._ready

    async def start(self) -> None:
        self._ready = True

    async def stop(self) -> None:
        self._ready = False

    async def complete(self, prompt: str, max_tokens: int) -> str:
        self.prompts.append(prompt)
        return self.output


@pytest.fixture
def valid_output() -> str:
    return (
        '{"intent":"complaint","category":"payments","issue_type":"upi_failed",'
        '"urgency":"medium","sentiment":"negative","language_mix":"balanced",'
        '"order_id":null,"product_name":null,"payment_method":"upi",'
        '"resolution_requested":"information"}'
    )


@pytest.fixture
def fake_backend(valid_output: str) -> Iterator[FakeBackend]:
    yield FakeBackend(valid_output)

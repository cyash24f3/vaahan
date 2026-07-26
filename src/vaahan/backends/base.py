from __future__ import annotations

from typing import Protocol


class InferenceBackend(Protocol):
    @property
    def ready(self) -> bool: ...

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    async def complete(self, prompt: str, max_tokens: int) -> str: ...

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    manifest_path: Path
    llama_binary: str
    backend_host: str
    backend_port: int
    model_cache: Path
    api_key: str | None
    rate_limit_per_minute: int
    queue_timeout_seconds: float
    startup_timeout_seconds: float

    @classmethod
    def from_env(cls) -> Settings:
        root = _repository_root()
        return cls(
            manifest_path=Path(
                os.getenv("VAHAAN_MANIFEST", str(root / "release" / "manifest.yaml"))
            ),
            llama_binary=os.getenv("VAHAAN_LLAMA_BINARY", "llama-server"),
            backend_host="127.0.0.1",
            backend_port=int(os.getenv("VAHAAN_BACKEND_PORT", "8082")),
            model_cache=Path(os.getenv("VAHAAN_MODEL_CACHE", str(root / "artifacts" / "models"))),
            api_key=os.getenv("VAHAAN_API_KEY") or None,
            rate_limit_per_minute=int(os.getenv("VAHAAN_RATE_LIMIT", "30")),
            queue_timeout_seconds=float(os.getenv("VAHAAN_QUEUE_TIMEOUT", "0.25")),
            startup_timeout_seconds=float(os.getenv("VAHAAN_STARTUP_TIMEOUT", "180")),
        )

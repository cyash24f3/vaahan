from __future__ import annotations

import hashlib
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class HubArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_id: str
    revision: str
    filename: str
    sha256: str


class LocalArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    sha256: str


class RuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    llama_cpp_revision: str
    context_size: int = Field(ge=256, le=4096)
    max_output_tokens: int = Field(ge=32, le=512)
    threads: int = Field(ge=1, le=64)
    parallel: int = Field(ge=1, le=4)
    request_timeout_seconds: float = Field(gt=0, le=300)


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    release: str
    model_id: str
    quantization: str
    schema_version: str
    prompt_version: str
    base: HubArtifact
    adapter: LocalArtifact
    runtime: RuntimeConfig
    evaluation_report: str
    predecessor: str | None


def load_manifest(path: Path) -> ReleaseManifest:
    with path.open(encoding="utf-8") as stream:
        return ReleaseManifest.model_validate(yaml.safe_load(stream))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path.name}: expected {expected}, got {actual}")

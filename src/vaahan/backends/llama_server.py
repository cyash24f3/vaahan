from __future__ import annotations

import asyncio
import logging
import secrets
from pathlib import Path

import httpx
from huggingface_hub import hf_hub_download

from vaahan.config import Settings
from vaahan.manifest import ReleaseManifest, verify_file

logger = logging.getLogger("vaahan.backend")


class LlamaServerBackend:
    def __init__(self, settings: Settings, manifest: ReleaseManifest) -> None:
        self.settings = settings
        self.manifest = manifest
        self._process: asyncio.subprocess.Process | None = None
        self._client: httpx.AsyncClient | None = None
        self._ready = False
        self._internal_key = secrets.token_urlsafe(24)
        self._log_task: asyncio.Task[None] | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    def _resolve_adapter(self) -> Path:
        path = self.settings.manifest_path.parent.parent / self.manifest.adapter.path
        verify_file(path, self.manifest.adapter.sha256)
        return path

    def _resolve_model(self) -> Path:
        self.settings.model_cache.mkdir(parents=True, exist_ok=True)
        path = Path(
            hf_hub_download(
                repo_id=self.manifest.base.repo_id,
                filename=self.manifest.base.filename,
                revision=self.manifest.base.revision,
                local_dir=self.settings.model_cache,
            )
        )
        verify_file(path, self.manifest.base.sha256)
        return path

    async def _drain_logs(self) -> None:
        if self._process is None or self._process.stderr is None:
            return
        while line := await self._process.stderr.readline():
            message = line.decode(errors="replace").strip()
            if message:
                logger.info("llama_server event=%s", message[:500])

    async def start(self) -> None:
        model_path = await asyncio.to_thread(self._resolve_model)
        adapter_path = await asyncio.to_thread(self._resolve_adapter)
        runtime = self.manifest.runtime
        command = [
            self.settings.llama_binary,
            "--model",
            str(model_path),
            "--lora",
            str(adapter_path),
            "--host",
            self.settings.backend_host,
            "--port",
            str(self.settings.backend_port),
            "--ctx-size",
            str(runtime.context_size),
            "--threads",
            str(runtime.threads),
            "--threads-batch",
            str(runtime.threads),
            "--parallel",
            str(runtime.parallel),
            "--api-key",
            self._internal_key,
            "--no-webui",
            "--metrics",
            "--reasoning",
            "off",
            "--reasoning-format",
            "none",
            "--log-verbosity",
            "1",
        ]
        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        self._log_task = asyncio.create_task(self._drain_logs())
        self._client = httpx.AsyncClient(
            base_url=f"http://{self.settings.backend_host}:{self.settings.backend_port}",
            headers={"Authorization": f"Bearer {self._internal_key}"},
            timeout=runtime.request_timeout_seconds,
        )
        deadline = asyncio.get_running_loop().time() + self.settings.startup_timeout_seconds
        while asyncio.get_running_loop().time() < deadline:
            if self._process.returncode is not None:
                raise RuntimeError(f"llama-server exited with code {self._process.returncode}")
            try:
                response = await self._client.get("/health")
                if response.status_code == 200:
                    self._ready = True
                    return
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.25)
        raise TimeoutError("llama-server did not become ready before the startup deadline")

    async def stop(self) -> None:
        self._ready = False
        if self._client is not None:
            await self._client.aclose()
        if self._process is not None and self._process.returncode is None:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=10)
            except TimeoutError:
                self._process.kill()
                await self._process.wait()
        if self._log_task is not None:
            await self._log_task

    async def complete(self, prompt: str, max_tokens: int) -> str:
        if not self._ready or self._client is None:
            raise RuntimeError("model backend is not ready")
        response = await self._client.post(
            "/completion",
            json={
                "prompt": prompt,
                "temperature": 0,
                "n_predict": max_tokens,
                "seed": 42,
                "cache_prompt": True,
                "stream": False,
            },
        )
        response.raise_for_status()
        payload = response.json()
        content = payload.get("content")
        if not isinstance(content, str):
            raise RuntimeError("backend returned no text completion")
        return content

from __future__ import annotations

import pytest
from conftest import FakeBackend

from vaahan.metrics import RuntimeMetrics
from vaahan.schema import AnalyzeRequest
from vaahan.service import AnalysisService, InvalidModelOutputError


async def test_service_returns_release_metadata(manifest, valid_output: str) -> None:
    backend = FakeBackend(valid_output)
    service = AnalysisService(backend, manifest, RuntimeMetrics(), 0.05)
    response = await service.analyze(AnalyzeRequest(message="UPI se payment fail hai"))
    assert response.result.issue_type == "upi_failed"
    assert response.metadata.release == "setu-2b-v1.0.0"
    assert len(backend.prompts) == 1


async def test_service_rejects_invalid_model_output(manifest) -> None:
    service = AnalysisService(FakeBackend("not-json"), manifest, RuntimeMetrics(), 0.05)
    with pytest.raises(InvalidModelOutputError):
        await service.analyze(AnalyzeRequest(message="UPI se payment fail hai"))

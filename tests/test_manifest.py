from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from vaahan.manifest import verify_file


def test_verify_file_accepts_matching_checksum(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"setu")
    expected = hashlib.sha256(b"setu").hexdigest()
    verify_file(artifact, expected)


def test_verify_file_rejects_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"setu")
    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_file(artifact, "0" * 64)

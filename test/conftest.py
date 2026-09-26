"""Shared pytest fixtures and sys.path setup.

version 1.0 by Albert Sheng
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pipeline as pl  # noqa: E402


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def data_root(repo_root) -> Path:
    p = repo_root / "image_AI_Ni"
    if not p.is_dir():
        pytest.skip(f"dataset root not present: {p}")
    return p


@pytest.fixture(scope="session")
def sample_txt(data_root) -> Path:
    """A known-good XANES txt with clean Ni signal.
    Prefer Z6_1/X0_5_1_120 (the guideline reference, e0 ≈ 8346 eV).
    Fall back to any parseable txt so tests still run on partial datasets."""
    preferred = data_root / "Z6_1" / "X0_5_1_120_XANES.txt"
    if preferred.exists():
        return preferred
    for txt in sorted(data_root.rglob("X*_XANES.txt")):
        if pl.FNAME_RE.match(txt.name):
            return txt
    pytest.skip(f"no XANES sample found under {data_root}")


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Redirect pipeline cache roots into tmp_path for isolation."""
    data = tmp_path / "data"
    image = tmp_path / "image"
    monkeypatch.setattr(pl, "DATA_ROOT", data)
    monkeypatch.setattr(pl, "IMAGE_ROOT", image)
    return {"data": data, "image": image}

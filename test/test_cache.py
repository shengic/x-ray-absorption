"""Cache round-trip: .npz arrays and .json metrics.

version 1.0 by Albert Sheng
"""
from __future__ import annotations

import json

import numpy as np
import pytest

pytest.importorskip("larch")

import pipeline as pl  # noqa: E402


BUNDLE_KEYS = (
    "energy", "mu", "mu_ref",
    "pre_edge", "post_edge", "norm", "flat",
    "e0", "edge_step",
)


def test_bundle_contains_all_expected_arrays(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    bundle = pl.cache_bundle(sec)
    assert bundle is not None
    for k in BUNDLE_KEYS:
        assert k in bundle, k


def test_bundle_arrays_equal_length(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    b = pl.cache_bundle(sec)
    n = len(b["energy"])
    for k in ("mu", "mu_ref", "pre_edge", "post_edge", "norm", "flat"):
        assert len(b[k]) == n, k


def test_bundle_energy_preserved(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    original_e, _, _ = pl.load_xanes(sample_txt)
    b = pl.cache_bundle(sec)
    # float32 round-trip; allow modest tolerance
    assert np.allclose(b["energy"], original_e.astype(np.float32), atol=1e-2)


def test_meta_json_matches_returned_metrics(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    meta_returned = pl.process_section(sec)
    meta_loaded = pl.load_meta(sec)
    assert meta_loaded["e0"] == meta_returned["e0"]
    assert meta_loaded["edge_step"] == meta_returned["edge_step"]
    assert meta_loaded["q5_glitches"] == meta_returned["q5_glitches"]


def test_meta_json_includes_pre_edge_parameters(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    meta = json.loads(sec.json_path.read_text(encoding="utf-8"))
    for k in ("pre1", "pre2", "norm1", "norm2", "nnorm", "nvict"):
        assert k in meta, k


def test_cache_bundle_returns_none_when_absent(tmp_cache):
    """Section pointing at a file that has never been processed."""
    from pathlib import Path
    fake_root = Path("nowhere")
    sec = pl.parse_section(fake_root / "Z5_0" / "X5_0_1_120_XANES.txt", fake_root)
    assert sec is not None
    assert pl.cache_bundle(sec) is None
    assert pl.load_meta(sec) is None

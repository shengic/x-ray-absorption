"""End-to-end pipeline: pre_edge → metrics → cache → PNGs.

Requires xraylarch. Skipped otherwise.

version 1.0 by Albert Sheng
"""
from __future__ import annotations

import time

import pytest

pytest.importorskip("larch")

import pipeline as pl  # noqa: E402


def test_run_pre_edge_group_has_expected_fields(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    for attr in ("e0", "edge_step", "pre_edge", "post_edge", "norm", "flat",
                 "pre_edge_details"):
        assert hasattr(g, attr), attr
    for attr in ("pre1", "pre2", "norm1", "norm2", "nnorm", "nvict"):
        assert hasattr(g.pre_edge_details, attr), attr


def test_e0_in_ni_k_edge_range(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    # Ni K-edge nominal 8333 eV; monochromator offset typically < 30 eV
    assert 8320 < float(g.e0) < 8380, float(g.e0)


def test_edge_step_reasonable(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    step = float(g.edge_step)
    assert 0.05 < step < 5.0, step


def test_arrays_same_length(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    n = len(e)
    assert len(g.pre_edge) == n
    assert len(g.post_edge) == n
    assert len(g.norm) == n
    assert len(g.flat) == n


def test_process_section_writes_all_artifacts(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    meta = pl.process_section(sec)
    assert sec.npz_path.exists()
    assert sec.json_path.exists()
    assert sec.preedge_png.exists()
    assert sec.norm_png.exists()
    assert meta["edge_step"] > 0
    assert 8000 < meta["e0"] < 9500


def test_process_section_cache_hit_is_no_op(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    mtime = sec.npz_path.stat().st_mtime
    time.sleep(0.05)
    pl.process_section(sec)
    assert sec.npz_path.stat().st_mtime == mtime


def test_process_section_force_overwrites(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    m1 = sec.npz_path.stat().st_mtime
    time.sleep(0.05)
    pl.process_section(sec, force=True)
    m2 = sec.npz_path.stat().st_mtime
    assert m2 > m1


def test_pngs_have_content(sample_txt, data_root, tmp_cache):
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    assert sec.preedge_png.stat().st_size > 1024
    assert sec.norm_png.stat().st_size > 1024


def test_meta_includes_fwhm_and_norm_coefs(sample_txt, data_root, tmp_cache):
    """v1.2 addition: edge_fwhm_eV + pre_slope + norm_c0/c1/c2 must land in JSON meta."""
    import json
    sec = pl.parse_section(sample_txt, data_root)
    pl.process_section(sec)
    meta = json.loads(sec.json_path.read_text(encoding="utf-8"))
    assert 0.1 < meta["edge_fwhm_eV"] < 20.0
    for k in ("pre_slope", "norm_c0", "norm_c1", "norm_c2"):
        assert k in meta, k


def test_edge_fwhm_eV_helper_on_synthetic_arctan():
    """FWHM of arctan-based derivative should be a few eV; sanity."""
    import numpy as np
    e = np.linspace(8300, 8400, 2001)
    mu = 0.5 * (0.5 + np.arctan((e - 8346.0) / 2.0) / np.pi)
    fwhm = pl.edge_fwhm_eV(e, mu, e0=8346.0, window=15.0)
    assert 3.0 < fwhm < 10.0

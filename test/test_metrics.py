"""Quality-metric calculations. Requires larch.

version 1.0 by Albert Sheng
"""
from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("larch")

import pipeline as pl  # noqa: E402


METRIC_KEYS = (
    "e0", "edge_step",
    "q1_edge_step", "q2_hf_noise", "q3_pre_flatness",
    "q4_e0_shift_vs_ref", "q5_glitches", "q6_white_line",
)


def test_all_metric_keys_present(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    m = pl.compute_metrics(g)
    for k in METRIC_KEYS:
        assert k in m, k


def test_q1_equals_edge_step(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    m = pl.compute_metrics(g)
    assert m["q1_edge_step"] == m["edge_step"]


def test_q4_none_without_ref(sample_txt):
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    m = pl.compute_metrics(g)
    assert m["q4_e0_shift_vs_ref"] is None


def test_q4_computed_with_ref(sample_txt):
    e, mu, mr = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    g_ref = pl.run_pre_edge(e, mr)
    m = pl.compute_metrics(g, mu_ref_e0=float(g_ref.e0))
    assert m["q4_e0_shift_vs_ref"] is not None
    assert isinstance(m["q4_e0_shift_vs_ref"], float)


def test_metrics_finite_on_real_section(sample_txt):
    e, mu, mr = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    m = pl.compute_metrics(g, mu_ref_e0=float(pl.run_pre_edge(e, mr).e0))
    assert np.isfinite(m["e0"])
    assert np.isfinite(m["edge_step"])
    assert np.isfinite(m["q2_hf_noise"])
    assert np.isfinite(m["q3_pre_flatness"])
    assert np.isfinite(m["q6_white_line"])
    assert m["q5_glitches"] >= 0


def test_q6_white_line_above_baseline(sample_txt):
    """White line peak of normalized spectrum should exceed 1.0."""
    e, mu, _ = pl.load_xanes(sample_txt)
    g = pl.run_pre_edge(e, mu)
    m = pl.compute_metrics(g)
    assert m["q6_white_line"] > 1.0


def test_decide_usable_rejects_tiny_step():
    m = {"edge_step": 0.01, "q2_hf_noise": 0.001, "q5_glitches": 0}
    assert pl.decide_usable(m) is False


def test_decide_usable_accepts_clean_section():
    m = {"edge_step": 0.5, "q2_hf_noise": 0.001, "q5_glitches": 2}
    assert pl.decide_usable(m) is True


def test_decide_usable_rejects_many_glitches():
    m = {"edge_step": 0.5, "q2_hf_noise": 0.001, "q5_glitches": 100}
    assert pl.decide_usable(m) is False


def test_decide_usable_rejects_high_noise():
    m = {"edge_step": 0.5, "q2_hf_noise": 0.1, "q5_glitches": 2}
    assert pl.decide_usable(m) is False

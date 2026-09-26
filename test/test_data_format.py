"""Raw XANES txt structural checks (no larch needed).

version 1.0 by Albert Sheng
"""
from __future__ import annotations

import numpy as np

import pipeline as pl


def test_load_xanes_returns_three_arrays(sample_txt):
    e, mu, mr = pl.load_xanes(sample_txt)
    assert e.shape == mu.shape == mr.shape


def test_energy_length_near_4000(sample_txt):
    e, _, _ = pl.load_xanes(sample_txt)
    assert 3500 <= len(e) <= 4500, f"unexpected point count {len(e)}"


def test_energy_monotonic_increasing(sample_txt):
    e, _, _ = pl.load_xanes(sample_txt)
    assert np.all(np.diff(e) > 0)


def test_energy_in_expected_ni_range(sample_txt):
    """Per guideline §3: ~8058-9241 eV for Ni K-edge dataset."""
    e, _, _ = pl.load_xanes(sample_txt)
    assert 7900 < e[0] < 8100
    assert 9200 < e[-1] < 9400


def test_all_values_finite(sample_txt):
    e, mu, mr = pl.load_xanes(sample_txt)
    assert np.all(np.isfinite(e))
    assert np.all(np.isfinite(mu))
    assert np.all(np.isfinite(mr))


def test_mu_variation_present(sample_txt):
    """A real absorption spectrum should have edge-like variation, not flat."""
    _, mu, _ = pl.load_xanes(sample_txt)
    assert float(np.ptp(mu)) > 0.1

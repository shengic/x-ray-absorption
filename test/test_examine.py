"""Examine engine + rule dispatch tests, using synthetic cell metadata.

Does NOT run larch — writes pipeline-shaped .json + .npz files by hand into
a tmp_path, then exercises examine.run_examine end-to-end.

version 1.0.0 by Albert Sheng
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest

import pipeline as pl
import rules as rl


yaml = pytest.importorskip("yaml")
import examine  # noqa: E402


# --------- Synthetic data helpers ---------

BASE_CONFIG = {
    "grid": {"n": 11},
    "edge": {
        "element": "Ni", "edge": "K",
        "e0_nominal_eV": 8333.0,
        "e0_alt_eV": 8331.90,
        "e0_nominal_tol_eV": 1.5,
        "mono_offset_window_eV": [-5.0, 25.0],
        "ref_e0_search_eV": [8320.0, 8370.0],
        "ref_e0_spread_tol_eV": 0.3,
    },
    "examine": {"combine_mode": "worst",
                "shape_grid_eV": [-30.0, 150.0, 0.3]},
    "rules": {
        "GATE-EDGE":  {"enabled": True, "min": 0.10, "max": 1.5},
        "CAL-EREF":   {"enabled": True},
        "R-SNR":      {"enabled": True, "warn_z": 3, "fail_z": 5},
        "R-NOISE-HF": {"enabled": True, "warn_z": 3, "fail_z": 5},
        "R-PRE-FLAT": {"enabled": True, "warn_z": 3, "fail_z": 5},
        "R-GLITCH":   {"enabled": True, "warn_z": 3, "fail_z": 5, "max_count": 5},
        "C-SHAPE":    {"enabled": True, "warn_z": 3, "fail_z": 5},
        "C-E0-NBR":   {"enabled": True, "warn_z": 3, "fail_z": 5},
    },
}


def _make_spectrum(e0: float = 8346.0, noise_sigma: float = 0.005,
                   n_glitches: int = 0, rng: np.random.Generator | None = None):
    """arctan edge + gaussian white line + optional white noise & glitches."""
    rng = rng or np.random.default_rng(0)
    e = np.linspace(8058.0, 9241.0, 4000)
    edge = 0.5 * (0.5 + np.arctan((e - e0) / 2.0) / np.pi)
    wl = 0.25 * np.exp(-((e - (e0 + 4.0)) ** 2) / (2 * 2.0 ** 2))
    baseline = -0.6 - 0.0002 * (e - 8000)
    mu = baseline + edge + wl + rng.normal(0, noise_sigma, size=e.shape)
    if n_glitches:
        idx = rng.choice(len(e), size=n_glitches, replace=False)
        mu[idx] += 0.5
    mu_ref = baseline + 0.5 * (0.5 + np.arctan((e - 8333.0) / 2.0) / np.pi) \
             + rng.normal(0, noise_sigma, size=e.shape)
    return e, mu, mu_ref


def _write_synthetic_cell(dataset_root: Path, data_root: Path,
                           i: int, j: int, *,
                           edge_step: float = 0.5,
                           q2_hf_noise: float = 0.001,
                           q3_pre_flatness: float = 0.005,
                           q5_glitches: int = 0,
                           q6_white_line: float = 1.25,
                           e0: float = 8346.0,
                           mu_ref_e0: float = 8333.10,
                           norm: np.ndarray | None = None,
                           energy: np.ndarray | None = None) -> None:
    """Write a pipeline-shaped .npz + .json for one synthetic cell."""
    z, x = i - 5, 5 - j
    stem = f"X{j}_{x}_1_120"
    zdir = f"Z{i}_{z}"
    fname = f"{stem}_XANES.txt"

    # Fake source txt file so parse_section works
    (dataset_root / zdir).mkdir(parents=True, exist_ok=True)
    (dataset_root / zdir / fname).write_text("# stub\n", encoding="utf-8")

    if energy is None:
        e, mu, mu_ref = _make_spectrum(e0=e0)
    else:
        e = energy
        mu = np.zeros_like(e); mu_ref = np.zeros_like(e)
    if norm is None:
        # simple normalized-like curve
        norm = 0.5 + 0.5 * np.arctan((e - e0) / 2.0) / (np.pi / 2)
    flat = norm.copy()

    npz_dir = data_root / zdir
    npz_dir.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        npz_dir / f"{stem}.npz",
        energy=e.astype(np.float32),
        mu=mu.astype(np.float32),
        mu_ref=mu_ref.astype(np.float32),
        pre_edge=np.zeros_like(e, dtype=np.float32),
        post_edge=np.zeros_like(e, dtype=np.float32),
        norm=norm.astype(np.float32),
        flat=flat.astype(np.float32),
        e0=np.float32(e0),
        edge_step=np.float32(edge_step),
    )
    meta = {
        "zdir": zdir, "fname": fname,
        "i": i, "j": j, "z": z, "x": x,
        "seg_start": 1, "seg_end": 120,
        "pre1": -288.0, "pre2": -144.0, "norm1": 25.0, "norm2": 895.0,
        "nnorm": 2, "nvict": 0,
        "e0": e0, "edge_step": edge_step,
        "q1_edge_step": edge_step,
        "q2_hf_noise": q2_hf_noise,
        "q3_pre_flatness": q3_pre_flatness,
        "q4_e0_shift_vs_ref": e0 - mu_ref_e0,
        "q5_glitches": q5_glitches,
        "q6_white_line": q6_white_line,
        "mu_ref_e0": mu_ref_e0,
        "usable": True,
    }
    (npz_dir / f"{stem}.json").write_text(json.dumps(meta, indent=2),
                                            encoding="utf-8")


@pytest.fixture
def synthetic_grid(tmp_path, monkeypatch):
    """Build a full 11x11 clean baseline grid under isolated cache roots.
    Small jitter in Q values keeps MAD > 0 so z-scores are defined."""
    dataset_root = tmp_path / "raw"
    data_root = tmp_path / "data"
    image_root = tmp_path / "image"
    monkeypatch.setattr(pl, "DATA_ROOT", data_root)
    monkeypatch.setattr(pl, "IMAGE_ROOT", image_root)
    rng = np.random.default_rng(42)
    for i in range(11):
        for j in range(11):
            _write_synthetic_cell(
                dataset_root, data_root, i, j,
                q2_hf_noise=float(0.001 + rng.normal(0, 5e-5)),
                q3_pre_flatness=float(0.005 + rng.normal(0, 2e-4)),
                q5_glitches=int(rng.integers(0, 3)),
                edge_step=float(0.5 + rng.normal(0, 0.02)),
                mu_ref_e0=float(8333.10 + rng.normal(0, 0.05)),
                e0=float(8346.0 + rng.normal(0, 0.05)),
            )
    return {"dataset_root": dataset_root, "data_root": data_root}


def _cfg():
    return copy.deepcopy(BASE_CONFIG)


# --------- Tests ---------

def test_registry_contains_all_8_rules():
    for rid in ("GATE-EDGE", "CAL-EREF", "R-SNR", "R-NOISE-HF", "R-PRE-FLAT",
                "R-GLITCH", "C-SHAPE", "C-E0-NBR"):
        assert rid in rl.REGISTRY, rid


def test_clean_grid_all_pass(synthetic_grid):
    cfg = _cfg()
    run = examine.run_examine(synthetic_grid["dataset_root"], cfg,
                              data_root=synthetic_grid["data_root"])
    assert run.n_cells == 121
    n_usable = sum(1 for v in run.verdicts.values() if v["usable"])
    assert n_usable == 121


def test_noise_injection_fails_smooth(synthetic_grid):
    root = synthetic_grid["dataset_root"]
    data = synthetic_grid["data_root"]
    _write_synthetic_cell(root, data, i=5, j=5, q2_hf_noise=0.05)  # ~50x baseline
    cfg = _cfg()
    run = examine.run_examine(root, cfg, data_root=data)
    v = run.verdicts[(5, 5)]
    assert v["rules"]["R-NOISE-HF"]["level_name"] in ("WARN", "FAIL")
    assert v["smooth"] in ("WARN", "FAIL")


def test_gate_edge_fails_and_excluded_from_baseline(synthetic_grid):
    root = synthetic_grid["dataset_root"]
    data = synthetic_grid["data_root"]
    _write_synthetic_cell(root, data, i=3, j=3, edge_step=0.02)
    cfg = _cfg()
    run = examine.run_examine(root, cfg, data_root=data)
    v = run.verdicts[(3, 3)]
    assert v["rules"]["GATE-EDGE"]["level_name"] == "FAIL"
    assert v["usable"] is False


def test_glitches_flagged(synthetic_grid):
    root = synthetic_grid["dataset_root"]
    data = synthetic_grid["data_root"]
    _write_synthetic_cell(root, data, i=7, j=2, q5_glitches=10)
    cfg = _cfg()
    run = examine.run_examine(root, cfg, data_root=data)
    v = run.verdicts[(7, 2)]
    assert v["rules"]["R-GLITCH"]["level_name"] in ("WARN", "FAIL")


def test_disable_cal_eref_propagates_na_to_consistent(synthetic_grid):
    cfg = _cfg()
    cfg["rules"]["CAL-EREF"]["enabled"] = False
    run = examine.run_examine(synthetic_grid["dataset_root"], cfg,
                              data_root=synthetic_grid["data_root"])
    v = run.verdicts[(5, 5)]
    # C-SHAPE and C-E0-NBR require CAL-EREF; both should be N/A when CAL-EREF
    # is disabled — reason should include the require id.
    for rid in ("C-SHAPE", "C-E0-NBR"):
        r = v["rules"][rid]
        assert r["level"] is None
        assert "CAL-EREF" in r["reason"]


def test_disable_all_smooth_rules_yields_na_and_not_usable(synthetic_grid):
    cfg = _cfg()
    for rid in ("R-SNR", "R-NOISE-HF", "R-PRE-FLAT", "R-GLITCH"):
        cfg["rules"][rid]["enabled"] = False
    run = examine.run_examine(synthetic_grid["dataset_root"], cfg,
                              data_root=synthetic_grid["data_root"])
    v = run.verdicts[(5, 5)]
    assert v["smooth"] == "N/A"
    assert v["usable"] is False


def test_config_hash_deterministic_and_sensitive(synthetic_grid):
    cfg1 = _cfg()
    cfg2 = _cfg()
    assert examine.canonical_config_hash(cfg1) == examine.canonical_config_hash(cfg2)
    cfg2["rules"]["R-SNR"]["warn_z"] = 4
    assert examine.canonical_config_hash(cfg1) != examine.canonical_config_hash(cfg2)


def test_examine_persists_per_cell_and_run_json(synthetic_grid):
    run = examine.run_examine(synthetic_grid["dataset_root"], _cfg(),
                              data_root=synthetic_grid["data_root"])
    data_root = synthetic_grid["data_root"]
    assert (data_root / "examine_run.json").exists()
    # A couple of examine.json sidecars
    p = data_root / "Z5_0" / "X5_0_1_120.examine.json"
    assert p.exists()
    per = json.loads(p.read_text(encoding="utf-8"))
    assert per["run_id"] == run.run_id
    assert per["smooth"] in ("PASS", "WARN", "FAIL", "N/A")
    assert per["consistent"] in ("PASS", "WARN", "FAIL", "N/A")


def test_coord_mapping_corners(synthetic_grid):
    """Naming invariants at extremes."""
    run = examine.run_examine(synthetic_grid["dataset_root"], _cfg(),
                              data_root=synthetic_grid["data_root"])
    v_top_left = run.verdicts[(10, 10)]     # z=+5, x=-5
    assert (v_top_left["z"], v_top_left["x"]) == (5, -5)
    assert v_top_left["zdir"] == "Z10_5"
    v_bot_right = run.verdicts[(0, 0)]      # z=-5, x=+5
    assert (v_bot_right["z"], v_bot_right["x"]) == (-5, 5)
    assert v_bot_right["zdir"] == "Z0_-5"

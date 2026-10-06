"""GUI smoke test for main2.py: imports, hover report, heatmap cell scan.

`hover_report` is a pure function and is tested without Tk. The viewer and
`_scan_cells` tests are skipped when no Tk display is available.

version 1.1.0 by Albert Sheng
"""
from __future__ import annotations

import json
import sys

import pytest

pytest.importorskip("matplotlib")
tk = pytest.importorskip("tkinter")

import pipeline as pl  # noqa: E402

META = {
    "zdir": "Z6_1", "fname": "X0_5_1_120_XANES.txt",
    "i": 6, "j": 0, "z": 1, "x": 5,
    "seg_start": 1, "seg_end": 120,
    "pre1": -285.0, "pre2": -142.5, "norm1": 25.0, "norm2": 930.0,
    "nnorm": 2, "nvict": 0,
    "pre_slope": -5.33e-4, "norm_c0": 8.08, "norm_c1": -1.84e-3,
    "norm_c2": 1.09e-7,
    "e0": 8346.2, "edge_step": 0.26208,
    "q1_edge_step": 0.26208, "q2_hf_noise": 0.00232,
    "q3_pre_flatness": 0.000425, "q4_e0_shift_vs_ref": 13.41,
    "q5_glitches": 6, "q6_white_line": 1.7318,
    "edge_fwhm_eV": 7.375, "mu_ref_e0": 8332.79, "usable": True,
}


def test_module_imports():
    if "main2" in sys.modules:
        del sys.modules["main2"]
    import main2
    assert hasattr(main2, "HoverHeatmapViewer")
    assert hasattr(main2, "hover_report")
    assert issubclass(main2.HoverHeatmapViewer, __import__("main").XANESViewer)


def test_hover_report_without_examine():
    import main2
    txt = main2.hover_report(META, None)
    assert "Z6_1/X0_5_1_120_XANES.txt" in txt
    assert "(x, z) = (+5, +1)" in txt
    assert "8346.20 eV" in txt          # E0
    assert "8332.79 eV" in txt          # mu_ref E0
    assert "0.2621" in txt              # edge step
    assert "7.38 eV" in txt             # edge FWHM
    assert "E0-285.0" in txt            # pre-edge window
    assert "nnorm=2" in txt
    assert "not run" in txt             # examine section


def test_hover_report_lists_flagged_rules():
    import main2
    examine = {
        "smooth": "FAIL", "smooth_evaluated": 6, "smooth_enabled": 6,
        "consistent": "PASS", "consistent_evaluated": 2,
        "consistent_enabled": 2, "usable": False,
        "rules": {
            "GATE-EDGE": {"level": 0, "level_name": "PASS",
                          "value": 0.26, "reason": "ok"},
            "R-NOISE-HF": {"level": 2, "level_name": "FAIL",
                           "value": 5.4, "reason": "z=+5.40 > fail_z"},
            "R-GLITCH": {"level": None, "level_name": "N/A",
                         "value": None, "reason": "requires GATE-EDGE"},
        },
    }
    txt = main2.hover_report(META, examine)
    assert "smooth\tFAIL (6/6)" in txt
    assert "FAIL R-NOISE-HF" in txt
    assert "z=+5.40 > fail_z" in txt
    assert "R-GLITCH" not in txt        # N/A is not "flagged"
    assert "GATE-EDGE" not in txt       # PASS is not "flagged"


def test_hover_report_uses_tab_stops_not_space_padding():
    """The GUI renders this in Georgia (proportional), so the value column is
    aligned by a Tk tab stop. Space padding would look ragged."""
    import main2
    txt = main2.hover_report(META, None)
    for label in ("E0 sample", "edge step dmu0", "Q2 hf noise RMS",
                  "usable (legacy)"):
        assert f"{label}\t" in txt
    # no run of 2+ spaces used as a column separator before a value
    assert "E0 sample  " not in txt
    assert main2.REPORT_TAB > 0


def test_hover_report_tolerates_legacy_cache():
    """Caches written before pipeline v1.2 lack edge_fwhm_eV / norm coeffs."""
    import main2
    legacy = {k: v for k, v in META.items()
              if k not in ("edge_fwhm_eV", "pre_slope",
                           "norm_c0", "norm_c1", "norm_c2")}
    txt = main2.hover_report(legacy, None)
    assert "n/a" in txt
    assert "Z6_1/X0_5_1_120_XANES.txt" in txt


def test_scan_cells_grid_orientation(tk_window, tmp_path, monkeypatch):
    """grid[i, 10 - j] must match main.py so the image is identical."""
    import main
    import main2
    monkeypatch.setattr(main.filedialog, "askdirectory", lambda **kw: "")
    cache = tmp_path / "data" / "Z6_1"
    cache.mkdir(parents=True)
    (cache / "X0_5_1_120.json").write_text(json.dumps(META), encoding="utf-8")
    monkeypatch.setattr(pl, "DATA_ROOT", tmp_path / "data")

    viewer = main2.HoverHeatmapViewer(tk_window)
    tk_window.update()
    grid, labels, index = viewer._scan_cells("edge_step", False)

    assert grid.shape == (11, 11)
    assert grid[6, 10 - 0] == pytest.approx(0.26208)
    assert labels == {}                       # continuous mode, no text
    assert (6, 0) in index
    assert index[(6, 0)]["meta"]["fname"] == "X0_5_1_120_XANES.txt"
    assert index[(6, 0)]["examine"] is None


def test_viewer_instantiates_and_is_georgia(tk_window, monkeypatch):
    import main
    import main2
    monkeypatch.setattr(main.filedialog, "askdirectory", lambda **kw: "")
    viewer = main2.HoverHeatmapViewer(tk_window)
    tk_window.update()
    tk_window.update_idletasks()
    assert viewer.dataset_root is None
    assert viewer.current_section is None
    assert viewer._cell_index == {}
    assert viewer._hover_xz is None
    # all-Georgia: the widgets main.py pinned to Consolas are restyled
    assert "Georgia" in str(viewer.lb_z.cget("font"))
    assert "Georgia" in str(viewer.info_text.cget("font"))

"""GUI smoke test: main.py imports cleanly and XANESViewer instantiates.

Skipped if matplotlib / Tk display is not available.

version 1.1 by Albert Sheng (use shared tk_window fixture)
"""
from __future__ import annotations

import sys

import pytest

pytest.importorskip("matplotlib")
tk = pytest.importorskip("tkinter")


def test_main_module_imports():
    if "main" in sys.modules:
        del sys.modules["main"]
    import main
    assert hasattr(main, "XANESViewer")
    assert hasattr(main, "run_batch")
    assert hasattr(main, "main")


def test_run_batch_signature():
    import main
    import inspect
    sig = inspect.signature(main.run_batch)
    assert "root" in sig.parameters


def test_xanes_viewer_class_init_signature():
    import main
    import inspect
    sig = inspect.signature(main.XANESViewer.__init__)
    assert "root" in sig.parameters


def test_viewer_instantiates_without_crash(tk_window, monkeypatch):
    """Instantiate the viewer and cancel the directory dialog immediately.

    `tk_window` is a Toplevel on the session-wide Tk root (see conftest) --
    creating a second `tk.Tk()` here made the suite flaky on Windows."""
    import main
    # Cancel the auto-prompted folder dialog so no user interaction is needed
    monkeypatch.setattr(main.filedialog, "askdirectory", lambda **kw: "")
    viewer = main.XANESViewer(tk_window)
    # Let scheduled after() callbacks fire
    tk_window.update()
    tk_window.update_idletasks()
    assert viewer.dataset_root is None  # cancelled dialog
    assert viewer.current_section is None

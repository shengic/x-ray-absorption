"""GUI smoke test: main.py imports cleanly and XANESViewer instantiates.

Skipped if matplotlib / Tk display is not available.

version 1.0 by Albert Sheng
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


def test_viewer_instantiates_without_crash(monkeypatch):
    """Instantiate the viewer, cancel the directory dialog immediately, then destroy."""
    try:
        root = tk.Tk()
    except tk.TclError as e:
        pytest.skip(f"no Tk display available: {e}")
    try:
        import main
        # Cancel the auto-prompted folder dialog so no user interaction is needed
        monkeypatch.setattr(main.filedialog, "askdirectory", lambda **kw: "")
        viewer = main.XANESViewer(root)
        # Let scheduled after() callbacks fire
        root.update()
        root.update_idletasks()
        assert viewer.dataset_root is None  # cancelled dialog
        assert viewer.current_section is None
    finally:
        root.destroy()

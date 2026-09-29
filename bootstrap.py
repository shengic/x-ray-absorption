"""
Cross-drive portable launcher for the NiXZ-121 XANES Analyzer.

Ensures the local `.venv` is functional (rebuilds it from scratch when it
is not) and that `requirements.txt` is installed, then hands off to
`main.py` with all remaining argv.

Why this exists
---------------
Windows console-script launchers inside a virtualenv (`.venv\\Scripts\\
python.exe`, `pip.exe`, `pytest.exe`) are compiled binaries with the
originating interpreter's absolute path baked in. If the project folder
is moved between drive letters (e.g. `I:` -> `J:`), or if the base
Python is uninstalled or reinstalled at a different location, every one
of those launchers dies with a cryptic error such as:

    Fatal error in launcher: Unable to create process using
    '"C:\\Program Files\\Python312\\python.exe" ...'

Repairing a venv in that state is not worth the trouble. This
bootstrapper detects the failure, deletes the stale `.venv`, rebuilds it
using whichever Python interpreter *is* currently available, installs
`requirements.txt`, and only then runs the app. On subsequent launches
the check is a fast no-op.

Usage
-----
    python bootstrap.py                          # start the GUI
    python bootstrap.py --batch image_AI_Ni      # forward CLI args
    python bootstrap.py --examine image_AI_Ni

The Windows one-click launcher `run.bat` calls this file. On macOS or
Linux, invoke it directly with any system Python 3.11+.

version 1.0 by Albert Sheng
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQ_FILE = PROJECT_ROOT / "requirements.txt"
MAIN_ENTRY = PROJECT_ROOT / "main.py"

MIN_PYTHON = (3, 11)


def venv_python() -> Path:
    """Path to the venv's python.exe (Windows) or python (POSIX)."""
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_is_functional() -> bool:
    """Return True iff the venv's python launches successfully.
    Catches every failure mode: missing file, broken launcher, wrong
    interpreter (numpy ABI mismatch would show at import time -- but
    here we only check that Python itself can run)."""
    py = venv_python()
    if not py.exists():
        return False
    try:
        result = subprocess.run(
            [str(py), "-c",
             "import sys, importlib.util; "
             "assert sys.version_info >= (3, 11); "
             "assert importlib.util.find_spec('numpy'), 'numpy missing'; "
             "assert importlib.util.find_spec('matplotlib'), 'matplotlib missing'; "
             "assert importlib.util.find_spec('larch'), 'larch missing'"],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def python_version_ok(python_exe: str = sys.executable) -> bool:
    try:
        result = subprocess.run(
            [python_exe, "-c",
             f"import sys; sys.exit(0 if sys.version_info >= "
             f"{MIN_PYTHON} else 1)"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def rebuild_venv() -> None:
    """Delete any existing `.venv` and create a fresh one using the
    currently running Python interpreter."""
    if VENV_DIR.exists():
        print(f"Removing stale .venv at {VENV_DIR}...", flush=True)
        shutil.rmtree(VENV_DIR, ignore_errors=True)
        # rmtree may leave locked launcher exes behind on Windows; try again
        if VENV_DIR.exists():
            shutil.rmtree(VENV_DIR)
    print(f"Creating fresh .venv at {VENV_DIR} "
          f"(Python {sys.version.split()[0]})...", flush=True)
    venv.create(VENV_DIR, with_pip=True, clear=True)


def install_requirements() -> None:
    """Install requirements.txt into the venv."""
    if not REQ_FILE.exists():
        print(f"[bootstrap] requirements.txt not found at {REQ_FILE}",
              file=sys.stderr)
        sys.exit(1)
    print("Installing dependencies from requirements.txt "
          "(this can take several minutes on first run)...", flush=True)
    subprocess.run(
        [str(venv_python()), "-m", "pip", "install",
         "--upgrade", "pip"],
        check=True,
    )
    subprocess.run(
        [str(venv_python()), "-m", "pip", "install",
         "-r", str(REQ_FILE)],
        check=True,
    )


def hand_off(argv: list[str]) -> int:
    """Run main.py inside the venv with the given argv."""
    if not MAIN_ENTRY.exists():
        print(f"[bootstrap] main.py not found at {MAIN_ENTRY}",
              file=sys.stderr)
        return 1
    result = subprocess.run(
        [str(venv_python()), str(MAIN_ENTRY), *argv],
    )
    return result.returncode


def main() -> int:
    if not python_version_ok():
        print(f"[bootstrap] Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ required; "
              f"currently running {sys.version.split()[0]}", file=sys.stderr)
        return 1

    if not venv_is_functional():
        print("[bootstrap] .venv is missing or broken; rebuilding.",
              flush=True)
        rebuild_venv()
        install_requirements()
        print("[bootstrap] .venv ready.", flush=True)
    return hand_off(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())

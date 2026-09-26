"""
NiXZ-121 XANES processing pipeline.

Discovers sections, runs larch pre_edge(), computes Q1-Q6 quality metrics,
and caches results:

    data/{Zdir}/{stem}.npz    -- energy, mu, mu_ref, pre_edge, post_edge, norm, flat
    data/{Zdir}/{stem}.json   -- scalar metrics + parameters
    image/{Zdir}/{stem}_preedge.png
    image/{Zdir}/{stem}_norm.png

where {stem} = "X{j}_{x}_{start}_{end}".

version 1.2 by Albert Sheng
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

PIPELINE_VERSION = "1.2"

DATA_ROOT = Path("data")
IMAGE_ROOT = Path("image")

FNAME_RE = re.compile(r"^X(\d+)_(-?\d+)_(\d+)_(\d+)_XANES\.txt$")
ZDIR_RE = re.compile(r"^Z(\d+)_(-?\d+)$")


@dataclass(frozen=True)
class Section:
    root: Path
    zdir: str
    fname: str
    i: int
    j: int
    z: int
    x: int
    seg_start: int
    seg_end: int

    @property
    def txt_path(self) -> Path:
        return self.root / self.zdir / self.fname

    @property
    def stem(self) -> str:
        return f"X{self.j}_{self.x}_{self.seg_start}_{self.seg_end}"

    @property
    def npz_path(self) -> Path:
        return DATA_ROOT / self.zdir / f"{self.stem}.npz"

    @property
    def json_path(self) -> Path:
        return DATA_ROOT / self.zdir / f"{self.stem}.json"

    @property
    def preedge_png(self) -> Path:
        return IMAGE_ROOT / self.zdir / f"{self.stem}_preedge.png"

    @property
    def norm_png(self) -> Path:
        return IMAGE_ROOT / self.zdir / f"{self.stem}_norm.png"


def parse_section(txt: Path, root: Path) -> Section | None:
    fm = FNAME_RE.match(txt.name)
    zm = ZDIR_RE.match(txt.parent.name)
    if not fm or not zm:
        return None
    return Section(
        root=root, zdir=txt.parent.name, fname=txt.name,
        i=int(zm[1]), z=int(zm[2]),
        j=int(fm[1]), x=int(fm[2]),
        seg_start=int(fm[3]), seg_end=int(fm[4]),
    )


def discover_z_dirs(root: Path) -> list[Path]:
    return sorted(
        (p for p in root.iterdir() if p.is_dir() and ZDIR_RE.match(p.name)),
        key=lambda p: int(ZDIR_RE.match(p.name)[1]),
    )


def discover_x_files(z_dir: Path) -> list[Path]:
    """Return X sections sorted by j. Windows glob is case-insensitive, so
    filter strictly by FNAME_RE to drop malformed names (e.g. lowercase x)."""
    def _key(p: Path) -> int:
        m = FNAME_RE.match(p.name)
        return int(m[1]) if m else 999
    return sorted(
        (p for p in z_dir.glob("X*_XANES.txt") if FNAME_RE.match(p.name)),
        key=_key,
    )


def load_xanes(path: Path):
    d = np.loadtxt(path, comments="#")
    return d[:, 1], d[:, 2], d[:, 3]  # energy, mu, mu_ref


def run_pre_edge(energy, mu):
    from larch import Group
    from larch.xafs import pre_edge
    g = Group(energy=np.asarray(energy, dtype=float),
              mu=np.asarray(mu, dtype=float))
    pre_edge(g)
    return g


def edge_fwhm_eV(energy: np.ndarray, mu: np.ndarray, e0: float,
                  window: float = 15.0) -> float:
    """FWHM (in eV) of the dμ/dE peak inside E0 ± window. Sub-pixel linear
    interpolation on the half-max crossings. Returns NaN if the derivative
    peak isn't well defined in the window."""
    energy = np.asarray(energy, dtype=float)
    mu = np.asarray(mu, dtype=float)
    mask = (energy >= e0 - window) & (energy <= e0 + window)
    e = energy[mask]
    if len(e) < 5:
        return float("nan")
    d = np.gradient(mu[mask], e)
    peak_val = float(np.max(d))
    if peak_val <= 0:
        return float("nan")
    peak_idx = int(np.argmax(d))
    half = peak_val / 2.0

    left_idx = None
    for i in range(peak_idx, -1, -1):
        if d[i] <= half:
            left_idx = i
            break
    right_idx = None
    for i in range(peak_idx, len(d)):
        if d[i] <= half:
            right_idx = i
            break
    if left_idx is None or right_idx is None:
        return float("nan")

    def _crossing(i0: int, i1: int) -> float:
        if d[i1] == d[i0]:
            return 0.5 * (e[i0] + e[i1])
        t = (half - d[i0]) / (d[i1] - d[i0])
        return float(e[i0] + t * (e[i1] - e[i0]))

    e_left = _crossing(left_idx, left_idx + 1) if left_idx + 1 <= peak_idx else float(e[left_idx])
    e_right = _crossing(right_idx - 1, right_idx) if right_idx - 1 >= peak_idx else float(e[right_idx])
    return e_right - e_left


def compute_metrics(g, mu_ref_e0: float | None = None) -> dict:
    e0 = float(g.e0)
    step = float(g.edge_step)
    energy = np.asarray(g.energy)
    mu = np.asarray(g.mu)
    pre = np.asarray(g.pre_edge)
    norm = np.asarray(g.norm)
    flat = np.asarray(g.flat)

    det = g.pre_edge_details
    pre_mask = (energy >= (e0 + det.pre1)) & (energy <= (e0 + det.pre2))
    q3 = float(np.sqrt(np.mean((mu[pre_mask] - pre[pre_mask]) ** 2))) \
         if pre_mask.any() else float("nan")

    exafs = energy >= (e0 + 150)
    if exafs.sum() > 10:
        d2 = np.diff(flat[exafs], n=2)
        q2 = float(np.sqrt(np.mean(d2 ** 2)))
        diffs = np.diff(flat[exafs])
        med = np.median(diffs)
        sigma = float(np.median(np.abs(diffs - med)) * 1.4826)
        q5 = int(np.sum(np.abs(diffs - med) > 5 * sigma)) if sigma > 0 else 0
    else:
        q2 = float("nan")
        q5 = -1

    wl = (energy >= e0 - 5) & (energy <= e0 + 30)
    q6 = float(np.max(norm[wl])) if wl.any() else float("nan")

    q4 = float(e0 - mu_ref_e0) if mu_ref_e0 is not None else None

    fwhm = edge_fwhm_eV(energy, mu, e0, window=15.0)

    return {
        "e0": e0,
        "edge_step": step,
        "q1_edge_step": step,
        "q2_hf_noise": q2,
        "q3_pre_flatness": q3,
        "q4_e0_shift_vs_ref": q4,
        "q5_glitches": q5,
        "q6_white_line": q6,
        "edge_fwhm_eV": fwhm,
    }


def decide_usable(m: dict) -> bool:
    """Preliminary heuristic; refine with 121-section MAD statistics later."""
    if m["edge_step"] < 0.05:
        return False
    q2 = m.get("q2_hf_noise")
    if q2 is not None and not np.isnan(q2) and q2 > 0.02:
        return False
    if m.get("q5_glitches", 0) > 30:
        return False
    return True


def plot_preedge_fig(bundle, title: str):
    from matplotlib.figure import Figure
    fig = Figure(figsize=(6.5, 4.5), dpi=100)
    ax = fig.add_subplot(111)
    e = bundle["energy"]
    ax.plot(e, bundle["mu"], label=r"$\mu(E)$", lw=1.0)
    ax.plot(e, bundle["pre_edge"], "--", label="pre-edge line", lw=1.0)
    ax.plot(e, bundle["post_edge"], "--", label="post-edge curve", lw=1.0)
    e0 = float(bundle["e0"])
    step = float(bundle["edge_step"])
    ax.set_title(f"Pre-edge subtraction  ($E_0$={e0:.2f} eV, step={step:.4f})")
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel(r"$\mu(E)$")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_norm_fig(bundle, title: str):
    from matplotlib.figure import Figure
    fig = Figure(figsize=(6.5, 4.5), dpi=100)
    ax = fig.add_subplot(111)
    e = bundle["energy"]
    ax.plot(e, bundle["norm"], label="normalized", lw=1.0)
    ax.plot(e, bundle["flat"], label="flattened", lw=1.0)
    ax.set_title("Normalized / flattened")
    ax.set_xlabel("Energy (eV)")
    ax.set_ylabel(r"normalized $\mu(E)$")
    ax.grid(alpha=0.3)
    ax.legend(loc="best")
    fig.suptitle(title)
    fig.tight_layout()
    return fig


def plot_combined_fig(bundle, title: str):
    """Single Figure with pre-edge subtraction (left) and normalized/flattened
    (right) side by side, matching the reference image.png layout."""
    from matplotlib.figure import Figure
    fig = Figure(figsize=(12.5, 4.6), dpi=100)
    e = bundle["energy"]
    e0 = float(bundle["e0"])
    step = float(bundle["edge_step"])

    ax1 = fig.add_subplot(121)
    ax1.plot(e, bundle["mu"], label=r"$\mu(E)$", lw=1.0)
    ax1.plot(e, bundle["pre_edge"], "--", label="pre-edge line", lw=1.0)
    ax1.plot(e, bundle["post_edge"], "--", label="post-edge curve", lw=1.0)
    ax1.set_title(f"Pre-edge subtraction  ($E_0$={e0:.2f} eV, step={step:.4f})")
    ax1.set_xlabel("Energy (eV)")
    ax1.set_ylabel(r"$\mu(E)$")
    ax1.grid(alpha=0.3)
    ax1.legend(loc="best")

    ax2 = fig.add_subplot(122)
    ax2.plot(e, bundle["norm"], label="normalized", lw=1.0)
    ax2.plot(e, bundle["flat"], label="flattened", lw=1.0)
    ax2.set_title("Normalized / flattened")
    ax2.set_xlabel("Energy (eV)")
    ax2.set_ylabel(r"normalized $\mu(E)$")
    ax2.grid(alpha=0.3)
    ax2.legend(loc="best")

    fig.suptitle(title)
    fig.tight_layout()
    return fig


def cache_bundle(sec: Section) -> dict | None:
    if not sec.npz_path.exists():
        return None
    with np.load(sec.npz_path) as npz:
        return {k: npz[k] for k in npz.files}


def load_meta(sec: Section) -> dict | None:
    if not sec.json_path.exists():
        return None
    return json.loads(sec.json_path.read_text(encoding="utf-8"))


def process_section(sec: Section, force: bool = False) -> dict:
    """Full pipeline: load, pre_edge, metrics, save arrays + JSON + PNGs.
    Returns metrics dict. Uses cache unless force=True."""
    have_cache = (sec.npz_path.exists() and sec.json_path.exists()
                  and sec.preedge_png.exists() and sec.norm_png.exists())
    if not force and have_cache:
        return load_meta(sec)  # type: ignore[return-value]

    energy, mu, mu_ref = load_xanes(sec.txt_path)
    g = run_pre_edge(energy, mu)
    g_ref = run_pre_edge(energy, mu_ref)

    metrics = compute_metrics(g, mu_ref_e0=float(g_ref.e0))
    metrics["mu_ref_e0"] = float(g_ref.e0)
    metrics["usable"] = decide_usable(metrics)

    det = g.pre_edge_details
    meta = {
        "zdir": sec.zdir, "fname": sec.fname,
        "i": sec.i, "j": sec.j, "z": sec.z, "x": sec.x,
        "seg_start": sec.seg_start, "seg_end": sec.seg_end,
        "pre1": float(det.pre1), "pre2": float(det.pre2),
        "norm1": float(det.norm1), "norm2": float(det.norm2),
        "nnorm": int(det.nnorm), "nvict": int(det.nvict),
        "pre_slope": float(det.pre_slope),
        "norm_c0": float(det.norm_c0),
        "norm_c1": float(det.norm_c1),
        "norm_c2": float(getattr(det, "norm_c2", 0.0)),
        **metrics,
    }

    sec.npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        sec.npz_path,
        energy=np.asarray(energy, dtype=np.float32),
        mu=np.asarray(mu, dtype=np.float32),
        mu_ref=np.asarray(mu_ref, dtype=np.float32),
        pre_edge=np.asarray(g.pre_edge, dtype=np.float32),
        post_edge=np.asarray(g.post_edge, dtype=np.float32),
        norm=np.asarray(g.norm, dtype=np.float32),
        flat=np.asarray(g.flat, dtype=np.float32),
        e0=np.float32(metrics["e0"]),
        edge_step=np.float32(metrics["edge_step"]),
    )
    sec.json_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    import larch as _larch
    title = f"{sec.stem} — Ni K-edge, larch {_larch.__version__} pre_edge()"
    bundle = cache_bundle(sec)
    sec.preedge_png.parent.mkdir(parents=True, exist_ok=True)
    fig1 = plot_preedge_fig(bundle, title)
    fig1.savefig(sec.preedge_png)
    fig2 = plot_norm_fig(bundle, title)
    fig2.savefig(sec.norm_png)
    del fig1, fig2

    return meta

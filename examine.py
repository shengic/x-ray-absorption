"""
NiXZ-121 examine engine.

Load cached pipeline outputs, apply rules in topological order, and write
per-cell verdicts + a run manifest.

Outputs:
    data/{Zdir}/{stem}.examine.json     -- {run_id, smooth, consistent, usable, rules{...}}
    data/examine_run.json               -- {run_id, computed_at, config, config_hash, ...}

CLI:
    python main.py --examine ROOT       (see main.py)

version 1.0.0 by Albert Sheng
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import pipeline as pl
import rules as rl


CONFIG_PATH_DEFAULT = Path("config.yaml")


# ---------- config ----------

def load_config(path: Path = CONFIG_PATH_DEFAULT) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def canonical_config_hash(config: dict) -> str:
    """sha256 of canonical (sorted-keys) JSON dump."""
    blob = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------- cell wrapper ----------

@dataclass
class Cell:
    section: pl.Section
    meta: dict
    npz_path: Path

    @property
    def key(self) -> tuple[int, int]:
        return (self.section.i, self.section.j)

    def bundle(self) -> dict | None:
        return pl.cache_bundle(self.section)


# ---------- context ----------

@dataclass
class Context:
    edge_cfg: dict
    examine_cfg: dict
    cells: dict[tuple[int, int], Cell] = field(default_factory=dict)
    gate_pass: set[tuple[int, int]] = field(default_factory=set)
    mu_ref_e0_median: float | None = None
    mu_ref_shift: dict[tuple[int, int], float] = field(default_factory=dict)
    stats: dict[str, dict] = field(default_factory=dict)     # field -> {median, mad_scaled}
    shape_r: dict[tuple[int, int], float] = field(default_factory=dict)
    n_med: np.ndarray | None = None
    common_energy: np.ndarray | None = None
    e0_nbr_diff: dict[tuple[int, int], float] = field(default_factory=dict)


# ---------- helpers ----------

def _robust_mad_scaled(vals: np.ndarray) -> float:
    if len(vals) == 0:
        return 0.0
    med = np.median(vals)
    return float(np.median(np.abs(vals - med)) * 1.4826)


def _stats_of(vals: list[float]) -> dict:
    arr = np.asarray([v for v in vals if v is not None and not np.isnan(v)],
                     dtype=float)
    if len(arr) == 0:
        return {"median": None, "mad_scaled": 0.0, "n": 0}
    return {"median": float(np.median(arr)),
            "mad_scaled": _robust_mad_scaled(arr),
            "n": int(len(arr))}


def _load_cells(data_root: Path, dataset_root: Path) -> dict[tuple[int, int], Cell]:
    """Scan data/{Zdir}/*.json and pair with source sections."""
    cells: dict[tuple[int, int], Cell] = {}
    for jf in data_root.rglob("*.json"):
        if jf.name == "examine_run.json" or jf.name.endswith(".examine.json"):
            continue
        try:
            meta = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:
            continue
        zdir = meta.get("zdir")
        fname = meta.get("fname")
        if not zdir or not fname:
            continue
        txt_path = dataset_root / zdir / fname
        sec = pl.parse_section(txt_path, dataset_root)
        if sec is None:
            continue
        cells[(sec.i, sec.j)] = Cell(section=sec, meta=meta, npz_path=sec.npz_path)
    return cells


def _run_gate_edge(ctx: Context, params: dict) -> dict[tuple[int, int], rl.RuleResult]:
    results = {}
    for k, cell in ctx.cells.items():
        res = rl.REGISTRY["GATE-EDGE"].fn(ctx, cell, params)
        results[k] = res
        if res.level == rl.PASS:
            ctx.gate_pass.add(k)
    return results


def _compute_mu_ref_stats(ctx: Context) -> None:
    vals = [ctx.cells[k].meta.get("mu_ref_e0")
            for k in ctx.gate_pass
            if ctx.cells[k].meta.get("mu_ref_e0") is not None]
    if not vals:
        return
    ctx.mu_ref_e0_median = float(np.median(vals))
    for k in ctx.gate_pass:
        ref = ctx.cells[k].meta.get("mu_ref_e0")
        if ref is not None:
            ctx.mu_ref_shift[k] = float(ref) - ctx.mu_ref_e0_median


def _compute_shape_context(ctx: Context, cal_pass: set[tuple[int, int]]) -> None:
    """Interpolate all cal_pass cells' norm onto common grid, compute n_med and
    per-cell residual r = sum((n-n_med)^2)/sum(n_med^2)."""
    if not cal_pass:
        return
    lo, hi, step = ctx.examine_cfg.get("shape_grid_eV", [-30.0, 150.0, 0.3])
    e0_meds = [ctx.cells[k].meta["e0"] - ctx.mu_ref_shift.get(k, 0.0) for k in cal_pass]
    e0_med = float(np.median(e0_meds))
    grid = np.arange(e0_med + lo, e0_med + hi + step * 0.5, step, dtype=float)
    ctx.common_energy = grid

    interpolated: dict[tuple[int, int], np.ndarray] = {}
    for k in cal_pass:
        cell = ctx.cells[k]
        b = cell.bundle()
        if b is None:
            continue
        e = np.asarray(b["energy"], dtype=float) - ctx.mu_ref_shift.get(k, 0.0)
        norm = np.asarray(b["norm"], dtype=float)
        if e[0] > grid[0] or e[-1] < grid[-1]:
            continue                                           # doesn't cover
        interpolated[k] = np.interp(grid, e, norm)
    if not interpolated:
        return
    stack = np.vstack(list(interpolated.values()))
    n_med = np.median(stack, axis=0)
    ctx.n_med = n_med
    denom = float(np.sum(n_med ** 2)) or 1.0
    for k, n in interpolated.items():
        ctx.shape_r[k] = float(np.sum((n - n_med) ** 2) / denom)


def _compute_e0_nbr(ctx: Context, cal_pass: set[tuple[int, int]]) -> None:
    for k in cal_pass:
        i, j = k
        nbrs = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                nk = (i + di, j + dj)
                if nk in cal_pass:
                    c = ctx.cells[nk]
                    e0c = c.meta["e0"] - ctx.mu_ref_shift.get(nk, 0.0)
                    nbrs.append(e0c)
        if len(nbrs) >= 2:
            e0_self = ctx.cells[k].meta["e0"] - ctx.mu_ref_shift.get(k, 0.0)
            ctx.e0_nbr_diff[k] = float(e0_self - float(np.median(nbrs)))


def _compute_stats(ctx: Context) -> None:
    """Baseline stats over gate-passing cells for each Q field + derived."""
    q2 = [ctx.cells[k].meta.get("q2_hf_noise") for k in ctx.gate_pass]
    q3 = [ctx.cells[k].meta.get("q3_pre_flatness") for k in ctx.gate_pass]
    q5 = [ctx.cells[k].meta.get("q5_glitches") for k in ctx.gate_pass]
    snr = []
    for k in ctx.gate_pass:
        m = ctx.cells[k].meta
        s, p = m.get("edge_step"), m.get("q3_pre_flatness")
        if s is not None and p is not None and p > 0:
            snr.append(float(s) / float(p))
    ctx.stats["q2_hf_noise"] = _stats_of(q2)
    ctx.stats["q3_pre_flatness"] = _stats_of(q3)
    ctx.stats["q5_glitches"] = _stats_of([float(v) if v is not None else None for v in q5])
    ctx.stats["snr"] = _stats_of(snr)
    ctx.stats["shape_r"] = _stats_of(list(ctx.shape_r.values()))
    ctx.stats["e0_nbr_diff"] = _stats_of(list(ctx.e0_nbr_diff.values()))


# ---------- main entry ----------

@dataclass
class ExamineRun:
    run_id: str
    computed_at: str
    config_hash: str
    verdicts: dict[tuple[int, int], dict]     # per-cell verdict dict
    n_cells: int
    stats: dict


def run_examine(dataset_root: Path, config: dict,
                data_root: Path | None = None) -> ExamineRun:
    data_root = data_root or pl.DATA_ROOT
    run_id = str(uuid.uuid4())
    computed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cfg_hash = canonical_config_hash(config)

    ctx = Context(edge_cfg=config.get("edge", {}),
                  examine_cfg=config.get("examine", {}))
    ctx.cells = _load_cells(data_root, dataset_root)
    if not ctx.cells:
        raise RuntimeError(f"no cached cells found under {data_root}")

    rules_cfg = config.get("rules", {})
    enabled = {rid: bool(rules_cfg.get(rid, {}).get("enabled", False))
               for rid in rl.REGISTRY.keys()}
    params_map = {rid: rules_cfg.get(rid, {}) for rid in rl.REGISTRY.keys()}

    per_cell_results: dict[tuple[int, int], dict[str, rl.RuleResult]] = {
        k: {} for k in ctx.cells
    }

    # 1. GATE-EDGE (always runs; if disabled, treated as PASS for all)
    if enabled.get("GATE-EDGE", True):
        gate_results = _run_gate_edge(ctx, params_map["GATE-EDGE"])
        for k, res in gate_results.items():
            per_cell_results[k]["GATE-EDGE"] = res
    else:
        for k in ctx.cells:
            per_cell_results[k]["GATE-EDGE"] = rl.RuleResult(
                None, None, "GATE-EDGE disabled"
            )
            ctx.gate_pass.add(k)

    # 2. CAL-EREF: median stats + per-cell result
    _compute_mu_ref_stats(ctx)
    cal_pass = set()
    if enabled.get("CAL-EREF", True):
        for k, cell in ctx.cells.items():
            res = rl.REGISTRY["CAL-EREF"].fn(ctx, cell, params_map["CAL-EREF"])
            per_cell_results[k]["CAL-EREF"] = res
            if k in ctx.gate_pass and res.level in (rl.PASS, rl.WARN):
                cal_pass.add(k)
    else:
        for k in ctx.cells:
            per_cell_results[k]["CAL-EREF"] = rl.RuleResult(
                None, None, "CAL-EREF disabled"
            )
        cal_pass = set(ctx.gate_pass)   # treat as pass-through if disabled

    # 3. Precompute grid stats
    _compute_shape_context(ctx, cal_pass)
    _compute_e0_nbr(ctx, cal_pass)
    _compute_stats(ctx)

    # 4. All remaining rules in topological order (requires resolved).
    remaining_ids = [rid for rid in rl.REGISTRY if rid not in ("GATE-EDGE", "CAL-EREF")]
    ordered = _topo_sort(remaining_ids)
    for rid in ordered:
        r = rl.REGISTRY[rid]
        for k, cell in ctx.cells.items():
            # Skip if any required rule is disabled or non-PASS
            skip_reason = None
            for req in r.requires:
                if not enabled.get(req, False):
                    skip_reason = f"requires {req} (disabled)"
                    break
                req_res = per_cell_results[k].get(req)
                if req_res is None or req_res.level not in (rl.PASS, rl.WARN):
                    skip_reason = f"requires {req} ({rl.LEVEL_NAME[req_res.level if req_res else None]})"
                    break
            if skip_reason:
                per_cell_results[k][rid] = rl.RuleResult(None, None, skip_reason)
                continue
            if not enabled.get(rid, False):
                per_cell_results[k][rid] = rl.RuleResult(None, None, "disabled")
                continue
            per_cell_results[k][rid] = r.fn(ctx, cell, params_map[rid])

    # 5. Combine per cell
    combine_mode = config.get("examine", {}).get("combine_mode", "worst")
    verdicts: dict[tuple[int, int], dict] = {}
    for k, cell in ctx.cells.items():
        r_map = per_cell_results[k]
        s_lvl, s_ev, s_en = rl.combine("smooth", r_map, enabled, combine_mode)
        c_lvl, c_ev, c_en = rl.combine("consistent", r_map, enabled, combine_mode)
        usable = rl.is_usable(s_lvl, r_map.get("GATE-EDGE"))
        verdicts[k] = {
            "run_id": run_id,
            "i": cell.section.i, "j": cell.section.j,
            "z": cell.section.z, "x": cell.section.x,
            "zdir": cell.section.zdir, "stem": cell.section.stem,
            "smooth": rl.LEVEL_NAME[s_lvl],
            "smooth_level": s_lvl,
            "smooth_evaluated": s_ev, "smooth_enabled": s_en,
            "consistent": rl.LEVEL_NAME[c_lvl],
            "consistent_level": c_lvl,
            "consistent_evaluated": c_ev, "consistent_enabled": c_en,
            "usable": bool(usable),
            "rules": {rid: {"level": (r.level if r else None),
                            "level_name": rl.LEVEL_NAME[r.level if r else None],
                            "value": (r.value if r else None),
                            "reason": (r.reason if r else "")}
                      for rid, r in r_map.items()},
        }

    # 6. Persist
    for k, v in verdicts.items():
        cell = ctx.cells[k]
        out = cell.npz_path.parent / f"{cell.section.stem}.examine.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(v, indent=2, default=_json_default),
                       encoding="utf-8")

    run_manifest = {
        "run_id": run_id,
        "computed_at": computed_at,
        "pipeline_version": getattr(pl, "PIPELINE_VERSION", "unknown"),
        "config_hash": cfg_hash,
        "config": config,
        "combine_mode": combine_mode,
        "n_cells": len(ctx.cells),
        "gate_pass": len(ctx.gate_pass),
        "stats": {k: v for k, v in ctx.stats.items()},
    }
    (data_root / "examine_run.json").write_text(
        json.dumps(run_manifest, indent=2, default=_json_default),
        encoding="utf-8",
    )

    return ExamineRun(
        run_id=run_id, computed_at=computed_at, config_hash=cfg_hash,
        verdicts=verdicts, n_cells=len(ctx.cells), stats=dict(ctx.stats),
    )


def _topo_sort(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    def visit(rid: str):
        if rid in seen or rid not in rl.REGISTRY:
            return
        for req in rl.REGISTRY[rid].requires:
            if req in ids:
                visit(req)
        seen.add(rid)
        out.append(rid)
    for rid in ids:
        visit(rid)
    return out


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer, np.floating)):
        return o.item()
    raise TypeError(f"unhashable {type(o).__name__}")

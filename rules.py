"""
NiXZ-121 examine rules.

Each rule is registered into REGISTRY via @rule(). A rule takes (ctx, cell, params)
and returns RuleResult(level, value, reason).

Levels: PASS(0), WARN(1), FAIL(2), None = N/A.

version 1.3.1 by Albert Sheng
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

PASS: int = 0
WARN: int = 1
FAIL: int = 2
LEVEL_NAME: dict[int | None, str] = {None: "N/A", 0: "PASS", 1: "WARN", 2: "FAIL"}


@dataclass(frozen=True)
class Rule:
    id: str
    flag: str          # 'gate' | 'smooth' | 'consistent'
    scope: str         # 'cell' | 'grid'
    requires: tuple[str, ...]
    fn: Callable       # (ctx, cell, params) -> RuleResult


@dataclass
class RuleResult:
    level: int | None      # None = N/A
    value: float | None
    reason: str


REGISTRY: dict[str, Rule] = {}


def rule(id: str, flag: str, scope: str, requires: tuple[str, ...] = ()):
    def _wrap(fn: Callable) -> Callable:
        REGISTRY[id] = Rule(id=id, flag=flag, scope=scope, requires=requires, fn=fn)
        return fn
    return _wrap


# ---------- helpers ----------

def lippold_c7(spec: np.ndarray, ref: np.ndarray) -> float:
    """Lippold et al. (J. Synchrotron Rad. 12, 45-52, 2005) criterion 7:
    standard deviation of the residual of the cumulative-difference spectrum
    A(j) = Σ_{i≤j}(spec − ref) after a linear regression fit.

    A(j) is a flat line only when spec and ref differ by pure random noise;
    systematic deviations (group shifts, jump discontinuities, slope changes,
    periodic bending — see Lippold Fig. 1b-e) blow up under cumulative
    summation, then the residual after linear detrend quantifies them.

    Inputs must be on the same (energy-corrected) grid. Values are only
    meaningful for relative comparison within one Examine run — the paper's
    absolute stopping threshold (~0.1) is system-specific and does not
    transfer to other datasets.
    """
    a = np.cumsum(np.asarray(spec, dtype=float) - np.asarray(ref, dtype=float))
    x = np.arange(a.size)
    p = np.polyfit(x, a, 1)
    return float(np.std(a - np.polyval(p, x), ddof=2))


def _robust_z(v: float, median: float, mad_scaled: float) -> float | None:
    """z = (v - median) / (1.4826 * MAD). Returns None if MAD == 0."""
    if mad_scaled is None or mad_scaled == 0.0:
        return None
    return (v - median) / mad_scaled


def _upper_z(v: float | None, stats: dict, params: dict, missing_reason: str) -> RuleResult:
    """High values are bad (WARN if z >= warn_z, FAIL if z >= fail_z)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return RuleResult(None, None, missing_reason)
    if not stats:
        return RuleResult(None, float(v), "no baseline stats")
    z = _robust_z(v, stats["median"], stats["mad_scaled"])
    if z is None:
        return RuleResult(None, float(v), "MAD=0")
    warn_z = params.get("warn_z", 3)
    fail_z = params.get("fail_z", 5)
    if z >= fail_z:
        return RuleResult(FAIL, z, f"z=+{z:.2f} > {fail_z}")
    if z >= warn_z:
        return RuleResult(WARN, z, f"z=+{z:.2f} > {warn_z}")
    return RuleResult(PASS, z, f"z={z:+.2f}")


def _two_sided_z(v: float | None, stats: dict, params: dict,
                  missing_reason: str) -> RuleResult:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return RuleResult(None, None, missing_reason)
    if not stats:
        return RuleResult(None, float(v), "no baseline stats")
    z = _robust_z(v, stats["median"], stats["mad_scaled"])
    if z is None:
        return RuleResult(None, float(v), "MAD=0")
    warn_z = params.get("warn_z", 3)
    fail_z = params.get("fail_z", 5)
    az = abs(z)
    if az >= fail_z:
        return RuleResult(FAIL, z, f"|z|={az:.2f} > {fail_z}")
    if az >= warn_z:
        return RuleResult(WARN, z, f"|z|={az:.2f} > {warn_z}")
    return RuleResult(PASS, z, f"z={z:+.2f}")


# ---------- rule implementations ----------

@rule("GATE-EDGE", flag="gate", scope="cell")
def _gate_edge(ctx, cell, params) -> RuleResult:
    """對 edge_step（Δμ₀）設硬邊界。超出 [min, max] 的格子判 FAIL，
    並且不會進入下游規則使用的統計基準（median / MAD）。
    參數：min（下限，預設 0.10，排除未打到樣品的邊緣像素）、
    max（上限，預設 1.5，防厚度效應壓低 white line）。"""
    v = cell.meta.get("edge_step")
    if v is None:
        return RuleResult(FAIL, None, "edge_step missing")
    lo, hi = params.get("min", 0.10), params.get("max", 1.5)
    if lo <= v <= hi:
        return RuleResult(PASS, float(v), f"edge_step={v:.4f} in [{lo},{hi}]")
    return RuleResult(FAIL, float(v), f"edge_step={v:.4f} out of [{lo},{hi}]")


@rule("CAL-EREF", flag="gate", scope="grid")
def _cal_eref(ctx, cell, params) -> RuleResult:
    """參考通道能量校正閘，兩層檢查：
    L1 — mu_ref_e0 − e0_nominal_eV 必須落在 mono_offset_window_eV 內
         （防止 mu_ref 抓到 glitch 而非真正的邊）；
    L3 — 全圖 |mu_ref_e0 − median(mu_ref_e0)| 必須在 ref_e0_spread_tol_eV 內
         （Ni 箔 E0 全圖應為常數，超過即為列間漂移）。
    L1 失敗 → FAIL；L3 失敗 → WARN。所有門檻取自 config.edge.*。"""
    ref = cell.meta.get("mu_ref_e0")
    if ref is None:
        return RuleResult(None, None, "mu_ref_e0 missing")
    e0_nom = ctx.edge_cfg.get("e0_nominal_eV", 8333.0)
    lo, hi = ctx.edge_cfg.get("mono_offset_window_eV", [-5.0, 25.0])
    offset = float(ref) - float(e0_nom)
    if not (lo <= offset <= hi):
        return RuleResult(FAIL, offset,
                          f"mu_ref_e0-e0_nom={offset:+.2f} eV out of [{lo},{hi}]")
    med = ctx.mu_ref_e0_median
    if med is None:
        return RuleResult(PASS, offset, "L1 ok; L3 skipped (no median)")
    tol = ctx.edge_cfg.get("ref_e0_spread_tol_eV", 0.3)
    dev = float(ref) - med
    if abs(dev) > tol:
        return RuleResult(WARN, dev,
                          f"|mu_ref_e0-med|={abs(dev):.3f} > {tol} eV")
    return RuleResult(PASS, offset, "L1+L3 ok")


@rule("R-NOISE-HF", flag="smooth", scope="grid", requires=("GATE-EDGE",))
def _r_noise_hf(ctx, cell, params) -> RuleResult:
    """後緣高頻雜訊。對 flat 於 E ≥ E₀ + 150 eV（EXAFS 區）做二階差分後 RMS。
    單側上尾 MAD z-score — 遠高於全圖中位數的格子代表雜訊大。
    參數：warn_z（預設 3）、fail_z（預設 5）。"""
    v = cell.meta.get("q2_hf_noise")
    return _upper_z(v, ctx.stats.get("q2_hf_noise"), params, "q2_hf_noise missing")


@rule("R-PRE-FLAT", flag="smooth", scope="grid", requires=("GATE-EDGE",))
def _r_pre_flat(ctx, cell, params) -> RuleResult:
    """前緣擬合殘差 RMS，作用於原始 μ 於 [E₀+pre1, E₀+pre2] 區間。
    當前緣無法用直線好好描述時會變大 — 散射、諧波污染、漏光。
    單側上尾 MAD z-score。
    參數：warn_z（預設 3）、fail_z（預設 5）。"""
    v = cell.meta.get("q3_pre_flatness")
    return _upper_z(v, ctx.stats.get("q3_pre_flatness"), params,
                    "q3_pre_flatness missing")


@rule("R-EDGE-FWHM", flag="smooth", scope="grid", requires=("GATE-EDGE",))
def _r_edge_fwhm(ctx, cell, params) -> RuleResult:
    """對 E₀ 附近 dμ/dE 峰的 FWHM 做雙側 MAD z-score。
    太寬（過大）代表厚度效應、樣品不均、或 beam 抖動；
    異常太窄（過小）代表 white line 流失或 E₀ 判定錯誤。
    Grid-relative — 自動校準到當次量測期的 beamline 解析度
    （Gaur 2026 的絕對窗 0.5–2.0 eV 僅作為 sanity 參考，此處不使用）。
    參數：warn_z（預設 2.5，Leys 2013）、fail_z（預設 4，明確離群）。"""
    v = cell.meta.get("edge_fwhm_eV")
    return _two_sided_z(v, ctx.stats.get("edge_fwhm_eV"), params,
                        "edge_fwhm_eV missing (reprocess needed)")


@rule("R-NORM-COEFS", flag="smooth", scope="grid", requires=("GATE-EDGE",))
def _r_norm_coefs(ctx, cell, params) -> RuleResult:
    """對應 §5.2 A Q3：正規化合理性。整合 pre_slope 與後緣多項式係數
    norm_c1、norm_c2，取三者對全圖中位數的 max|z|（MAD-scaled）判定。
    偵測散射、諧波、飽和、或前/後緣窗設定錯誤 — 正常 121 格網不應共享的問題。
    reason 會標明是哪一個係數超標。
    參數：warn_z（預設 2.5）、fail_z（預設 4）。"""
    values = {
        "pre_slope": cell.meta.get("pre_slope"),
        "norm_c1": cell.meta.get("norm_c1"),
        "norm_c2": cell.meta.get("norm_c2"),
    }
    if any(v is None for v in values.values()):
        return RuleResult(None, None,
                          "norm coefficients missing (reprocess needed)")
    warn_z = params.get("warn_z", 3)
    fail_z = params.get("fail_z", 5)
    worst_z = None
    worst_name = None
    for name, v in values.items():
        stats = ctx.stats.get(name)
        if not stats:
            continue
        z = _robust_z(float(v), stats["median"], stats["mad_scaled"])
        if z is None:
            continue
        if worst_z is None or abs(z) > abs(worst_z):
            worst_z = z
            worst_name = name
    if worst_z is None:
        return RuleResult(None, None, "no baseline stats for any coefficient")
    az = abs(worst_z)
    if az >= fail_z:
        return RuleResult(FAIL, worst_z, f"{worst_name}: |z|={az:.2f} > {fail_z}")
    if az >= warn_z:
        return RuleResult(WARN, worst_z, f"{worst_name}: |z|={az:.2f} > {warn_z}")
    return RuleResult(PASS, worst_z, f"{worst_name}: z={worst_z:+.2f}")


@rule("R-GLITCH", flag="smooth", scope="grid", requires=("GATE-EDGE",))
def _r_glitch(ctx, cell, params) -> RuleResult:
    """flat 於 E ≥ E₀ + 150 eV 區間內 MAD 離群點的計數 —
    偵測單色器 glitch、Bragg 峰、top-up 注射瞬變。兩段判定：
      1. 絕對計數 > max_count → 直接 FAIL；
      2. 否則對全圖做單側上尾 MAD z-score。
    參數：max_count（預設 5）、warn_z（預設 3）、fail_z（預設 5）。"""
    v = cell.meta.get("q5_glitches")
    if v is None:
        return RuleResult(None, None, "q5_glitches missing")
    max_count = params.get("max_count", 5)
    if v > max_count:
        return RuleResult(FAIL, float(v), f"glitches={v} > {max_count}")
    res = _upper_z(float(v), ctx.stats.get("q5_glitches"), params, "n/a")
    if res.level is None:
        return RuleResult(PASS, float(v), f"count={v}, no z stats")
    return res


@rule("R-SNR", flag="smooth", scope="grid", requires=("GATE-EDGE",))
def _r_snr(ctx, cell, params) -> RuleResult:
    """邊緣訊雜比：edge_step / q3_pre_flatness（兩者皆為原始 μ 單位 → 無因次）。
    低 SNR 為壞事，故採單側「下尾」MAD z-score —
    z ≤ −warn_z → WARN，z ≤ −fail_z → FAIL。
    與 R-PRE-FLAT 相關（共用 q3）；若使用 combine_mode=weighted 時應調整權重。
    參數：warn_z（預設 3）、fail_z（預設 5）。"""
    step = cell.meta.get("edge_step")
    q3 = cell.meta.get("q3_pre_flatness")
    if step is None or q3 is None or q3 <= 0:
        return RuleResult(None, None, "edge_step / q3 missing or non-positive")
    snr = float(step) / float(q3)
    stats = ctx.stats.get("snr")
    if not stats:
        return RuleResult(None, snr, "no snr baseline stats")
    z = _robust_z(snr, stats["median"], stats["mad_scaled"])
    if z is None:
        return RuleResult(None, snr, "MAD=0")
    warn_z = params.get("warn_z", 3)
    fail_z = params.get("fail_z", 5)
    # low SNR is bad
    if z <= -fail_z:
        return RuleResult(FAIL, z, f"z={z:.2f} < -{fail_z}")
    if z <= -warn_z:
        return RuleResult(WARN, z, f"z={z:.2f} < -{warn_z}")
    return RuleResult(PASS, z, f"z={z:+.2f}")


@rule("C-SHAPE", flag="consistent", scope="grid",
      requires=("GATE-EDGE", "CAL-EREF"))
def _c_shape(ctx, cell, params) -> RuleResult:
    """本格經校正的 norm 對「所有通過 gate + cal-eref 格子的逐點中位數」做 R-factor，
    兩者皆內插到共同能量網格
    ([E0_med + shape_grid_eV[0], E0_med + shape_grid_eV[1]]、
    步長 shape_grid_eV[2]，取自 config.examine）。單側上尾 MAD z-score。
    能量範圍未涵蓋共同網格的格子回傳 N/A。
    參數：warn_z（預設 3）、fail_z（預設 5）。"""
    r = ctx.shape_r.get(cell.key)
    if r is None:
        return RuleResult(None, None, "no shape residual (excluded from median)")
    return _upper_z(r, ctx.stats.get("shape_r"), params, "n/a")


@rule("C-E0-NBR", flag="consistent", scope="grid",
      requires=("GATE-EDGE", "CAL-EREF"))
def _c_e0_nbr(ctx, cell, params) -> RuleResult:
    """校正後 E₀ 與 8 鄰格校正後 E₀ 中位數之差。雙側 MAD z-score
    （過高與過低都算異常）。有效鄰格少於 2 個 → N/A。
    此規則若命中可能是真實化學差異（該點氧化態不同），
    所以只影響 `consistent` 旗標，不影響 `usable`。
    參數：warn_z（預設 3）、fail_z（預設 5）。"""
    d = ctx.e0_nbr_diff.get(cell.key)
    if d is None:
        return RuleResult(None, None, "<2 valid neighbors")
    return _two_sided_z(d, ctx.stats.get("e0_nbr_diff"), params, "n/a")


@rule("C-CUMDIFF", flag="consistent", scope="grid",
      requires=("GATE-EDGE", "CAL-EREF"))
def _c_cumdiff(ctx, cell, params) -> RuleResult:
    """Lippold 2005 判準 7，參考採 8 鄰格「校正後 norm」於共同網格上的平均值。
    需要 shape context（各格內插到共同網格的 norm）— 無法內插到共同網格、
    或於共同網格上有效鄰格少於 2 個的格子，回傳 N/A。
    參數：warn_z（預設 3）、fail_z（預設 5）；預設 enabled: false。"""
    v = ctx.cumdiff_c7.get(cell.key)
    if v is None:
        return RuleResult(None, None,
                          "<2 neighbours on common grid or interp missing")
    return _upper_z(v, ctx.stats.get("cumdiff_c7"), params, "n/a")


# ---------- Combine ----------

def combine(flag: str, results: dict[str, RuleResult],
            enabled: dict[str, bool], mode: str = "worst") -> tuple[int | None, int, int]:
    """Return (level, n_evaluated, n_enabled) for a given flag."""
    if mode == "weighted":
        raise NotImplementedError("combine_mode 'weighted' not implemented; use 'worst'")
    if mode != "worst":
        raise ValueError(f"unknown combine_mode: {mode}")
    n_enabled = 0
    n_eval = 0
    worst = None
    for rid, r in REGISTRY.items():
        if r.flag != flag:
            continue
        if not enabled.get(rid, False):
            continue
        n_enabled += 1
        res = results.get(rid)
        if res is None or res.level is None:
            continue
        n_eval += 1
        if worst is None or res.level > worst:
            worst = res.level
    return worst, n_eval, n_enabled


def is_usable(smooth_level: int | None, gate_edge: RuleResult | None) -> bool:
    """usable = GATE-EDGE PASS AND smooth in {PASS, WARN}."""
    if gate_edge is None or gate_edge.level != PASS:
        return False
    if smooth_level is None:
        return False
    return smooth_level in (PASS, WARN)

<!-- README.md | version 2.0.2 by Albert Sheng | R-EDGE-FWHM + R-NORM-COEFS 加入 -->

# NiXZ-121 XANES Analyzer

Quality assessment for **NiXZ-121** — an 11 × 11 grid of QEXAFS scans of a
Ni sample (121 sections total). Pipeline: raw `.txt` →
[`larch.xafs.pre_edge()`](https://xraypy.github.io/xraylarch/xafs_preedge.html)
→ 6 quality metrics → 11 rule-based verdicts → Tk GUI + heatmaps.

---

## Features

- **Phase 1 pipeline** (`pipeline.py`) — parses JAQ QEXAFS text, runs
  `pre_edge()`, computes Q1–Q6 (edge step, HF noise, pre-edge flatness,
  E₀ shift vs `mu_ref`, glitch count, white-line height), caches arrays +
  metrics + PNG plots.
- **Phase 2 examine** (`rules.py`, `examine.py`) — 11 configurable rules
  produce two flags per cell:
  - `smooth` — measurement quality (`R-SNR`, `R-NOISE-HF`, `R-PRE-FLAT`,
    `R-GLITCH`, `R-EDGE-FWHM`, `R-NORM-COEFS`)
  - `consistent` — grid-wide agreement (`C-SHAPE`, `C-E0-NBR`, `C-CUMDIFF`)
  - plus gates `GATE-EDGE`, `CAL-EREF`
  - `usable = GATE-EDGE PASS AND smooth in {PASS, WARN}`
  - `C-CUMDIFF` implements Lippold 2005 criterion 7 (std of residual of
    cumulative-difference after linear-fit) against the 8-neighbour mean;
    opt-in via config.
- **Tk GUI** — three-panel browser (Z folders → X sections → info),
  light-blue batch progress bar, singleton plot windows (Pre-edge /
  Normalized / Combined; reused per kind, never stacked), 11 × 11 heatmap
  with combobox coloring by raw metrics or examine flags, small-multiples
  Rule Violations window (one 11 × 11 per rule), click-to-select on all
  heatmaps, Rules toggle panel with editable thresholds + optional
  Save-to-yaml, Exit.
- **File cache** — `data/**/*.npz` (arrays), `data/**/*.json` (metrics),
  `data/**/*.examine.json` (rule verdict), `data/examine_run.json` (run
  manifest with `config_hash`), `image/**/*.png` (plots). 1-to-1 map onto
  the MySQL schema in `doc/NiXZ-121_project.md` §6 — MySQL wiring deferred
  until the schema is finalized.
- **Tests** — 79 pytest tests covering regex/naming, discovery, data
  format, pipeline round-trip, metric shapes, cache I/O, GUI smoke,
  examine engine (rules, N/A propagation, config-hash determinism,
  flag combine, lippold_c7 identities, C-CUMDIFF jump detection,
  R-EDGE-FWHM broaden/narrow detection, R-NORM-COEFS legacy-cache handling).

## Install

Python 3.11+ (Windows / macOS / Linux).

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

xraylarch pulls a heavy dependency tree (scipy, lmfit, pymatgen, silx,
h5py, sqlalchemy, plotly, mkl); first install takes several minutes.

## Run

**GUI** — the default:

```
python main.py
```

On launch, pick the dataset root (folder containing
`Z{i}_{z}/X{j}_{x}_{start}_{end}_XANES.txt`). Then:

| gesture | action |
|---|---|
| click a Z folder | list its X sections in the middle panel |
| single-click an X section | process (or load cache), show metrics only |
| double-click an X section | also open Pre-edge + Normalized plot windows |
| **Both plots (combined)** button | open the side-by-side combined figure |
| **Process all (batch)** | run pipeline on all 121, progress bar fills |
| **Examine 121** | rule-based verdict over all cached cells |
| **Rules...** | toggle rules, edit z-score thresholds, Apply & Examine |
| **11 × 11 heatmap** | color by raw metric or examine flag (PASS/WARN/FAIL/N/A) |
| **Rule violations** | small-multiples: one 11 × 11 per rule |
| click any heatmap cell | jump-select the section in the listboxes |

**Headless (batch + examine, no GUI)**:

```
python main.py --batch image_AI_Ni                                   # pipeline only
python main.py --examine image_AI_Ni                                 # rule verdict on cached cells
python main.py --batch image_AI_Ni --examine image_AI_Ni             # both in one run
python main.py --examine image_AI_Ni --config alt.yaml               # custom config
```

## Tests

```
python -m pytest test/
```

See `test/README.md` for what each file covers.

## Storage layout

```
data/
  examine_run.json                  run manifest: uuid, config, config_hash, per-field stats
  Z0_-5/
    X0_5_1_120.npz                  energy, mu, mu_ref, pre_edge, post_edge, norm, flat, e0, edge_step (float32)
    X0_5_1_120.json                 pipeline metadata + Q1-Q6 + preliminary usable
    X0_5_1_120.examine.json         rule verdict: smooth, consistent, usable, per-rule {level,value,reason}
    ...
image/
  Z0_-5/
    X0_5_1_120_preedge.png
    X0_5_1_120_norm.png
    ...
```

Filename stem `X{j}_{x}_{start}_{end}` mirrors the source; folder disambiguates Z.

## Project docs

- **`doc/NiXZ-121_project.md`** — authoritative technical reference (data
  format, naming rules, 11 × 11 matrix, pipeline steps, metric
  definitions, §5.1 literature review with citations to xraylarch, MBACK,
  TXM-Wizard, Lippold 2005, Gaur 2026, Leys 2013, Stern & Kim 1981;
  §5.1.1 rule-provenance table; §6 MySQL schema; §10 discrepancy log
  D1–D8).
- **`doc/TASK_examine_rules.md`** — Phase 2 spec + §12 implementation log
  (assumed vs actual key names, unit choices, Lippold paper reading,
  MySQL deferral, C-CUMDIFF status).
- **`test/README.md`** — per-file test-suite guide.

---

## For contributors and AI agents

### Repository layout

```
main.py                tkinter GUI + --batch / --examine CLI
pipeline.py            Phase 1: parse, pre_edge, metrics, cache I/O, figure builders
rules.py               Phase 2: Rule dataclass + REGISTRY + 11 rules + lippold_c7 helper
examine.py             Phase 2: context builder + topological execution + verdict writer
config.yaml            rules + thresholds + edge config + (disabled) db config
requirements.txt       numpy, matplotlib, xraylarch, pyyaml, pytest
test/                  73-test pytest suite
```

### Sharp edges (bugs I hit or foresee)

1. **Windows glob is case-insensitive** — `Z6_1/x5_0_666_786_XANES.txt`
   (lowercase `x`) was included by `glob("X*_XANES.txt")` and crashed the
   sort. `pipeline.discover_x_files` now strictly filters by `FNAME_RE`
   so malformed names drop silently. Rename lowercase files to uppercase
   to recover the 121st section.
2. **`g.pre1` doesn't exist** — larch stores those parameters under
   `g.pre_edge_details.pre1` (and `.pre2, .norm1, .norm2, .nnorm, .nvict`).
3. **E₀ garbage on empty regions** — corner sections with no Ni signal
   have `edge_step ≈ 0.05` and `find_e0` picks something like 8629 eV
   instead of ~8333. Baseline stats in examine.py exclude non-`GATE-EDGE`
   cells for this reason; sanity-check `edge_step > 0.05` before trusting `e0`.
4. **Progress bar color needs `clam` theme** — Windows vista theme silently
   ignores `background` on `ttk.Progressbar`; `main.py` switches to `clam`
   globally so the `Blue.Horizontal.TProgressbar` style takes effect.
5. **Plot windows are singletons keyed by kind** — `self.plot_windows` is
   `dict[str, Toplevel]`; do not `.pack()` into an existing Toplevel
   without destroying its children first. `_open_plot` handles this.
6. **`matplotlib.figure.Figure` is used directly** (no `pyplot`) so figures
   work identically for `savefig()` and for `FigureCanvasTkAgg`. Don't
   switch to pyplot.
7. **MAD = 0 → N/A** — if the whole 121-grid is unrealistically uniform,
   robust MAD-scaled z can be 0 and every rule returns N/A. Real data has
   jitter; tests seed jitter explicitly to avoid this false-negative.
8. **N/A does NOT count as PASS** — if a required rule is disabled or
   non-PASS, downstream rules return N/A with reason
   `"requires X (disabled)"` or `"requires X (FAIL)"`. Baseline stats
   (median/MAD) use only cells that passed `GATE-EDGE`.

### Adding a new rule

1. Add a function decorated with
   `@rl.rule(id, flag, scope, requires=(...))` in `rules.py`, returning
   `RuleResult(level, value, reason)`.
2. Add its default settings under `rules:` in `config.yaml`.

Nothing in `examine.py` needs to change — topological sort picks it up.

### Deferred work

Recorded in `doc/NiXZ-121_project.md` §8:
1. Full 121-file dataset (currently 3 Z folders present: Z0_-5, Z6_1, Z10_5)
2. MAD-based threshold auto-tuning across the full grid
3. `mu_ref` calibration reference confirmation (Ni foil?)
4. Q7 (image indicator) — needs the `.bin` per-scan data
5. MySQL wiring — schema in `doc/NiXZ-121_project.md` §6; `.npz` + `.json` +
   `.examine.json` map 1-to-1 onto `spectra`, `qc`, `qc_rule_result`,
   `qc_verdict`
6. Reserved rules `T-DRIFT`, `T-UPDOWN`, `T-OUTLIER-SCAN`, `T-SATURATION`
   — will reuse `rules.lippold_c7()` once `.bin` scan-level data is
   available

---

version 2.0 by Albert Sheng

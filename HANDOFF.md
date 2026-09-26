<!-- version 1.0 by Albert Sheng -->

# Handoff — NiXZ-121 XANES Analyzer

Read this if you are an AI agent (or a human dropped in cold) tasked with
extending or debugging this project. Keep the load light: this document
plus `NiXZ-121.md` should be enough to orient without reading every file.

---

## 1. What this project is (30-second version)

The user has a 3-D X-ray absorption microscopy dataset of a Ni sample:
an 11 × 11 spatial grid of 121 QEXAFS scans. Each scan is a
~4000-point μ(E) spectrum across 8058–9241 eV covering the Ni K-edge
(~8333 eV).

The goal is to **automatically judge which of the 121 sections are
"smooth and usable"** and browse them interactively — reject noisy /
signal-less spots, keep the good ones for downstream chemical-state
analysis (the white-line and pre-edge peaks tell you Ni oxidation state).

The reference algorithm is `larch.xafs.pre_edge()` (larch 2026.3.1), which
gives you E₀, edge step Δμ₀, and normalized/flattened spectra. From those
we compute 6 quality metrics (Q1–Q6) and a boolean `usable` flag.

## 2. Repository layout

```
main.py           tkinter GUI + --batch CLI entry
pipeline.py       pure-logic: parse, pre_edge, metrics, cache I/O, figure builders
test/             pytest suite (58 tests, ~4 s)
NiXZ-121.md       consolidated project doc: data format, naming, matrix,
                  Q1-Q7 definitions, DB schema
README.md         user-facing quickstart
HANDOFF.md        this file
requirements.txt  pinned-loose dep list
.gitignore        excludes data/, image/, image_AI_Ni/, .venv/
```

At runtime (excluded from git):
```
image_AI_Ni/      raw dataset (Z{i}_{z}/X{j}_{x}_{start}_{end}_XANES.txt + .bin sidecars)
data/             cache: {stem}.npz (arrays) + {stem}.json (metrics)
image/            cache: {stem}_preedge.png + {stem}_norm.png
.venv/            Python virtual env
```

## 3. Naming — the single most important invariant

Every filename encodes physical position on the sample:

- Folder `Z{i}_{z}`: **i ∈ [0, 10]**, z = i − 5  → same direction
- File `X{j}_{x}_{start}_{end}_XANES.txt`: **j ∈ [0, 10]**, x = **5 − j**  → **inverted**

So:
- Center `(x, z) = (0, 0)` = `Z5_0/X5_0_668_788_XANES.txt`
- Top-left `(x=-5, z=+5)` = `Z10_5/X10_-5_...` (both i and j max out at 10)
- Bottom-right `(x=+5, z=-5)` = `Z0_-5/X0_5_...`

Regexes: `pipeline.FNAME_RE` and `pipeline.ZDIR_RE`.

**Windows glob is case-insensitive.** We hit this with `Z6_1/x5_0_666_786_XANES.txt`
(lowercase `x`) — `discover_x_files` now strictly filters by `FNAME_RE`
so malformed names get dropped silently. If you see 10 of 11 sections in
a Z folder, check for a case-mismatched filename.

## 4. Data format

Header block (`# ...`), then 4 columns:
```
No.  Energy [eV]  mu  mu_ref
```
- `mu` = ln(col_0/col_1) — sample absorption (transmission mode)
- `mu_ref` = ln(col_1/col_2) — reference channel, used for energy calibration
- 4000 points, 8058.1–9241.3 eV, step ≈ 0.30 eV
- File header says the file is an **average** over spectrum indices `{start}..{end}`
  (typically ~120 scans per average).

`pipeline.load_xanes()` returns `(energy, mu, mu_ref)` as three arrays.

## 5. Pipeline (pipeline.py, ~275 lines)

```
load_xanes(path)
    -> (energy, mu, mu_ref)

run_pre_edge(energy, mu)
    -> larch.Group  with e0, edge_step, pre_edge, post_edge, norm, flat,
                        pre_edge_details.{pre1,pre2,norm1,norm2,nnorm,nvict,...}

compute_metrics(g, mu_ref_e0=None)
    -> dict with e0, edge_step, q1..q6, q4_e0_shift_vs_ref (None if no ref)

decide_usable(metrics) -> bool     preliminary heuristic; replace with
                                   MAD-based thresholds once 121 are collected

process_section(sec, force=False) -> dict
    -- writes  data/{Zdir}/{stem}.npz  + {stem}.json
    --        image/{Zdir}/{stem}_preedge.png  + {stem}_norm.png
    -- uses cache unless force=True

cache_bundle(sec) -> dict | None      loads npz
load_meta(sec)    -> dict | None      loads json
```

Plot builders return a `matplotlib.figure.Figure` (no pyplot) so they work
inside Tk and for standalone `.savefig()`:

- `plot_preedge_fig(bundle, title)` — μ + pre-edge line + post-edge curve
- `plot_norm_fig(bundle, title)`    — normalized + flattened
- `plot_combined_fig(bundle, title)` — both side-by-side (image.png style)

### Larch gotcha
`g.pre1` **does not exist**. Those params live at `g.pre_edge_details.pre1`
(and `.pre2, .norm1, .norm2, .nnorm, .nvict, ...`). Cost me a full test
failure on first run — see test/test_pipeline.py::test_run_pre_edge_group_has_expected_fields.

### E₀ noise on empty regions
Corner sections with no Ni signal (e.g. `Z0_-5/X0_5_1_120` in the current
partial dataset) have `edge_step ≈ 0.05` and `find_e0` picks garbage
(~8629 eV instead of 8333). Guard tests use `Z6_1/X0_5_1_120` (guideline
reference, e0 ≈ 8346.2 eV) as the known-good sample.

## 6. Quality metrics (compute_metrics, ~40 lines)

| # | key | what | window |
|---|---|---|---|
| Q1 | `q1_edge_step` | edge_step (= g.edge_step) | — |
| Q2 | `q2_hf_noise` | RMS of 2nd difference of `flat` | E ≥ E₀ + 150 eV |
| Q3 | `q3_pre_flatness` | RMS of `mu − pre_edge_line` | `[E₀+pre1, E₀+pre2]` |
| Q4 | `q4_e0_shift_vs_ref` | e0_sample − e0_mu_ref | — |
| Q5 | `q5_glitches` | count of `abs(diff) > 5·MAD·1.4826` | E ≥ E₀ + 150 eV |
| Q6 | `q6_white_line` | max(norm) | `[E₀-5, E₀+30]` |
| Q7 | — | image ROI (Laplacian variance) | **not implemented** — no image data yet |

Thresholds in `decide_usable` are placeholders. Guideline §5 says the
correct approach is median ± k·MAD across all 121 sections; do that once
the full dataset arrives.

## 7. GUI (main.py, ~280 lines)

Three-panel layout:
- Left: Z folders (Listbox)
- Middle: X sections in selected Z (Listbox)
- Right: metrics text + 4 buttons (Pre-edge / Normalized / Both combined / Reprocess)

Bottom:
- Light-blue `ttk.Progressbar` (`Blue.Horizontal.TProgressbar` style, needs
  clam theme — vista theme ignores color changes)
- Status text on the left + Exit button on the lower right
- `WM_DELETE_WINDOW` routes to `_on_exit` which closes all plot windows

Selection semantics:
- Single-click X → process (cached) + show metrics only
- Double-click X → also opens Pre-edge + Normalized plots
- All plot windows are **singletons keyed by kind** in `self.plot_windows: dict[str, Toplevel]`.
  Reused (children destroyed, redrawn) rather than stacked. Max concurrent
  plot windows: 3 (preedge/norm/combined) + 1 heatmap.
- Manually closing a plot window is fine — `winfo_exists()` check handles it.

`run_batch(root, status_cb, progress_cb, tk_root)` drives the progress bar;
same function is called by `--batch` CLI with only `status_cb` (prints to stdout).

## 8. Storage strategy

Decision made in an earlier turn: **cache calculated arrays, not just algorithm**.

- Same disk cost as PNGs (~12 MB per 121 sections)
- Arrays are queryable, re-plottable, interactive; PNGs are dead views
- GUI needs to redraw on demand (zoom/pan/threshold sliders) — arrays win
- MySQL migration path is clear: `.npz` maps to `spectra(section_id, energy BLOB, norm BLOB, flat BLOB)`,
  `.json` maps to `qc(section_id, e0, edge_step, q1..q6, usable)`.
  See `NiXZ-121.md` §6.1 for the column spec.

PNGs are generated as a convenience for external reports; they're NOT the
source of truth. GUI plots directly from `.npz`.

## 9. Testing (test/, 58 tests, ~4 s)

Structured by concern, not by file-under-test. `conftest.py` provides:
- `data_root` → `image_AI_Ni/` (skips whole test if missing)
- `sample_txt` → `Z6_1/X0_5_1_120_XANES.txt` (known-good; falls back if absent)
- `tmp_cache` → monkeypatches `pl.DATA_ROOT` + `pl.IMAGE_ROOT` into `tmp_path`

Tests degrade gracefully — larch-dependent tests use `pytest.importorskip("larch")`,
so a fresh checkout without larch still passes the naming / regex / GUI
smoke tests.

Files:
- `test_naming.py` — FNAME_RE, ZDIR_RE, parse_section, all-121-cell invariants
- `test_discovery.py` — Z/X ordering, malformed-name filtering, bounds ≤ 11
- `test_data_format.py` — raw txt shape, energy monotonic, Ni K-edge range
- `test_pipeline.py` — larch Group fields, E₀ range, cache hit / force overwrite, PNG size
- `test_metrics.py` — key presence, Q1==edge_step, Q4 gating, decide_usable thresholds
- `test_cache.py` — .npz + .json round-trip, missing-cache handling
- `test_gui_smoke.py` — module imports, XANESViewer instantiates headless with cancelled filedialog

## 10. What's not done (from NiXZ-121.md §8)

1. **Full dataset** — currently 3 of 11 Z folders present (Z0_-5, Z6_1, Z10_5).
2. **MAD-based thresholds** — `decide_usable` uses guesses; recompute with
   median ± k·MAD over all 121 sections once collected.
3. **`mu_ref` calibration reference** — assumed Ni foil; needs confirmation
   with the beamline operator.
4. **Q7 (image indicator)** — needs image-side data (`image_AI_Ni/Z*/Z*.bin`
   at ~12.5 GB each; format unclear).
5. **MySQL migration** — currently file-cache; schema drafted in `NiXZ-121.md` §6.1.

## 11. Sharp edges to remember

- Windows glob is **case-insensitive**; always filter with `FNAME_RE`.
- E₀ auto-detection on empty regions returns garbage — sanity check
  `edge_step > 0.05` before trusting `e0`.
- ttk `clam` theme is applied globally so the progress bar takes color;
  removing it means Windows vista theme silently ignores the color spec.
- Plot windows are **singletons keyed by kind**; do not `.pack()` new canvas
  into an existing Toplevel without first destroying children.
- `find_e0` and `pre_edge` are called separately for `mu` and `mu_ref` to get
  `q4_e0_shift_vs_ref` — small extra cost, correct semantics.
- `matplotlib.figure.Figure` is used directly (no `pyplot`) so figures work
  identically for `savefig()` and for `FigureCanvasTkAgg`. Don't switch to pyplot.

---

version 1.0 by Albert Sheng

<!-- version 1.1 by Albert Sheng -->

# NiXZ-121 XANES Analyzer

Quality-assessment tool for the **NiXZ-121** X-ray absorption dataset — an
11 × 11 grid (121 sections) of XANES scans of a Ni sample collected in
QEXAFS mode.

Pipeline: raw `.txt` → [`larch.xafs.pre_edge()`](https://xraypy.github.io/xraylarch/xafs_preedge.html)
→ 6 quality metrics → cached arrays + PNG plots → Tk GUI browser + 11 × 11 heatmap.

---

## Features

- **Batch pipeline** — parses JAQ QEXAFS text files, runs `pre_edge()`,
  computes Q1–Q6 (edge step, high-freq noise, pre-edge flatness, E₀ shift vs
  `mu_ref`, glitch count, white-line height), and caches everything.
- **Examine (rule-based)** — 9 configurable rules produce two flags per cell:
  `smooth` (measurement quality) and `consistent` (agreement with the rest
  of the grid). Rules are individually toggleable via a GUI panel or
  `config.yaml`; per-cell verdict + `usable` tag written to
  `data/**/*.examine.json`. `usable = GATE-EDGE PASS AND smooth in {PASS, WARN}`.
  Includes `C-CUMDIFF` (opt-in) implementing Lippold 2005 criterion 7 —
  standard-deviation-of-cumulative-difference against the 8-neighbour mean;
  see `references/` and `TASK_examine_rules.md` §12 for the paper reading.
- **Tkinter GUI** — three-panel browser (Z folders → X sections → info),
  light-blue progress bar during batch runs, **singleton** plot windows
  (Pre-edge / Normalized / Combined; each refreshes in place instead of
  stacking), Examine + Rules toggle panel, 11 × 11 heatmap with combobox
  coloring (raw metrics or examine flags), click-to-select a cell, and an
  Exit button.
- **Cache** — per-section `.npz` (arrays) + `.json` (scalar metrics) +
  `.examine.json` (rule verdicts) under `data/`; PNG plots under `image/`.
  Layout is 1-to-1 with the MySQL schema planned in `NiXZ-121.md` §6
  (MySQL wiring deferred until schema is finalized).
- **Tests** — 73 pytest tests covering regex/naming, discovery, data format,
  pipeline round-trip, metric shapes, cache I/O, GUI smoke, and the examine
  engine (rules, N/A propagation, config hash, flag combine, lippold_c7
  identities, C-CUMDIFF jump detection).

## Install

Python 3.11+ on Windows/macOS/Linux.

```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

xraylarch pulls in a large dependency tree (scipy, lmfit, pymatgen, silx,
h5py, sqlalchemy, plotly, mkl, ...). First install takes several minutes.

## Run

GUI (default):

```
python main.py
```

On launch you'll be prompted for the dataset root — a folder containing
`Z{i}_{z}/X{j}_{x}_{start}_{end}_XANES.txt` files. Then:

- Click a **Z folder** → middle panel lists that folder's X sections
- **Single-click** an X section → runs pipeline (or loads cache), shows E₀
  and Q1–Q6 in the info panel
- **Double-click** an X section → opens Pre-edge + Normalized plot windows
- **Both plots (combined)** button → one window with both panels side-by-side
- **Process all (batch)** → runs the whole tree, progress bar advances
- **11 × 11 heatmap** → colored by Q1 (edge step); white cells = unprocessed

Batch (headless, no GUI):

```
python main.py --batch image_AI_Ni                    # pipeline only
python main.py --examine image_AI_Ni                  # rule-based examine (needs cache)
python main.py --batch image_AI_Ni --examine image_AI_Ni  # both
```

## Rule-based examine

`config.yaml` at the repo root defines the 8 rules and their thresholds.
In the GUI, `Rules...` opens a toggle panel — check/uncheck each rule,
edit its z-score thresholds, and hit **Apply & Examine**. The heatmap can
color by any raw metric or by the resulting flag (green / yellow / red /
grey) — pick from the combobox above the heatmap.

Rule dependencies (`requires`) are enforced: disabling `CAL-EREF` propagates
N/A to `C-SHAPE` and `C-E0-NBR` (with reason `"requires CAL-EREF (disabled)"`).
Disabling all `smooth` rules yields `smooth: N/A` and `usable: NO`.

## Storage layout

## Tests

```
python -m pytest test/
```

See [`test/README.md`](test/README.md) for a per-file breakdown.

## Storage layout

```
data/
  examine_run.json               run manifest (uuid, config, config_hash, stats)
  Z0_-5/
    X0_5_1_120.npz               energy, mu, mu_ref, pre_edge, post_edge, norm, flat, e0, edge_step
    X0_5_1_120.json              pipeline metadata + Q1-Q6
    X0_5_1_120.examine.json      per-cell verdict: smooth, consistent, usable, per-rule level/value/reason
    ...
image/
  Z0_-5/
    X0_5_1_120_preedge.png
    X0_5_1_120_norm.png
    ...
```

Filename stem: `X{j}_{x}_{start}_{end}` (mirrors source). Folder disambiguates Z.

## Project docs

- [`NiXZ-121_project.md`](NiXZ-121_project.md) — **authoritative** project
  reference (v1.3+): includes §5.1 literature review with Lippold 2005 /
  Gaur 2026 / TXM-Wizard citations, §5.1.1 rule-provenance table, §10
  discrepancy log (D1–D8), and the MySQL schema decision.
- [`NiXZ-121.md`](NiXZ-121.md) — earlier consolidated summary; kept for
  history. New details go into `NiXZ-121_project.md`.
- [`HANDOFF.md`](HANDOFF.md) — architectural handoff for AI agents or new
  contributors; explains code structure, invariants, and next steps.
- [`TASK_examine_rules.md`](TASK_examine_rules.md) — Phase 2 examine spec;
  §12 records implementation deviations from the original assumption doc.
- [`test/README.md`](test/README.md) — test suite guide.

## Roadmap

Items still open (from `NiXZ-121.md` §8):

1. Full 121-file dataset (currently 3 of 11 Z folders present)
2. MAD-based threshold auto-tuning across all 121 sections
3. `mu_ref` calibration reference confirmation (Ni foil?)
4. Image-side ROI & Q7 (Laplacian variance, greyscale uniformity)
5. MySQL schema implementation (schema in `NiXZ-121.md` §6.1)

---

version 1.1 by Albert Sheng

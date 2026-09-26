<!-- version 1.0 by Albert Sheng -->

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
- **Tkinter GUI** — three-panel browser (Z folders → X sections → info),
  light-blue progress bar during batch runs, **singleton** plot windows
  (Pre-edge / Normalized / Combined; each refreshes in place instead of
  stacking), an 11 × 11 edge-step heatmap, and an Exit button.
- **Cache** — per-section `.npz` (arrays) + `.json` (scalar metrics) under
  `data/`; PNG plots under `image/`. Layout is 1-to-1 with the MySQL schema
  planned in `NiXZ-121.md` §6.
- **Tests** — 58 pytest tests covering regex/naming, discovery, data format,
  pipeline round-trip, metric shapes, cache I/O, and a GUI smoke test.

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
python main.py --batch image_AI_Ni
```

## Tests

```
python -m pytest test/
```

See [`test/README.md`](test/README.md) for a per-file breakdown.

## Storage layout

```
data/
  Z0_-5/
    X0_5_1_120.npz      energy, mu, mu_ref, pre_edge, post_edge, norm, flat, e0, edge_step (float32)
    X0_5_1_120.json     i,j,z,x, seg_start/end, pre1/pre2/norm1/norm2/nnorm/nvict, Q1-Q6, usable
    ...
image/
  Z0_-5/
    X0_5_1_120_preedge.png
    X0_5_1_120_norm.png
    ...
```

Filename stem: `X{j}_{x}_{start}_{end}` (mirrors source). Folder disambiguates Z.

## Project docs

- [`NiXZ-121.md`](NiXZ-121.md) — consolidated technical reference: data
  format, naming rules, 11 × 11 matrix, pipeline, quality metrics, DB schema.
- [`HANDOFF.md`](HANDOFF.md) — architectural handoff for AI agents or new
  contributors; explains code structure, invariants, and next steps.
- [`test/README.md`](test/README.md) — test suite guide.

## Roadmap

Items still open (from `NiXZ-121.md` §8):

1. Full 121-file dataset (currently 3 of 11 Z folders present)
2. MAD-based threshold auto-tuning across all 121 sections
3. `mu_ref` calibration reference confirmation (Ni foil?)
4. Image-side ROI & Q7 (Laplacian variance, greyscale uniformity)
5. MySQL schema implementation (schema in `NiXZ-121.md` §6.1)

---

version 1.0 by Albert Sheng

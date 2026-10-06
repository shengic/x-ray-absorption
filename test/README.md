<!-- test/README.md | version 1.2 by Albert Sheng | + test_gui2_smoke.py -->

# NiXZ-121 QC test suite

pytest-based checks for `pipeline.py`, `rules.py`, `examine.py`, `main.py`, and `main2.py`.
Current count: **89 tests, ~35 s** on a warm venv.

## Install

```
pip install -r ../requirements.txt
```

Adds numpy, matplotlib, xraylarch, pyyaml, pytest.

## Run

From the repo root (`I:\x-ray absorption app`):

```
python -m pytest test/ -v
```

Selected file:

```
python -m pytest test/test_examine.py -v
```

## What each file covers

| file | scope | needs larch | needs data |
|---|---|---|---|
| `test_naming.py` | `FNAME_RE`, `ZDIR_RE`, `parse_section` field mapping, all-121 grid invariants | no | no |
| `test_discovery.py` | `discover_z_dirs`, `discover_x_files` ordering + regex compliance, malformed-name filtering | no | yes |
| `test_data_format.py` | raw txt shape, energy monotonic + Ni K-edge range, finiteness | no | yes |
| `test_pipeline.py` | `run_pre_edge` fields, E0 in range, edge_step > 0, `process_section` cache round-trip, force overwrite, PNG size, `edge_fwhm_eV` helper + meta persistence (v1.2) | yes | yes |
| `test_metrics.py` | `compute_metrics` keys, Q1 == edge_step, Q4 gated on `mu_ref_e0`, `decide_usable` thresholds | yes | yes |
| `test_cache.py` | `.npz` bundle contents + shapes, energy round-trip, `.json` meta matches returned metrics, pre_edge params persisted | yes | yes |
| `test_gui_smoke.py` | `main` imports, `XANESViewer` instantiates headless with cancelled filedialog | no (larch) | no |
| `test_gui2_smoke.py` | `main2` imports + subclasses `XANESViewer`; `hover_report()` content for with/without examine, flagged-rule listing, legacy cache (missing v1.2 keys); `_scan_cells` grid orientation `grid[i, 10-j]` and per-cell index | no (larch) | no |
| `test_examine.py` | Rule dispatch + REGISTRY completeness, N/A propagation from disabled deps, config-hash determinism, flag combine (worst mode), `lippold_c7` identities, C-CUMDIFF jump detection, R-EDGE-FWHM broaden/narrow, R-NORM-COEFS pre_slope outlier + legacy-cache handling. Uses synthetic 11×11 grid — does **not** need larch or real data. | no (larch) | no |

Tests that need larch or the dataset are skipped automatically when the
requirement is missing — the naming, regex, examine, and GUI-smoke tests
always run and are the fastest way to sanity-check a refactor.

## Isolation

`tmp_cache` fixture monkeypatches `pipeline.DATA_ROOT` and `pipeline.IMAGE_ROOT`
into `tmp_path`, so test runs do not touch the real `data/` or `image/`.
`synthetic_grid` fixture in `test_examine.py` builds a full 11×11 grid of
pipeline-shaped `.json` + `.npz` files by hand (with jitter so MAD > 0)
so examine tests need no larch and no real dataset.

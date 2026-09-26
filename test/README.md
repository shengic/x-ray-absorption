<!-- version 1.0 by Albert Sheng -->

# NiXZ-121 QC test suite

pytest-based sanity checks for `pipeline.py` and `main.py`.

## Install

```
pip install pytest numpy matplotlib xraylarch
```

## Run

From the repo root (`I:\x-ray absorption app`):

```
python -m pytest test/ -v
```

Selected file:

```
python -m pytest test/test_metrics.py -v
```

## What each file covers

| file | scope | needs larch | needs data |
|---|---|---|---|
| `test_naming.py` | `FNAME_RE`, `ZDIR_RE`, `parse_section` field mapping, all-121 grid invariants | no | no |
| `test_discovery.py` | `discover_z_dirs`, `discover_x_files` ordering + regex compliance | no | yes |
| `test_data_format.py` | raw txt shape, energy monotonic + Ni K-edge range, finiteness | no | yes |
| `test_pipeline.py` | `run_pre_edge` fields, E0 in range, edge_step > 0, `process_section` cache round-trip, force overwrite, PNG size | yes | yes |
| `test_metrics.py` | `compute_metrics` keys, Q1 == edge_step, Q4 gated on `mu_ref_e0`, `decide_usable` thresholds | yes | yes |
| `test_cache.py` | `.npz` bundle contents + shapes, energy round-trip, `.json` meta matches returned metrics, pre_edge params persisted | yes | yes |
| `test_gui_smoke.py` | `main` imports, `XANESViewer` instantiates headless with cancelled filedialog | no (larch) | no |

Tests that need larch or the dataset are skipped automatically when the
requirement is missing — the naming/regex tests always run and are the
fastest way to sanity-check a refactor.

## Isolation

`tmp_cache` fixture monkeypatches `pipeline.DATA_ROOT` and `pipeline.IMAGE_ROOT`
into `tmp_path`, so test runs do not touch the real `data/` or `image/`.

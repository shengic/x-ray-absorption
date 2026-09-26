"""Folder / file discovery ordering and completeness.

version 1.0 by Albert Sheng
"""
from __future__ import annotations

import pipeline as pl


def test_discover_z_dirs_nonempty(data_root):
    zs = pl.discover_z_dirs(data_root)
    assert len(zs) >= 1


def test_discover_z_dirs_match_regex(data_root):
    for z in pl.discover_z_dirs(data_root):
        assert pl.ZDIR_RE.match(z.name), z.name


def test_discover_z_dirs_sorted_by_i(data_root):
    zs = pl.discover_z_dirs(data_root)
    idxs = [int(pl.ZDIR_RE.match(z.name)[1]) for z in zs]
    assert idxs == sorted(idxs)


def test_discover_x_files_nonempty_per_z(data_root):
    for z in pl.discover_z_dirs(data_root):
        xs = pl.discover_x_files(z)
        assert xs, f"no X files in {z}"


def test_discover_x_files_match_regex(data_root):
    for z in pl.discover_z_dirs(data_root):
        for x in pl.discover_x_files(z):
            assert pl.FNAME_RE.match(x.name), x.name


def test_discover_x_files_sorted_by_j(data_root):
    for z in pl.discover_z_dirs(data_root):
        xs = pl.discover_x_files(z)
        js = [int(pl.FNAME_RE.match(x.name)[1]) for x in xs]
        assert js == sorted(js), f"{z.name}: {js}"


def test_at_most_11_x_files_per_z(data_root):
    """121-cell grid: each Z should hold at most 11 X sections."""
    for z in pl.discover_z_dirs(data_root):
        xs = pl.discover_x_files(z)
        assert len(xs) <= 11, f"{z.name} has {len(xs)}"


def test_at_most_11_z_folders(data_root):
    assert len(pl.discover_z_dirs(data_root)) <= 11


def test_discover_x_files_drops_malformed_names(tmp_path):
    """Malformed filenames (wrong case, missing suffix, wrong prefix) must
    be excluded rather than causing downstream parse failures."""
    z = tmp_path / "Z5_0"
    z.mkdir()
    (z / "X0_5_1_120_XANES.txt").write_text("")   # valid
    (z / "x5_0_666_786_XANES.txt").write_text("")  # lowercase x -- reject
    (z / "X0_5_1_120.txt").write_text("")          # no _XANES -- reject
    (z / "Y0_5_1_120_XANES.txt").write_text("")    # wrong prefix -- reject
    xs = pl.discover_x_files(z)
    assert [p.name for p in xs] == ["X0_5_1_120_XANES.txt"]

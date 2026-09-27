"""Folder / file discovery ordering and completeness.

version 1.1 by Albert Sheng
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


def test_discover_x_files_accepts_lowercase_and_uppercase_x(tmp_path):
    """v1.3 (D9 fix): FNAME_RE is case-insensitive so 'x5_...' and 'X0_...'
    are both accepted. Files that don't match FNAME_RE at all are dropped."""
    z = tmp_path / "Z5_0"
    z.mkdir()
    (z / "X0_5_1_120_XANES.txt").write_text("")     # valid uppercase
    (z / "x5_0_666_786_XANES.txt").write_text("")   # valid lowercase (D9)
    (z / "X0_5_1_120.txt").write_text("")           # no _XANES -- reject
    (z / "Y0_5_1_120_XANES.txt").write_text("")     # wrong prefix -- reject
    names = [p.name for p in pl.discover_x_files(z)]
    assert names == ["X0_5_1_120_XANES.txt", "x5_0_666_786_XANES.txt"]


def test_validate_root_flags_incomplete_z(tmp_path):
    z1 = tmp_path / "Z0_-5"
    z1.mkdir()
    (z1 / "X0_5_1_120_XANES.txt").write_text("")
    (z1 / "X1_4_134_254_XANES.txt").write_text("")
    r = pl.validate_root(tmp_path)
    assert r.total_x == 2
    assert "Z0_-5" in r.incomplete_z
    assert r.per_z_count["Z0_-5"] == 2


def test_validate_root_reports_regex_skipped(tmp_path):
    z1 = tmp_path / "Z5_0"
    z1.mkdir()
    (z1 / "X0_5_1_120_XANES.txt").write_text("")
    (z1 / "Y9_9_1_120_XANES.txt").write_text("")
    r = pl.validate_root(tmp_path)
    assert "Y9_9_1_120_XANES.txt" in r.per_z_skipped["Z5_0"]


def test_validate_root_recognises_lowercase_x_as_matched(tmp_path):
    """D9: lowercase-x files count toward the per-Z quota, not toward
    per_z_skipped."""
    z = tmp_path / "Z6_1"
    z.mkdir()
    (z / "x5_0_666_786_XANES.txt").write_text("")
    r = pl.validate_root(tmp_path)
    assert r.per_z_count["Z6_1"] == 1
    assert "Z6_1" not in r.per_z_skipped

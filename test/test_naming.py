"""Filename regex, ZDIR regex, and parse_section field extraction.

version 1.1 by Albert Sheng
"""
from __future__ import annotations

from pathlib import Path

import pipeline as pl


def test_fname_re_single_digit():
    m = pl.FNAME_RE.match("X0_5_1_120_XANES.txt")
    assert m and m.groups() == ("0", "5", "1", "120")


def test_fname_re_double_digit_negative_x():
    m = pl.FNAME_RE.match("X10_-5_1338_1458_XANES.txt")
    assert m and m.groups() == ("10", "-5", "1338", "1458")


def test_fname_re_rejects_wrong_prefix():
    assert pl.FNAME_RE.match("Y0_5_1_120_XANES.txt") is None


def test_fname_re_is_case_insensitive():
    """v1.3 (D9 fix): lowercase 'x' filenames must be matched."""
    m = pl.FNAME_RE.match("x5_0_666_786_XANES.txt")
    assert m is not None
    assert m.groups() == ("5", "0", "666", "786")


def test_fname_re_rejects_missing_suffix():
    assert pl.FNAME_RE.match("X0_5_1_120.txt") is None


def test_zdir_re_negative_z():
    assert pl.ZDIR_RE.match("Z0_-5")


def test_zdir_re_zero_z():
    assert pl.ZDIR_RE.match("Z5_0")


def test_zdir_re_double_digit():
    assert pl.ZDIR_RE.match("Z10_5")


def test_zdir_re_rejects_non_z():
    assert pl.ZDIR_RE.match("Q0_0") is None
    assert pl.ZDIR_RE.match("Z_5") is None


def test_parse_section_center():
    root = Path("dummy")
    txt = root / "Z5_0" / "X5_0_668_788_XANES.txt"
    sec = pl.parse_section(txt, root)
    assert sec is not None
    assert (sec.i, sec.j, sec.z, sec.x) == (5, 5, 0, 0)
    assert (sec.seg_start, sec.seg_end) == (668, 788)
    assert sec.stem == "X5_0_668_788"


def test_parse_section_top_left_corner():
    root = Path("dummy")
    txt = root / "Z10_5" / "X10_-5_1338_1458_XANES.txt"
    sec = pl.parse_section(txt, root)
    assert sec.i == 10 and sec.z == 5
    assert sec.j == 10 and sec.x == -5


def test_parse_section_bottom_right_corner():
    root = Path("dummy")
    txt = root / "Z0_-5" / "X0_5_1_120_XANES.txt"
    sec = pl.parse_section(txt, root)
    assert sec.i == 0 and sec.z == -5
    assert sec.j == 0 and sec.x == 5


def test_parse_section_all_121_cells_consistent():
    """Every (i, j) in the grid should parse and satisfy x = 5-j, z = i-5."""
    root = Path("dummy")
    for i in range(11):
        for j in range(11):
            z = i - 5
            x = 5 - j
            txt = root / f"Z{i}_{z}" / f"X{j}_{x}_1_120_XANES.txt"
            sec = pl.parse_section(txt, root)
            assert sec is not None, txt
            assert sec.x == 5 - sec.j, txt
            assert sec.z == sec.i - 5, txt


def test_parse_section_rejects_bad_filename():
    root = Path("dummy")
    assert pl.parse_section(root / "Z5_0" / "bad.txt", root) is None


def test_parse_section_rejects_non_z_parent():
    root = Path("dummy")
    assert pl.parse_section(root / "not_a_z" / "X5_0_1_120_XANES.txt", root) is None


def test_section_paths_use_module_roots():
    """Section .npz_path / .png paths must derive from pl.DATA_ROOT / pl.IMAGE_ROOT
    so monkeypatching the roots redirects output."""
    root = Path("dummy")
    txt = root / "Z5_0" / "X5_0_668_788_XANES.txt"
    sec = pl.parse_section(txt, root)
    assert str(sec.npz_path).startswith(str(pl.DATA_ROOT))
    assert str(sec.preedge_png).startswith(str(pl.IMAGE_ROOT))
    assert sec.npz_path.name == "X5_0_668_788.npz"
    assert sec.json_path.name == "X5_0_668_788.json"
    assert sec.preedge_png.name == "X5_0_668_788_preedge.png"
    assert sec.norm_png.name == "X5_0_668_788_norm.png"

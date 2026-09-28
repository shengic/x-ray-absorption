"""
Generate NiXZ-121_Report.docx (technical report + user manual).

Part 1: theory + algorithm description (journal-style)
Part 2: user manual for the Tk GUI + CLI

Equations use OMML (Office MathML) so Word can render them natively.
Run:
    python build_report.py

version 1.0 by Albert Sheng
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, Cm
from lxml import etree

# --------------------------------------------------------------------------
# OMML helpers -- build small pieces of Office MathML as raw XML strings and
# stitch them together, then parse into an lxml element for insertion.
# --------------------------------------------------------------------------
NS_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"


def _r(text: str, italic: bool = False) -> str:
    if italic:
        return (
            f'<m:r xmlns:m="{NS_M}">'
            f'<m:rPr><m:sty m:val="i"/></m:rPr>'
            f'<m:t xml:space="preserve">{text}</m:t></m:r>'
        )
    return (
        f'<m:r xmlns:m="{NS_M}">'
        f'<m:t xml:space="preserve">{text}</m:t></m:r>'
    )


def _sub(base: str, sub: str) -> str:
    return (
        f'<m:sSub xmlns:m="{NS_M}">'
        f'<m:e>{base}</m:e><m:sub>{sub}</m:sub></m:sSub>'
    )


def _sup(base: str, sup: str) -> str:
    return (
        f'<m:sSup xmlns:m="{NS_M}">'
        f'<m:e>{base}</m:e><m:sup>{sup}</m:sup></m:sSup>'
    )


def _frac(num: str, den: str) -> str:
    return (
        f'<m:f xmlns:m="{NS_M}">'
        f'<m:num>{num}</m:num><m:den>{den}</m:den></m:f>'
    )


def _sqrt(inner: str) -> str:
    return f'<m:rad xmlns:m="{NS_M}"><m:deg/><m:e>{inner}</m:e></m:rad>'


def _sum(lower: str, upper: str, body: str) -> str:
    return (
        f'<m:nary xmlns:m="{NS_M}">'
        f'<m:naryPr><m:chr m:val="∑"/></m:naryPr>'
        f'<m:sub>{lower}</m:sub><m:sup>{upper}</m:sup>'
        f'<m:e>{body}</m:e></m:nary>'
    )


def add_display_math(doc: Document, body_xml: str) -> None:
    """Insert a display equation (oMathPara wrapping oMath) into the doc."""
    xml = (
        f'<m:oMathPara xmlns:m="{NS_M}"><m:oMath>{body_xml}</m:oMath>'
        f'</m:oMathPara>'
    )
    element = etree.fromstring(xml)
    p = doc.add_paragraph()
    p._p.append(element)


def add_inline_math(paragraph, body_xml: str) -> None:
    xml = f'<m:oMath xmlns:m="{NS_M}">{body_xml}</m:oMath>'
    paragraph._p.append(etree.fromstring(xml))


# --------------------------------------------------------------------------
# Doc setup + styling helpers
# --------------------------------------------------------------------------
def make_doc() -> Document:
    doc = Document()
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Georgia"
    normal.font.size = Pt(11)
    # East Asian font (Word respects w:eastAsia for CJK glyphs)
    from docx.oxml.ns import qn
    normal_rpr = normal.element.get_or_add_rPr()
    rfonts = normal_rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = etree.SubElement(normal_rpr, qn("w:rFonts"))
    rfonts.set(qn("w:ascii"), "Georgia")
    rfonts.set(qn("w:hAnsi"), "Georgia")
    rfonts.set(qn("w:eastAsia"), "標楷體")  # 標楷體
    for hstyle in ("Heading 1", "Heading 2", "Heading 3"):
        h = styles[hstyle]
        h.font.name = "Georgia"
        h_rpr = h.element.get_or_add_rPr()
        h_rfonts = h_rpr.find(qn("w:rFonts"))
        if h_rfonts is None:
            h_rfonts = etree.SubElement(h_rpr, qn("w:rFonts"))
        h_rfonts.set(qn("w:ascii"), "Georgia")
        h_rfonts.set(qn("w:hAnsi"), "Georgia")
        h_rfonts.set(qn("w:eastAsia"), "標楷體")
    section = doc.sections[0]
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)
    return doc


def h1(doc: Document, text: str) -> None:
    p = doc.add_heading(text, level=1)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT


def h2(doc: Document, text: str) -> None:
    doc.add_heading(text, level=2)


def h3(doc: Document, text: str) -> None:
    doc.add_heading(text, level=3)


def para(doc: Document, text: str) -> None:
    doc.add_paragraph(text)


def code(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)


def bullet(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="List Bullet")


def numbered(doc: Document, text: str) -> None:
    doc.add_paragraph(text, style="List Number")


def make_table(doc: Document, header, rows) -> None:
    tbl = doc.add_table(rows=1 + len(rows), cols=len(header))
    tbl.style = "Light Grid Accent 1"
    for j, h in enumerate(header):
        cell = tbl.rows[0].cells[j]
        cell.text = h
        for run in cell.paragraphs[0].runs:
            run.font.bold = True
            run.font.size = Pt(10)
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = tbl.rows[i].cells[j]
            cell.text = str(v)
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(9)


# --------------------------------------------------------------------------
# Part 1 -- Technical Report
# --------------------------------------------------------------------------
def part1(doc: Document) -> None:
    h1(doc, "Part I. Technical Report")

    h2(doc, "Abstract")
    para(
        doc,
        "We describe a two-stage automated quality-control pipeline for a "
        "spatially resolved X-ray absorption near-edge structure (XANES) "
        "dataset acquired at the NSRRC TPS 44A quick-EXAFS (QEXAFS) beamline "
        "on a Ni sample scanned over an 11 x 11 spatial grid (121 sections "
        "total). Stage one applies the standard xraylarch pre_edge routine "
        "to obtain edge energy E0, edge step Delta mu 0, and normalized "
        "absorption per cell. Stage two evaluates eleven configurable rules "
        "producing two orthogonal per-cell flags -- smooth (measurement "
        "quality) and consistent (grid-wide chemistry agreement) -- via "
        "robust median-absolute-deviation z-scores computed against only "
        "cells that pass a hard edge_step gate. Thresholds are data-driven, "
        "calibrated from the observed 121-cell distributions. A dedicated "
        "rule (C-CUMDIFF) implements Lippold et al.'s criterion 7 adapted "
        "to spatial mapping: the reference is the 8-neighbour mean rather "
        "than a scan leave-one-out average. The full workflow is exposed "
        "through a Tk GUI and a headless CLI, with all thresholds and edge "
        "parameters editable from a single tabbed configuration panel."
    )

    # ----------------------------------------------------------------------
    h2(doc, "1. Introduction")
    para(
        doc,
        "The NiXZ-121 dataset was acquired on 2025-12-09 at NSRRC TPS 44A "
        "using a Si(111) monochromator operated at 1 Hz DAC drive. The "
        "beam was rastered over an 11 x 11 grid, producing 121 averaged "
        "XANES spectra (approximately 120 scans averaged per section) in "
        "transmission mode. Each averaged file contains 4000 energy points "
        "from 8058 to 9241 eV, sampling the Ni K-edge (nominal E0 = 8333 "
        "eV) at approximately 0.30 eV step. The chemical state at each "
        "spatial location must be inferred from the resulting spectrum, "
        "but only after establishing that the measurement itself is "
        "trustworthy. Manual visual screening of 121 spectra is impractical "
        "in a production workflow, motivating the automated framework "
        "described here."
    )
    para(
        doc,
        "Existing XAS quality-control literature focuses either on single "
        "bulk-transmission spectra (Gaur et al. 2026) or on repeated scans "
        "of the same sample (Lippold et al. 2005). Neither directly "
        "addresses the spatial-mapping case, where genuine chemical "
        "differences between neighbouring cells must be preserved rather "
        "than flagged as artefacts. Our two-flag design (smooth vs "
        "consistent) preserves this distinction: a cell whose consistent "
        "flag fires but whose smooth flag is clean represents a candidate "
        "for further chemical analysis, not a candidate for exclusion."
    )

    # ----------------------------------------------------------------------
    h2(doc, "2. Dataset")

    h3(doc, "2.1 Naming and coordinates")
    para(
        doc,
        "The dataset is stored under image_AI_Ni/. Row i in {0, ..., 10} "
        "corresponds to a folder Z{i}_{z} with z = i - 5. Column j in "
        "{0, ..., 10} corresponds to a file X{j}_{x}_{start}_{end}_XANES.txt "
        "with x = 5 - j (note that the X index runs opposite to its "
        "physical x-coordinate). Uniqueness therefore requires the pair "
        "(zdir, filename); the filename alone is ambiguous because segment "
        "indices repeat across Z folders. The centre of the grid, (x, z) = "
        "(0, 0), lives at Z5_0/X5_0_668_788_XANES.txt."
    )

    h3(doc, "2.2 File format")
    para(
        doc,
        "Each per-cell file follows the JAQ 3.3.53+ QEXAFS raw text schema. "
        "The header lists the beamline software version, DAC / ADC "
        "configuration, absorber (Ni), edge energy (8333 eV per the JAQ "
        "settings), the averaged spectrum indices, and the source .bin "
        "file. Data columns are: point index, energy in eV, mu = ln(col0 / "
        "col1) for the sample transmission channel, and mu_ref = ln(col1 / "
        "col2) for the reference channel used for absolute energy "
        "calibration."
    )

    # ----------------------------------------------------------------------
    h2(doc, "3. Stage 1 -- Pre-edge Subtraction and Normalization")
    para(
        doc,
        "Stage one closely follows the xraylarch documentation (Newville, "
        "xraylarch 2026.3.1, section 14.2). For each cell we:"
    )
    numbered(doc, "Read energy, mu, mu_ref via numpy.loadtxt with comments='#'.")
    numbered(
        doc,
        "Determine E0 as the maximum of the first derivative dmu/dE, "
        "computed by numpy.gradient."
    )
    numbered(
        doc,
        "Fit a linear pre-edge in the window [E0 + pre1, E0 + pre2] and a "
        "polynomial post-edge in [E0 + norm1, E0 + norm2]. The polynomial "
        "order nnorm defaults to 2 for windows wider than 350 eV; the "
        "pre-edge fit uses nvict = 0."
    )
    numbered(
        doc,
        "Compute the edge step:"
    )
    add_display_math(
        doc,
        _sub(_r("Δμ", italic=True), _r("0"))
        + _r(" = ")
        + _r("post(")
        + _sub(_r("E", italic=True), _r("0"))
        + _r(") − pre(")
        + _sub(_r("E", italic=True), _r("0"))
        + _r(")")
    )
    numbered(
        doc,
        "Compute the normalized and flattened spectra:"
    )
    # norm = (mu - pre) / Delta_mu_0
    norm_eq = (
        _r("norm(", italic=True) + _r("E", italic=True) + _r(")")
        + _r(" = ")
        + _frac(
            _r("μ(", italic=True) + _r("E", italic=True) + _r(") − pre(")
            + _r("E", italic=True) + _r(")"),
            _sub(_r("Δμ", italic=True), _r("0"))
        )
    )
    add_display_math(doc, norm_eq)
    para(
        doc,
        "The flat variant additionally subtracts the post-edge polynomial "
        "above E0 so that residual atomic absorption is removed and the "
        "post-edge baseline sits at unity."
    )
    numbered(
        doc,
        "Compute six scalar quality metrics Q1-Q6 (edge step, high-frequency "
        "post-edge noise, pre-edge fit residual, E0 shift versus reference "
        "channel, glitch count, white-line height), an edge-derivative "
        "full-width at half-maximum, and persist the pre_edge polynomial "
        "coefficients pre_slope, norm_c0, norm_c1, norm_c2."
    )
    para(
        doc,
        "The per-cell output is a compressed .npz containing all arrays "
        "(energy, mu, mu_ref, pre_edge line, post_edge curve, norm, flat, "
        "e0, edge_step in float32) plus a JSON sidecar with scalar metadata "
        "and metrics. Two PNG plots (pre-edge subtraction and normalized/"
        "flattened views) are also produced for offline inspection."
    )

    # ----------------------------------------------------------------------
    h2(doc, "4. Stage 2 -- Rule-based Quality Assessment")

    h3(doc, "4.1 Framework")
    para(
        doc,
        "Stage two operates entirely on the stage-one cache; xraylarch is "
        "not called. Each of eleven rules produces a RuleResult with one "
        "of four levels: PASS (0), WARN (1), FAIL (2), or N/A (not "
        "applicable). Rules are tagged with a flag in {gate, smooth, "
        "consistent} and a scope in {cell, grid}. A dependency graph "
        "(requires) determines topological execution order. Two flags per "
        "cell are then produced by the worst-of combination:"
    )
    add_display_math(
        doc,
        _r("smooth", italic=True) + _r(" = ")
        + _r("max")
        + _r("{ ")
        + _r("level", italic=True)
        + _r(" : ")
        + _r("rule", italic=True)
        + _r(" ∈ smooth, rule evaluated }")
    )
    add_display_math(
        doc,
        _r("consistent", italic=True) + _r(" = ")
        + _r("max")
        + _r("{ ")
        + _r("level", italic=True)
        + _r(" : ")
        + _r("rule", italic=True)
        + _r(" ∈ consistent, rule evaluated }")
    )
    para(
        doc,
        "A cell is deemed usable when the GATE-EDGE gate passes and smooth "
        "is PASS or WARN. The consistent flag deliberately does not affect "
        "usability, because a consistent-only failure may indicate real "
        "chemistry rather than a measurement fault."
    )

    h3(doc, "4.2 Robust z-score")
    para(
        doc,
        "All grid-scoped rules use a robust z-score based on median and "
        "median-absolute deviation (MAD), following Leys et al. 2013:"
    )
    z_eq = (
        _sub(_r("z", italic=True), _r("k")) + _r(" = ")
        + _frac(
            _sub(_r("v", italic=True), _r("k")) + _r(" − median(")
            + _r("v", italic=True) + _r(")"),
            _r("1.4826 · MAD(") + _r("v", italic=True) + _r(")")
        )
    )
    add_display_math(doc, z_eq)
    para(
        doc,
        "The scale factor 1.4826 ensures that the resulting z is unit-"
        "normal-distributed for large samples drawn from N(0, sigma^2). "
        "Median and MAD are computed only over cells passing GATE-EDGE, so "
        "off-sample pixels do not skew the baseline. When MAD evaluates to "
        "zero (unrealistically uniform grid), the rule returns N/A rather "
        "than falsely PASSing."
    )

    h3(doc, "4.3 Energy calibration")
    para(
        doc,
        "The mu_ref channel provides an absolute-energy reference. Its E0 "
        "on the current dataset is offset from the tabulated Ni K value "
        "(8333 eV) by approximately +13 eV, reflecting a systematic "
        "monochromator scaling error. We therefore compute a per-cell "
        "energy correction:"
    )
    shift_eq = (
        _sub(_r("shift", italic=True), _r("k")) + _r(" = ")
        + _sub(_r("E", italic=True), _r("0,ref,k"))
        + _r(" − median(")
        + _sub(_r("E", italic=True), _r("0,ref"))
        + _r(")")
    )
    add_display_math(doc, shift_eq)
    para(
        doc,
        "This shift is applied both to the energy axis when interpolating "
        "spectra onto a common grid (for C-SHAPE and C-CUMDIFF), and to "
        "the sample E0 when comparing to neighbours (for C-E0-NBR). "
        "Note that we align to the grid median rather than to the "
        "tabulated absolute value; the absolute monochromator offset is "
        "monitored separately by the CAL-EREF L1 check."
    )

    h3(doc, "4.4 Rule catalogue")
    para(
        doc,
        "The current implementation registers the following eleven rules. "
        "Each row lists the rule ID, flag, scope, prerequisite rules, and "
        "the underlying observable."
    )
    make_table(
        doc,
        ["ID", "Flag", "Scope", "Requires", "Observable / decision"],
        [
            ["GATE-EDGE", "gate", "cell", "-",
             "edge_step in [min, max]; else FAIL, excluded from baseline"],
            ["CAL-EREF", "gate", "grid", "-",
             "L1: mu_ref_e0 - e0_nominal in mono_offset_window; L3: |mu_ref_e0 - median| < ref_e0_spread_tol"],
            ["R-SNR", "smooth", "grid", "GATE-EDGE",
             "SNR = edge_step / q3_pre_flatness; lower-tail robust z"],
            ["R-NOISE-HF", "smooth", "grid", "GATE-EDGE",
             "RMS of 2nd difference of flat for E >= E0 + 150 eV; upper-tail z"],
            ["R-PRE-FLAT", "smooth", "grid", "GATE-EDGE",
             "Pre-edge linear-fit residual RMS; upper-tail z"],
            ["R-GLITCH", "smooth", "grid", "GATE-EDGE",
             "MAD-outlier point count on flat for E >= E0 + 150; abs > max_count => FAIL"],
            ["R-EDGE-FWHM", "smooth", "grid", "GATE-EDGE",
             "FWHM of dmu/dE in E0 +/- 15 eV; two-sided z"],
            ["R-NORM-COEFS", "smooth", "grid", "GATE-EDGE",
             "max|z| over pre_slope, norm_c1, norm_c2"],
            ["C-SHAPE", "consistent", "grid", "GATE-EDGE, CAL-EREF",
             "R-factor of interpolated norm vs cross-cell pointwise median; upper-tail z"],
            ["C-E0-NBR", "consistent", "grid", "GATE-EDGE, CAL-EREF",
             "Corrected E0 vs 8-neighbour median; two-sided z"],
            ["C-CUMDIFF", "consistent", "grid", "GATE-EDGE, CAL-EREF",
             "Lippold 2005 criterion 7 vs 8-neighbour mean; upper-tail z (opt-in)"],
        ]
    )

    h3(doc, "4.5 Consistency rules")
    para(
        doc,
        "C-SHAPE quantifies overall spectral shape agreement using the "
        "Ravel and Newville R-factor. Cells passing GATE-EDGE and CAL-EREF "
        "have their corrected norm interpolated onto the common grid "
        "[E0_med - 30, E0_med + 150] eV at 0.30 eV step. The pointwise "
        "median across all interpolated cells forms the reference n_med, "
        "and each cell's residual is:"
    )
    r_eq = (
        _sub(_r("R", italic=True), _r("k")) + _r(" = ")
        + _frac(
            _sum(
                _r("i"),
                _r("N"),
                _sup(_r("("), _r("")) + _sub(_r("n"), _r("k,i"))
                + _r(" − ")
                + _sub(_r("n"), _r("med,i"))
                + _sup(_r(")"), _r("2"))
            ),
            _sum(
                _r("i"),
                _r("N"),
                _sup(_sub(_r("n"), _r("med,i")), _r("2"))
            )
        )
    )
    add_display_math(doc, r_eq)
    para(
        doc,
        "One-sided upper MAD z applied to R_k identifies outlier shapes."
    )
    para(
        doc,
        "C-CUMDIFF implements Lippold et al.'s criterion 7 with the "
        "reference redefined as the mean of the eight spatial neighbours "
        "rather than a scan-wise leave-one-out average. Given corrected "
        "spectra spec and reference ref on the same grid:"
    )
    D_eq = (
        _r("D(") + _r("i") + _r(") = ")
        + _r("spec(") + _r("i") + _r(") − ref(") + _r("i") + _r(")")
    )
    add_display_math(doc, D_eq)
    A_eq = (
        _r("A(") + _r("j") + _r(") = ")
        + _sum(
            _r("i = 1"),
            _r("j"),
            _r("D(") + _r("i") + _r(")")
        )
    )
    add_display_math(doc, A_eq)
    para(
        doc,
        "Criterion 7 is the standard deviation of A(j) after a linear-"
        "regression detrend. Cumulative summation amplifies four archetypal "
        "systematic deviations (group offsets, jump discontinuities, slope "
        "changes, periodic bending) while attenuating random noise. Cells "
        "with fewer than two valid spatial neighbours on the common grid "
        "return N/A. The Lippold paper's absolute stopping threshold (0.1) "
        "is system-specific and is not applied here; a grid-relative MAD z-"
        "score is used instead."
    )
    para(
        doc,
        "C-E0-NBR compares each cell's corrected E0 against the median of "
        "its up to eight spatial neighbours' corrected E0s, applying a two-"
        "sided robust z-score. Because a hit here can indicate genuine "
        "chemistry, only the consistent flag is affected."
    )

    h3(doc, "4.6 Threshold calibration")
    para(
        doc,
        "GATE-EDGE bounds and rule z-thresholds were calibrated against "
        "the actual 121-cell distributions observed on the current dataset "
        "rather than adopted from bulk-spectrum literature."
    )
    para(
        doc,
        "The edge_step distribution is bimodal: 6 cells cluster at [0.043, "
        "0.062] (off-sample / near-void pixels), a natural gap sits at "
        "[0.099, 0.131] with only 2 cells, and the remaining 110 real "
        "cells populate [0.13, 0.93]. The chosen lower bound 0.10 sits in "
        "the gap; 90.9% of cells pass. All 11 failures lie on the sample's "
        "geometric left edge (X10_-5 column) or corners, consistent with "
        "the intended semantics of GATE-EDGE. The Gaur 2026 recommendation "
        "of [0.5, 2.0] would reject 102 of 121 cells and is therefore "
        "inappropriate for spatial mapping."
    )
    para(
        doc,
        "For R-EDGE-FWHM and R-NORM-COEFS the 110 gate-pass values are "
        "near-Gaussian (percentile ratio P50(|z|)/max ~ 0.67, matching "
        "the theoretical N(0,1) MAD/max ratio 0.6745). The old defaults "
        "warn_z = 3, fail_z = 5 correspond to 3-sigma and 5-sigma "
        "respectively; on n = 110 the 5-sigma level triggers essentially "
        "never (theoretical rate 6e-7). We therefore adopted warn_z = 2.5 "
        "(Leys 2013 default) and fail_z = 4 (clear outlier line for a "
        "near-Gaussian). Under the new thresholds R-EDGE-FWHM flags 3 "
        "WARN 0 FAIL and R-NORM-COEFS flags 2 WARN 0 FAIL, while any "
        "future outlier at |z| >= 4 is caught immediately."
    )

    # ----------------------------------------------------------------------
    h2(doc, "5. Implementation")
    h3(doc, "5.1 Software architecture")
    para(
        doc,
        "The system is implemented in Python 3.11+, with xraylarch 2026.3.1 "
        "for pre_edge and numpy for numerical operations. Persistence uses "
        "a file-based cache (.npz and .json under data/, .png under image/) "
        "that maps one-to-one onto a planned MySQL schema with tables for "
        "sections, per-cell spectra, per-cell quality metrics, per-rule "
        "results, and per-run manifests. Database wiring is deferred until "
        "the schema is finalised; the file cache is authoritative in the "
        "interim."
    )
    para(
        doc,
        "The rule registry uses a decorator pattern. Each rule function "
        "receives a Context object (grid statistics, corrected shifts, "
        "interpolated spectra), the target Cell, and the parameter block "
        "from config.yaml, and returns a RuleResult. Adding a new rule "
        "requires only a decorated function plus an entry in config.yaml; "
        "the topological executor picks it up automatically."
    )

    h3(doc, "5.2 Cache layout")
    code(
        doc,
        "data/\n"
        "  examine_run.json                run manifest\n"
        "  Z0_-5/\n"
        "    X0_5_1_120.npz                arrays (float32)\n"
        "    X0_5_1_120.json               pipeline metrics\n"
        "    X0_5_1_120.examine.json       rule verdict\n"
        "    ...\n"
        "image/\n"
        "  Z0_-5/\n"
        "    X0_5_1_120_preedge.png\n"
        "    X0_5_1_120_norm.png"
    )

    h3(doc, "5.3 Reproducibility")
    para(
        doc,
        "The run manifest records a SHA-256 canonical hash of the full "
        "config.yaml used to produce that run, together with a UUID run_id, "
        "computed_at timestamp (UTC ISO-8601), pipeline version, combine "
        "mode, and full baseline statistics. Two runs with identical config "
        "hashes are guaranteed to produce identical verdicts on the same "
        "cache."
    )

    # ----------------------------------------------------------------------
    h2(doc, "6. Results on the NiXZ-121 grid")
    para(
        doc,
        "The current 121-cell run (run 987973d5, 2026-09-28) reports:"
    )
    make_table(
        doc,
        ["Level", "smooth (n = 121)", "consistent (n = 121)"],
        [
            ["PASS", "69", "48"],
            ["WARN", "7", "1"],
            ["FAIL", "34", "61"],
            ["N/A", "11", "11"],
        ]
    )
    para(
        doc,
        "76 of 121 cells (62.8%) are marked usable. Per-rule tallies are:"
    )
    make_table(
        doc,
        ["Rule", "PASS", "WARN", "FAIL", "N/A"],
        [
            ["GATE-EDGE", "110", "0", "11", "0"],
            ["CAL-EREF", "44", "77", "0", "0"],
            ["R-SNR", "110", "0", "0", "11"],
            ["R-NOISE-HF", "104", "4", "2", "11"],
            ["R-PRE-FLAT", "108", "2", "0", "11"],
            ["R-GLITCH", "78", "0", "32", "11"],
            ["R-EDGE-FWHM", "107", "3", "0", "11"],
            ["R-NORM-COEFS", "108", "2", "0", "11"],
            ["C-SHAPE", "66", "1", "43", "11"],
            ["C-E0-NBR", "67", "0", "43", "11"],
            ["C-CUMDIFF", "0", "0", "0", "121"],
        ]
    )
    para(
        doc,
        "Consistent failures dominate over smooth failures (61 vs 34), "
        "suggesting that most of the current unusability is driven by "
        "spatial variation rather than raw measurement noise. CAL-EREF "
        "reports 77 L3 WARN cells, indicating a smooth cross-grid drift "
        "in mu_ref E0 beyond the initial 0.3 eV L3 tolerance; this warrants "
        "inspection of the row-time correlation given the ~2.5-hour "
        "acquisition span, and possibly loosening ref_e0_spread_tol_eV. "
        "C-CUMDIFF is disabled by default (all 121 N/A); enabling it "
        "provides an independent structural-deviation cross-check for "
        "cells that pass C-SHAPE but exhibit hidden systematic patterns."
    )

    # ----------------------------------------------------------------------
    h2(doc, "7. Conclusions and future work")
    para(
        doc,
        "The two-flag design (smooth versus consistent) proved decisive: "
        "it lets an operator distinguish measurement problems from real "
        "chemistry without collapsing both into a single usable flag. The "
        "MAD-based grid-relative thresholds adapt to whichever beamline "
        "resolution and mu_ref calibration the current session happens to "
        "have, reducing the need for beamline-specific tuning."
    )
    para(
        doc,
        "Immediate next steps are: (i) confirm the reference standard is "
        "Ni foil so that mu_ref-based absolute calibration is well defined; "
        "(ii) implement the per-scan rules T-DRIFT, T-UPDOWN, T-OUTLIER-"
        "SCAN, T-SATURATION once the .bin per-scan format is documented; "
        "(iii) migrate the file cache into MySQL once the schema is "
        "finalised; and (iv) evaluate a weighted combine mode as an "
        "alternative to the current worst-of-scoring."
    )

    # ----------------------------------------------------------------------
    h2(doc, "References")
    para(
        doc,
        "The following sources ground individual rule choices; verification "
        "status column indicates whether the original text was consulted "
        "in full for this project."
    )
    make_table(
        doc,
        ["#", "Reference", "Used for", "Verified"],
        [
            ["1", "M. Newville, xraylarch 2026.3.1 documentation section 14.2",
             "pre_edge algorithm and outputs", "yes"],
            ["2", "M. Newville, xraylarch section 14.1 (estimate_noise)",
             "confirmed as EXAFS chi(R) tool; not used here", "partially"],
            ["3", "Y. Liu et al., TXM-Wizard, J. Synchrotron Rad. 19, 281 (2012)",
             "GATE-EDGE lower bound, R-SNR, R-PRE-FLAT, C-E0-NBR concept",
             "yes"],
            ["4", "T.-C. Weng et al., MBACK, J. Synchrotron Rad. 12, 506 (2005)",
             "alternative normalization, not adopted", "bibliography only"],
            ["5", "B. Lippold et al., J. Synchrotron Rad. 12, 45 (2005)",
             "C-CUMDIFF (criterion 7), reserved T-OUTLIER-SCAN family",
             "yes"],
            ["6", "Gaur et al., Sci. Data (2026)",
             "GATE-EDGE upper bound, CAL-EREF concept, T-DRIFT motivation",
             "abstract-level"],
            ["7", "C. Leys et al., J. Exp. Soc. Psychol. 49, 764 (2013)",
             "MAD-based robust z; warn_z = 2.5 default", "bibliography only"],
            ["8", "E. A. Stern and K. Kim, Phys. Rev. B 23, 3781 (1981)",
             "thickness effect, GATE-EDGE upper bound physical basis",
             "bibliography only"],
            ["9", "B. Ravel and M. Newville, J. Synchrotron Rad. 12, 537 (2005)",
             "R-factor definition, C-SHAPE observable",
             "bibliography only"],
        ]
    )


# --------------------------------------------------------------------------
# Part 2 -- User Manual
# --------------------------------------------------------------------------
def part2(doc: Document) -> None:
    doc.add_page_break()
    h1(doc, "Part II. User Manual")

    h2(doc, "8. Installation")
    para(
        doc,
        "The application targets Python 3.11 or newer on Windows, macOS, "
        "and Linux, though it is developed and primarily tested on Windows "
        "11. To install:"
    )
    code(
        doc,
        "python -m venv .venv\n"
        ".venv\\Scripts\\python -m pip install -r requirements.txt"
    )
    para(
        doc,
        "The dependency tree pulled by xraylarch is large (scipy, lmfit, "
        "pymatgen, silx, h5py, sqlalchemy, plotly, mkl); first install "
        "takes several minutes. PyYAML is required for config parsing and "
        "pytest for the test suite."
    )

    h2(doc, "9. Data preparation")
    para(
        doc,
        "The application expects a dataset root folder containing per-Z-"
        "row subfolders named Z{i}_{z} (i in 0..10, z = i - 5). Each Z "
        "folder holds up to 11 files matching the pattern:"
    )
    code(doc, "X{j}_{x}_{start}_{end}_XANES.txt")
    para(
        doc,
        "Filename matching is case-insensitive (a legacy dataset had one "
        "file starting with a lowercase 'x'; regex now accepts both). "
        "Every filename that fails the regex is silently dropped by the "
        "loader; a validate_root call at batch startup reports both the "
        "number of X files per Z folder and any regex-rejected filenames "
        "so genuine typos are surfaced."
    )

    h2(doc, "10. GUI overview")
    para(
        doc,
        "Launch the GUI:"
    )
    code(doc, "python main.py")
    para(
        doc,
        "On startup you are prompted for the dataset root; the folder "
        "dialog opens at the project directory containing main.py. Pick "
        "image_AI_Ni/ (or wherever your dataset lives). The main window "
        "has three vertical panels (Z folders, X sections, Section info) "
        "and a top button bar."
    )

    h3(doc, "10.1 Top bar buttons")
    make_table(
        doc,
        ["Button", "Purpose"],
        [
            ["Choose root...", "Re-select the dataset root folder."],
            ["Process all (batch)",
             "Run Stage 1 pipeline over the whole tree. Progress bar advances; "
             "already-cached cells are skipped."],
            ["Examine 121",
             "Run Stage 2 (rule-based) over the whole cache. Auto-opens a "
             "results panel with usable count, flag breakdown, and per-rule "
             "tally."],
            ["Config...",
             "Open the tabbed Rules + Edge editor. See section 11."],
            ["11x11 heatmap",
             "Open the flag heatmap (colour by raw metric or by smooth / "
             "consistent / usable). Click any cell to jump-select it."],
            ["Rule violations",
             "Small-multiples: one 11x11 heatmap per rule. Click any cell "
             "to jump-select."],
        ]
    )

    h3(doc, "10.2 Three-panel browser")
    numbered(doc, "Click a Z folder in the left panel to list its X sections.")
    numbered(
        doc,
        "Single-click an X section to load its cache and populate the "
        "Section info panel (raw metrics Q1-Q6 plus, if Examine has been "
        "run, the rule-based smooth / consistent / usable summary)."
    )
    numbered(
        doc,
        "Double-click an X section to also open the Pre-edge and "
        "Normalized plot windows (singletons; the same window is re-drawn "
        "if opened again)."
    )

    h3(doc, "10.3 Plot windows")
    para(
        doc,
        "Three plot kinds are available:"
    )
    bullet(
        doc,
        "Pre-edge plot -- mu(E) with the fitted pre-edge line and post-"
        "edge polynomial overlaid."
    )
    bullet(
        doc,
        "Normalized plot -- both norm (standard normalization) and flat "
        "(post-edge polynomial subtracted above E0) curves."
    )
    bullet(
        doc,
        "Both plots (combined) -- a single Toplevel with the two panels "
        "side by side, matching the reference image used during "
        "development."
    )
    para(
        doc,
        "Each kind has its own singleton window. Selecting a different "
        "cell simply updates whichever kinds are already open."
    )

    h2(doc, "11. Config editor")
    para(
        doc,
        "The Config... panel is a Toplevel with two tabs and a shared "
        "footer."
    )
    h3(doc, "11.1 Rules tab")
    para(
        doc,
        "One row per registered rule showing the rule ID as a blue "
        "underlined hyperlink, an enable/disable checkbox, the flag "
        "(gate / smooth / consistent), and editable Entry widgets for "
        "each numeric parameter (warn_z, fail_z, min, max, max_count as "
        "applicable). Clicking a rule ID opens a non-modal Traditional-"
        "Chinese help window explaining the rule's mathematics, "
        "dependencies, and parameters. The help window uses Georgia for "
        "Latin characters and DFKai-SB (biau kai) for CJK characters and "
        "can be left open while continuing to edit."
    )
    h3(doc, "11.2 Edge tab")
    para(
        doc,
        "One row per key in the config.yaml edge section. Two-element "
        "list values (mono_offset_window_eV and ref_e0_search_eV) are "
        "shown as [a , b] with two Entry widgets. Field names are "
        "clickable hyperlinks with descriptions of what CAL-EREF's L1 / "
        "L2 / L3 checks use each parameter for."
    )
    h3(doc, "11.3 Apply and save")
    para(
        doc,
        "The shared footer has one checkbox (Save to config.yaml on Apply, "
        "default off), an Apply & Examine button that writes both tabs' "
        "state into the in-memory config and immediately runs Examine, and "
        "a Close button. Nothing is written to disk unless Save is "
        "checked; unchecked edits are held in memory for subsequent "
        "Examine runs but revert if the application is restarted."
    )

    h2(doc, "12. Command-line usage")
    para(
        doc,
        "Two headless modes are available (no GUI). Both accept an "
        "optional --config path (default ./config.yaml)."
    )
    code(
        doc,
        "python main.py --batch image_AI_Ni\n"
        "python main.py --examine image_AI_Ni\n"
        "python main.py --batch image_AI_Ni --examine image_AI_Ni"
    )
    para(
        doc,
        "The --batch flag runs Stage 1 over every unprocessed cell in the "
        "dataset root. --examine runs Stage 2 over the current cache. "
        "Both can be combined in a single invocation to fully rebuild "
        "artefacts from raw text files."
    )

    h2(doc, "13. Reference: config.yaml")
    para(
        doc,
        "The config file has four top-level sections. All numeric values "
        "are starting seeds; nothing is hard-coded in the source."
    )
    code(
        doc,
        "grid:\n"
        "  n: 11                       # grid dimension (fixed at 11 x 11)\n"
        "\n"
        "edge:\n"
        "  element: Ni\n"
        "  edge: K\n"
        "  e0_nominal_eV: 8333.0        # CAL-EREF L1 reference\n"
        "  e0_alt_eV: 8331.90           # Info.txt alternate nominal\n"
        "  e0_nominal_tol_eV: 1.5       # CAL-EREF L2 tolerance\n"
        "  mono_offset_window_eV: [-5.0, 25.0]   # CAL-EREF L1 window\n"
        "  ref_e0_search_eV: [8320.0, 8370.0]    # find_e0 search bounds\n"
        "  ref_e0_spread_tol_eV: 0.3    # CAL-EREF L3 tolerance\n"
        "\n"
        "examine:\n"
        "  combine_mode: worst          # worst | weighted (not implemented)\n"
        "  shape_grid_eV: [-30.0, 150.0, 0.3]    # C-SHAPE common grid\n"
        "\n"
        "rules:\n"
        "  GATE-EDGE:    {enabled: true,  min: 0.10, max: 1.5}\n"
        "  CAL-EREF:     {enabled: true}\n"
        "  R-SNR:        {enabled: true,  warn_z: 3, fail_z: 5}\n"
        "  R-NOISE-HF:   {enabled: true,  warn_z: 3, fail_z: 5}\n"
        "  R-PRE-FLAT:   {enabled: true,  warn_z: 3, fail_z: 5}\n"
        "  R-GLITCH:     {enabled: true,  warn_z: 3, fail_z: 5, max_count: 5}\n"
        "  R-EDGE-FWHM:  {enabled: true,  warn_z: 2.5, fail_z: 4}\n"
        "  R-NORM-COEFS: {enabled: true,  warn_z: 2.5, fail_z: 4}\n"
        "  C-SHAPE:      {enabled: true,  warn_z: 3, fail_z: 5}\n"
        "  C-E0-NBR:     {enabled: true,  warn_z: 3, fail_z: 5}\n"
        "  C-CUMDIFF:    {enabled: false, warn_z: 3, fail_z: 5}\n"
        "\n"
        "db:\n"
        "  enabled: false               # MySQL wiring deferred"
    )

    h2(doc, "14. Cache layout on disk")
    para(
        doc,
        "All outputs live under data/ and image/, mirroring the Z-folder "
        "structure of the source dataset. The stem X{j}_{x}_{start}_{end} "
        "is always uppercase X, regardless of the source filename's case."
    )
    make_table(
        doc,
        ["File", "Producer", "Contents"],
        [
            ["data/{Zdir}/{stem}.npz",
             "Stage 1",
             "energy, mu, mu_ref, pre_edge, post_edge, norm, flat (float32); e0, edge_step scalars"],
            ["data/{Zdir}/{stem}.json",
             "Stage 1",
             "i, j, z, x, seg_start, seg_end, pre1, pre2, norm1, norm2, nnorm, nvict, pre_slope, norm_c0/1/2, Q1-Q6, edge_fwhm_eV, mu_ref_e0, usable (legacy)"],
            ["data/{Zdir}/{stem}.examine.json",
             "Stage 2",
             "run_id, smooth, consistent, usable, per-rule {level, value, reason}"],
            ["data/examine_run.json",
             "Stage 2",
             "run_id, computed_at, pipeline_version, config_hash, full config, combine_mode, n_cells, gate_pass count, baseline stats"],
            ["image/{Zdir}/{stem}_preedge.png",
             "Stage 1",
             "mu(E) with pre-edge line and post-edge curve overlaid"],
            ["image/{Zdir}/{stem}_norm.png",
             "Stage 1",
             "norm and flat curves"],
        ]
    )

    h2(doc, "15. Troubleshooting")
    para(
        doc,
        "Common issues and their resolutions:"
    )
    bullet(
        doc,
        "'py: import larch' fails on click. Larch is imported lazily "
        "inside pipeline.run_pre_edge to avoid slowing GUI startup. Ensure "
        "xraylarch is installed in the active venv and that the venv's "
        "Python is on PATH."
    )
    bullet(
        doc,
        "Heatmap has grey cells after Examine. Grey means either that "
        "cell was not in the cache (pipeline never ran on it) or the "
        "current metric is not defined for that cell. For flag mode, "
        "grey == N/A which happens when a required rule is disabled or "
        "the cell failed GATE-EDGE."
    )
    bullet(
        doc,
        "Rule violations window shows all N/A for a rule you enabled. "
        "That rule may require a dependency that is disabled. Check the "
        "rule's help popup (click its ID in the Config panel) for the "
        "requires list."
    )
    bullet(
        doc,
        "Cannot edit older cached cells' new fields (edge_fwhm_eV etc). "
        "Legacy caches predate pipeline v1.2 field additions. Trigger a "
        "reprocess: either delete data/**/*.json for those cells or run "
        "Reprocess from the Section info panel to force-recompute a single "
        "cell."
    )
    bullet(
        doc,
        "config.yaml edits in the GUI don't persist. Ensure the 'Save to "
        "config.yaml on Apply' checkbox in the Config panel footer is "
        "ticked before pressing Apply. In-memory edits are kept for the "
        "current session and thrown away on restart."
    )
    bullet(
        doc,
        "Windows glob is case-insensitive but the loader used to require "
        "uppercase X. Since pipeline v1.3 the FNAME_RE regex is case-"
        "insensitive; a stray 'x5_0_...' filename is now accepted. If "
        "your grid shows 120/121, look for such filenames or run "
        "validate_root to see what was rejected."
    )

    h2(doc, "16. Testing")
    para(
        doc,
        "The pytest suite (test/) covers regex and naming invariants, "
        "folder / file discovery, raw data format sanity, the pipeline "
        "round-trip (arrays and PNG artefacts), quality-metric shapes, "
        "cache I/O, a GUI import smoke test, and the examine engine "
        "including rule dispatch, N/A propagation from disabled "
        "dependencies, config-hash determinism, flag combination in worst "
        "mode, lippold_c7 identities on synthetic spectra, C-CUMDIFF jump "
        "detection, R-EDGE-FWHM broaden/narrow detection, and R-NORM-COEFS "
        "legacy-cache handling. Run:"
    )
    code(doc, "python -m pytest test/")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main() -> None:
    doc = make_doc()

    # Title page
    title = doc.add_heading("NiXZ-121 XANES Quality Assessment", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle = doc.add_paragraph(
        "Technical Report and User Manual"
    )
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    subtitle.runs[0].font.size = Pt(14)
    subtitle.runs[0].italic = True

    byline = doc.add_paragraph("Albert Sheng")
    byline.alignment = WD_ALIGN_PARAGRAPH.CENTER
    byline.runs[0].font.size = Pt(12)
    date_p = doc.add_paragraph(datetime.now().strftime("%Y-%m-%d"))
    date_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    date_p.runs[0].font.size = Pt(11)

    doc.add_paragraph("")
    doc.add_paragraph("")
    doc.add_paragraph(
        "This document has two parts. Part I is a technical description "
        "of the algorithms and thresholds used for automated quality "
        "control of the NiXZ-121 spatially resolved XANES dataset. Part II "
        "is a user manual for the accompanying application."
    )
    doc.add_page_break()

    part1(doc)
    part2(doc)

    out = Path("NiXZ-121_Report.docx")
    doc.save(out)
    print(f"wrote: {out.resolve()}")


if __name__ == "__main__":
    main()

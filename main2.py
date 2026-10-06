"""
NiXZ-121 XANES viewer — variant GUI with an interactive 11x11 heatmap.

Identical pipeline and rule engine to `main.py` (it subclasses that GUI, so
there is exactly one copy of the algorithm). Only the heatmap window differs:

  * same image as main.py -- same grid, colormap, extent and flag overlay
  * MOUSE MOVE over a cell  -> side panel shows that cell's file name,
    absorption header (E0, edge step, pre/post-edge windows, larch
    normalization coefficients) and Q1-Q6 + examine verdicts, live
  * CLICK a cell            -> opens the combined (pre-edge + normalized)
    plot window for that cell, with the same absorption info shown beside
    the figure, and syncs the main window's listboxes

All text is set in Georgia (GUI widgets and matplotlib figures alike).
Because Georgia is proportional, the report aligns its value column with a
Tk tab stop rather than space padding.

Run:
    python main2.py                          # GUI
    python main2.py --batch image_AI_Ni      # headless, delegates to main.py
    python main2.py --examine image_AI_Ni

version 1.1.0 by Albert Sheng
"""

from __future__ import annotations

import json
import sys
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np

try:
    import matplotlib
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg,
        NavigationToolbar2Tk,
    )
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
except ImportError:
    sys.exit("matplotlib required. Install: pip install matplotlib xraylarch")

import main as base
import pipeline as pl

# Every bit of text in this GUI is Georgia -- Tk widgets and figures alike.
UI_FONT = ("Georgia", 10)
REPORT_FONT = ("Georgia", 10)
#: Tk tab stop (pixels) that the report's value column lines up on. Georgia is
#: proportional, so space padding would not align.
REPORT_TAB = 150
matplotlib.rcParams["font.family"] = "Georgia"


# --------------------------------------------------------------------------
# Hover report (pure function -- no Tk, so it is directly unit-testable)
# --------------------------------------------------------------------------

def _fmt(value, spec: str = ".4f", na: str = "n/a") -> str:
    """Format an optional numeric cache field, tolerating missing keys."""
    if value is None:
        return na
    try:
        return format(float(value), spec)
    except (TypeError, ValueError):
        return str(value)


def hover_report(meta: dict, examine: dict | None) -> str:
    """Build the text shown while the cursor sits over a heatmap cell, and
    beside the combined plot window.

    `meta` is the pipeline cache `data/{Zdir}/{stem}.json`; `examine` is the
    matching `.examine.json`, or None when Examine has not been run.

    Label and value are separated by a tab, not by space padding: the GUI
    renders this in Georgia (proportional), so the value column is aligned by
    a Tk tab stop (`REPORT_TAB`) instead."""
    g = meta.get
    lines = [
        f"{g('zdir')}/{g('fname')}",
        f"(i, j) = ({g('i')}, {g('j')})"
        f"    (x, z) = ({g('x'):+d}, {g('z'):+d})",
        f"segment\t{g('seg_start')} - {g('seg_end')}",
        "",
        "-- absorption header --",
        f"E0 sample\t{_fmt(g('e0'), '.2f')} eV",
        f"E0 mu_ref\t{_fmt(g('mu_ref_e0'), '.2f')} eV",
        f"edge step dmu0\t{_fmt(g('edge_step'))}",
        f"edge FWHM\t{_fmt(g('edge_fwhm_eV'), '.2f')} eV",
        f"pre-edge win\tE0{_fmt(g('pre1'), '+.1f')}"
        f" .. E0{_fmt(g('pre2'), '+.1f')} eV",
        f"post-edge win\tE0{_fmt(g('norm1'), '+.1f')}"
        f" .. E0{_fmt(g('norm2'), '+.1f')} eV  (nnorm={g('nnorm')})",
        f"pre slope\t{_fmt(g('pre_slope'), '.3e')}",
        f"norm c0/c1/c2\t{_fmt(g('norm_c0'), '.3e')}"
        f"  {_fmt(g('norm_c1'), '.3e')}  {_fmt(g('norm_c2'), '.3e')}",
        "",
        "-- quality metrics --",
        f"Q1 edge step\t{_fmt(g('q1_edge_step'))}",
        f"Q2 hf noise RMS\t{_fmt(g('q2_hf_noise'), '.5f')}",
        f"Q3 pre-edge flat\t{_fmt(g('q3_pre_flatness'), '.5f')}",
        f"Q4 E0 vs ref\t{_fmt(g('q4_e0_shift_vs_ref'), '+.2f')} eV",
        f"Q5 glitches\t{g('q5_glitches')}",
        f"Q6 white line\t{_fmt(g('q6_white_line'), '.3f')}",
        f"usable (legacy)\t{'YES' if g('usable') else 'NO'}",
    ]

    if examine is None:
        lines += ["", "-- examine --", "not run"]
        return "\n".join(lines)

    e = examine.get
    lines += [
        "",
        "-- examine (rule-based) --",
        f"smooth\t{e('smooth')} "
        f"({e('smooth_evaluated', 0)}/{e('smooth_enabled', 0)})",
        f"consistent\t{e('consistent')} "
        f"({e('consistent_evaluated', 0)}/{e('consistent_enabled', 0)})",
        f"usable\t{'YES' if e('usable') else 'NO'}",
    ]
    flagged = [(rid, r) for rid, r in examine.get("rules", {}).items()
               if r.get("level_name") in ("WARN", "FAIL")]
    if flagged:
        lines.append("")
        lines.append("-- flagged rules --")
        for rid, r in flagged:
            val = r.get("value")
            tail = "" if val is None else f"  value={_fmt(val, '.4g')}"
            lines.append(f"{r['level_name']} {rid}{tail}")
            if r.get("reason"):
                lines.append(f"\t{r['reason']}")
    return "\n".join(lines)

# --------------------------------------------------------------------------
# GUI
# --------------------------------------------------------------------------

class HoverHeatmapViewer(base.XANESViewer):
    """main.py's viewer with a hover-aware, click-to-plot heatmap."""

    HIGHLIGHT_COLOR = "#0d47a1"

    def __init__(self, root: tk.Tk):
        super().__init__(root)
        root.title("NiXZ-121 XANES Viewer -- hover heatmap (main2)")
        self._cell_index: dict[tuple[int, int], dict] = {}
        self._hover_xz: tuple[int, int] | None = None
        self.hover_text: tk.Text | None = None
        self._heatmap_canvas = None     # set by _refresh_heatmap
        self._heatmap_ax = None
        self.combined_info_text: tk.Text | None = None
        self._apply_georgia()

    def _apply_georgia(self) -> None:
        """Put every widget in Georgia, including the ones main.py built.

        Retargeting Tk's *named* fonts does most of the work: it cascades to
        ttk widgets, to `_link_label`'s underlined links and to the bold
        `("TkDefaultFont", 9, "bold")` headers, all of which derive from them.
        Only the three widgets main.py pins to a literal ("Consolas", 10) need
        setting by hand. main.py itself is untouched -- its own GUI keeps
        Consolas; this applies to the main2 process only."""
        from tkinter import font as tkfont

        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont",
                     "TkHeadingFont", "TkTooltipFont", "TkFixedFont"):
            try:
                tkfont.nametofont(name).configure(family=UI_FONT[0])
            except tk.TclError:
                pass                                   # font not defined here
        self.root.option_add("*Font", UI_FONT)
        style = ttk.Style()
        style.configure(".", font=UI_FONT)
        style.configure("TLabelframe.Label", font=UI_FONT)
        style.configure("TNotebook.Tab", font=UI_FONT)

        for widget in (getattr(self, "lb_z", None), getattr(self, "lb_x", None)):
            if widget is not None:
                widget.configure(font=UI_FONT)
        if getattr(self, "info_text", None) is not None:
            self.info_text.configure(font=REPORT_FONT)

    def _open_examine_results(self, run) -> None:
        """main.py pins this window's Text to ("Consolas", 10); restyle it so
        main2 stays all-Georgia. Its ASCII bar chart is built from space
        padding, so it goes ragged in a proportional font -- that is the one
        place where all-Georgia costs alignment."""
        super()._open_examine_results(run)
        win = self.examine_results_window
        if win is None or not win.winfo_exists():
            return
        for child in win.winfo_children():
            if isinstance(child, tk.Text):
                child.configure(font=REPORT_FONT)

    # ---------------- heatmap ----------------

    def show_heatmap(self):
        super().show_heatmap()
        win = self.heatmap_window
        if win is not None and win.winfo_exists():
            win.title("11x11 heatmap -- hover for details, click for plots")
            win.geometry("1180x700")

    def _scan_cells(self, metric: str, is_flag: bool):
        """Walk the pipeline cache once: build the heatmap grid, the flag text
        overlay, and the per-cell lookup used by the hover panel.

        Grid layout matches main.py exactly: grid[i, 10 - j] with
        origin='lower' and extent (-5.5, 5.5, -5.5, 5.5)."""
        grid = np.full((11, 11), np.nan)
        labels: dict[tuple[int, int], str] = {}
        index: dict[tuple[int, int], dict] = {}

        for jf in pl.DATA_ROOT.rglob("*.json"):
            if jf.name.endswith(".examine.json") or jf.name == "examine_run.json":
                continue
            try:
                m = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            i, j = m.get("i"), m.get("j")
            if i is None or j is None:
                continue

            ex = None
            ex_path = jf.with_name(f"{jf.stem}.examine.json")
            if ex_path.exists():
                try:
                    ex = json.loads(ex_path.read_text(encoding="utf-8"))
                except Exception:
                    ex = None
            index[(i, j)] = {"meta": m, "examine": ex}

            row, col = i, 10 - j
            if is_flag:
                if ex is None:
                    continue
                if metric == "usable":
                    grid[row, col] = 0.0 if ex["usable"] else 2.0
                    labels[(row, col)] = "PASS" if ex["usable"] else "FAIL"
                else:
                    name = ex.get(metric, "N/A")
                    grid[row, col] = {"PASS": 0.0, "WARN": 1.0, "FAIL": 2.0,
                                      "N/A": np.nan}.get(name, np.nan)
                    labels[(row, col)] = name
            else:
                grid[row, col] = m.get(metric, np.nan)

        return grid, labels, index

    def _refresh_heatmap(self):
        for child in self._heatmap_body.winfo_children():
            child.destroy()
        metric = self.heatmap_metric.get()
        is_flag = metric in self.HEATMAP_FLAG
        grid, labels, self._cell_index = self._scan_cells(metric, is_flag)
        self._hover_xz = None

        pane = ttk.PanedWindow(self._heatmap_body, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(pane)
        right = ttk.LabelFrame(pane, text="Cell under cursor", padding=6)
        pane.add(left, weight=3)
        pane.add(right, weight=2)

        self.hover_text = tk.Text(right, wrap=tk.NONE, width=46, height=30,
                                  font=REPORT_FONT, tabs=(REPORT_TAB,),
                                  state=tk.DISABLED)
        self.hover_text.pack(fill=tk.BOTH, expand=True)
        ttk.Label(right, foreground="gray",
                  text="move the cursor over a cell for details\n"
                       "click a cell to open its combined plots").pack(
            anchor=tk.W, pady=(4, 0))

        fig = Figure(figsize=(6.4, 5.8), dpi=100)
        ax = fig.add_subplot(111)
        if is_flag:
            from matplotlib.colors import ListedColormap
            cmap = ListedColormap([self.FLAG_COLORS["PASS"],
                                   self.FLAG_COLORS["WARN"],
                                   self.FLAG_COLORS["FAIL"]])
            cmap.set_bad(self.FLAG_COLORS["N/A"])
            ax.imshow(grid, cmap=cmap, vmin=-0.5, vmax=2.5,
                      origin="lower", extent=(-5.5, 5.5, -5.5, 5.5))
        else:
            from matplotlib import colormaps
            cmap = colormaps.get_cmap("viridis").copy()
            cmap.set_bad("lightgray")
            im = ax.imshow(grid, cmap=cmap, origin="lower",
                           extent=(-5.5, 5.5, -5.5, 5.5))
            fig.colorbar(im, ax=ax)
        ax.set_xlabel("x")
        ax.set_ylabel("z")
        ax.set_title(f"11x11 - {metric}")
        ax.set_xticks(range(-5, 6))
        ax.set_yticks(range(-5, 6))
        if is_flag:
            for (row, col), name in labels.items():
                ax.text(col - 5, row - 5, name, ha="center", va="center",
                        fontsize=7, color="black")

        highlight = Rectangle((-0.5, -0.5), 1, 1, fill=False, zorder=5,
                              edgecolor=self.HIGHLIGHT_COLOR, lw=2.5)
        highlight.set_visible(False)
        ax.add_patch(highlight)

        canvas = FigureCanvasTkAgg(fig, master=left)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, left).update()
        self._heatmap_canvas, self._heatmap_ax = canvas, ax

        def _cell_at(event) -> tuple[int, int] | None:
            if event.inaxes is not ax or event.xdata is None or event.ydata is None:
                return None
            x_r, z_r = int(round(event.xdata)), int(round(event.ydata))
            if not (-5 <= x_r <= 5 and -5 <= z_r <= 5):
                return None
            return x_r, z_r

        def _on_motion(event):
            cell = _cell_at(event)
            if cell == self._hover_xz:
                return                      # same cell -- skip the redraw
            self._hover_xz = cell
            if cell is None:
                highlight.set_visible(False)
                self._set_hover_text(None)
            else:
                x_r, z_r = cell
                highlight.set_xy((x_r - 0.5, z_r - 0.5))
                highlight.set_visible(True)
                self._set_hover_text(cell)
            canvas.draw_idle()

        def _on_leave(_event):
            self._hover_xz = None
            highlight.set_visible(False)
            self._set_hover_text(None)
            canvas.draw_idle()

        def _on_click(event):
            cell = _cell_at(event)
            if cell is not None:
                self._open_cell_combined(*cell)

        canvas.mpl_connect("motion_notify_event", _on_motion)
        canvas.mpl_connect("axes_leave_event", _on_leave)
        canvas.mpl_connect("button_press_event", _on_click)
        self._set_hover_text(None)

    # ---------------- hover + click behaviour ----------------

    def _set_hover_text(self, cell: tuple[int, int] | None) -> None:
        if self.hover_text is None or not self.hover_text.winfo_exists():
            return
        if cell is None:
            body = "(no cell under cursor)"
        else:
            x, z = cell
            entry = self._cell_index.get((z + 5, 5 - x))
            if entry is None:
                body = (f"(x, z) = ({x:+d}, {z:+d})\n\n"
                        "no cached result for this cell.\n"
                        "run 'Process all (batch)' first.")
            else:
                body = hover_report(entry["meta"], entry["examine"])
        self.hover_text.configure(state=tk.NORMAL)
        self.hover_text.delete("1.0", tk.END)
        self.hover_text.insert(tk.END, body)
        self.hover_text.configure(state=tk.DISABLED)

    def _open_cell_combined(self, x: int, z: int) -> None:
        """Click handler: sync the main window to this cell, then open the
        combined pre-edge + normalized plot window."""
        entry = self._cell_index.get((z + 5, 5 - x))
        if entry is None:
            self.status.set(f"({x},{z}) has no cached result")
            return

        # Keep the main window's listboxes and info panel in step. Best effort:
        # it needs a dataset root, which the heatmap itself does not.
        self._select_cell_by_xz(x, z)

        sec = self.current_section
        if sec is None or (sec.x, sec.z) != (x, z):
            # No root loaded (or the file is missing there) -- the cache alone
            # is enough to plot, so rebuild the Section from the cached meta.
            m = entry["meta"]
            self.current_section = pl.Section(
                root=self.dataset_root or pl.DATA_ROOT,
                zdir=m["zdir"], fname=m["fname"],
                i=m["i"], j=m["j"], z=m["z"], x=m["x"],
                seg_start=m["seg_start"], seg_end=m["seg_end"],
            )
        self.show_combined()

    # ---------------- combined plot window, with info beside it ----------

    def _open_plot(self, kind: str):
        """Same singleton plot windows as main.py, except that the combined
        window carries the cell's absorption info next to the figure.
        Pre-edge / normalized windows are untouched."""
        if kind != "combined":
            return super()._open_plot(kind)

        sec = self.current_section
        if sec is None:
            return
        bundle = pl.cache_bundle(sec)
        if bundle is None:
            messagebox.showerror("Cache missing",
                                 "Cache not found. Click Reprocess.")
            return
        fig = pl.plot_combined_fig(bundle, f"{sec.stem} — Ni K-edge")

        win = self.plot_windows.get(kind)
        fresh = win is None or not win.winfo_exists()
        if fresh:
            win = tk.Toplevel(self.root)
            self.plot_windows[kind] = win
        else:
            for child in win.winfo_children():
                child.destroy()
        win.title(f"Combined — {sec.zdir}/{sec.stem}")
        if fresh:
            win.geometry("1680x620")      # only on creation; keep user resizes

        pane = ttk.PanedWindow(win, orient=tk.HORIZONTAL)
        pane.pack(fill=tk.BOTH, expand=True)
        left = ttk.Frame(pane)
        right = ttk.LabelFrame(pane, text="X-ray absorption info", padding=6)
        pane.add(left, weight=4)
        pane.add(right, weight=1)

        canvas = FigureCanvasTkAgg(fig, master=left)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, left).update()

        scroll = ttk.Scrollbar(right, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        info = tk.Text(right, wrap=tk.NONE, width=46, font=REPORT_FONT,
                       tabs=(REPORT_TAB,), yscrollcommand=scroll.set)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.configure(command=info.yview)

        meta = pl.load_meta(sec)
        body = (hover_report(meta, self._load_examine_for_current())
                if meta is not None
                else f"{sec.zdir}/{sec.fname}\n\nno cached metrics "
                     f"(.json missing) — click Reprocess")
        info.insert(tk.END, body)
        info.configure(state=tk.DISABLED)
        self.combined_info_text = info

        win.lift()


def main() -> int:
    """GUI entry point. Headless flags behave exactly as in main.py, so they
    are delegated there rather than duplicated."""
    argv = sys.argv[1:]
    headless = any(a.split("=")[0] in ("--batch", "--examine", "-h", "--help")
                   for a in argv)
    if headless:
        return base.main()

    root = tk.Tk()
    HoverHeatmapViewer(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

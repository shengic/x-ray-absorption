"""
NiXZ-121 XANES viewer — tkinter GUI.

Flow:
  1. On launch, prompt for dataset root (folder containing Z*/X*_XANES.txt).
  2. Left panel lists Z folders; click one to list its X sections in the middle panel.
  3. Single-click a section → runs pipeline (cached) and shows quality metrics.
  4. Double-click a section → also opens Pre-edge + Normalized plot windows.
  5. Plot windows are singletons per kind (preedge/norm/combined); reused in place.

Cache:
  data/{Zdir}/{stem}.npz + {stem}.json      -- arrays + metrics
  image/{Zdir}/{stem}_preedge.png + _norm.png

Batch mode (no GUI):
    python main.py --batch image_AI_Ni

version 1.0 by Albert Sheng
"""

from __future__ import annotations

import argparse
import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np

try:
    from matplotlib.backends.backend_tkagg import (
        FigureCanvasTkAgg,
        NavigationToolbar2Tk,
    )
    from matplotlib.figure import Figure
except ImportError:
    sys.exit("matplotlib required. Install: pip install matplotlib xraylarch")

try:
    import pipeline as pl
except Exception as e:
    sys.exit(f"failed to import pipeline: {e}")


class XANESViewer:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("NiXZ-121 XANES Viewer")
        root.geometry("1080x640")

        self.dataset_root: Path | None = None
        self.current_section: pl.Section | None = None
        self.plot_windows: dict[str, tk.Toplevel] = {}
        self.heatmap_window: tk.Toplevel | None = None

        self._build_ui()
        root.after(200, self.pick_root)

    def _build_ui(self):
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure(
            "Blue.Horizontal.TProgressbar",
            troughcolor="#e5eef7",
            background="#5faaf0",
            bordercolor="#7fb0e0",
            lightcolor="#7fb0e0",
            darkcolor="#5faaf0",
            thickness=14,
        )

        top = ttk.Frame(self.root, padding=6)
        top.pack(fill=tk.X)
        ttk.Button(top, text="Choose root...", command=self.pick_root).pack(side=tk.LEFT)
        self.root_label = ttk.Label(top, text="(no root selected)", foreground="gray")
        self.root_label.pack(side=tk.LEFT, padx=8)
        ttk.Button(top, text="11×11 heatmap",
                   command=self.show_heatmap).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Process all (batch)",
                   command=self.process_all).pack(side=tk.RIGHT)

        main = ttk.Frame(self.root, padding=6)
        main.pack(fill=tk.BOTH, expand=True)

        f_z = ttk.LabelFrame(main, text="Z folders", padding=4)
        f_z.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        self.lb_z = tk.Listbox(f_z, width=12, exportselection=False,
                                font=("Consolas", 10))
        self.lb_z.pack(fill=tk.Y, expand=True)
        self.lb_z.bind("<<ListboxSelect>>", self.on_z_select)

        f_x = ttk.LabelFrame(main, text="X sections", padding=4)
        f_x.pack(side=tk.LEFT, fill=tk.Y, padx=4)
        self.lb_x = tk.Listbox(f_x, width=32, exportselection=False,
                                font=("Consolas", 10))
        self.lb_x.pack(fill=tk.Y, expand=True)
        self.lb_x.bind("<<ListboxSelect>>", self.on_x_select)
        self.lb_x.bind("<Double-Button-1>", self.on_x_double)

        f_i = ttk.LabelFrame(main, text="Section info", padding=8)
        f_i.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        self.info_text = tk.Text(f_i, wrap=tk.WORD, height=22, width=50,
                                  font=("Consolas", 10))
        self.info_text.pack(fill=tk.BOTH, expand=True)
        btns = ttk.Frame(f_i)
        btns.pack(fill=tk.X, pady=4)
        ttk.Button(btns, text="Pre-edge plot",
                   command=self.show_preedge).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Normalized plot",
                   command=self.show_norm).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Both plots (combined)",
                   command=self.show_combined).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Reprocess",
                   command=self.reprocess).pack(side=tk.LEFT, padx=2)

        self.status = tk.StringVar(value="Ready")
        bottom = ttk.Frame(self.root)
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        status_row = ttk.Frame(bottom)
        status_row.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(status_row, text="Exit",
                   command=self._on_exit).pack(side=tk.RIGHT, padx=6, pady=3)
        ttk.Label(status_row, textvariable=self.status, anchor=tk.W,
                   relief=tk.SUNKEN).pack(side=tk.LEFT, fill=tk.X, expand=True)

        prog_row = ttk.Frame(bottom, padding=(6, 3, 6, 0))
        prog_row.pack(fill=tk.X, side=tk.TOP)
        self.progress = ttk.Progressbar(
            prog_row,
            style="Blue.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL,
            mode="determinate",
        )
        self.progress.pack(fill=tk.X, expand=True)

        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)

    def _on_exit(self):
        self._close_plot_windows()
        self.root.destroy()

    def pick_root(self):
        default = "image_AI_Ni" if Path("image_AI_Ni").is_dir() else "."
        d = filedialog.askdirectory(
            title="Choose dataset root (contains Z*/X*_XANES.txt)",
            initialdir=default,
        )
        if not d:
            return
        self.dataset_root = Path(d)
        self.root_label.config(text=str(self.dataset_root), foreground="black")
        self._populate_z()

    def _populate_z(self):
        self.lb_z.delete(0, tk.END)
        self.lb_x.delete(0, tk.END)
        if not self.dataset_root:
            return
        z_dirs = pl.discover_z_dirs(self.dataset_root)
        for zd in z_dirs:
            self.lb_z.insert(tk.END, zd.name)
        self.status.set(f"{len(z_dirs)} Z folder(s) found")

    def on_z_select(self, _evt):
        sel = self.lb_z.curselection()
        if not sel:
            return
        zname = self.lb_z.get(sel[0])
        self.lb_x.delete(0, tk.END)
        txts = pl.discover_x_files(self.dataset_root / zname)
        for t in txts:
            self.lb_x.insert(tk.END, t.name)
        self.status.set(f"{zname}: {len(txts)} X section(s)")

    def on_x_select(self, _evt):
        z_sel = self.lb_z.curselection()
        x_sel = self.lb_x.curselection()
        if not z_sel or not x_sel:
            return
        zname = self.lb_z.get(z_sel[0])
        xname = self.lb_x.get(x_sel[0])
        sec = pl.parse_section(self.dataset_root / zname / xname, self.dataset_root)
        if sec is None:
            messagebox.showerror("Parse error", f"Cannot parse: {xname}")
            return
        self.current_section = sec
        self.status.set(f"Processing {sec.zdir}/{sec.stem}...")
        self.root.update_idletasks()
        try:
            meta = pl.process_section(sec)
        except Exception as e:
            self.status.set("Error")
            messagebox.showerror("Processing error", f"{sec.stem}\n\n{e}")
            return
        self._update_info(meta)
        self.status.set(
            f"Loaded {sec.zdir}/{sec.stem}  (double-click to open plots)"
        )

    def on_x_double(self, _evt):
        if not self.current_section:
            return
        self.show_preedge()
        self.show_norm()

    def _update_info(self, m: dict):
        self.info_text.delete("1.0", tk.END)
        q4 = m.get("q4_e0_shift_vs_ref")
        q4_line = (f"Q4 E0 shift vs ref: {q4:+.2f} eV"
                   if q4 is not None else "Q4 E0 shift vs ref: n/a")
        lines = [
            f"Path:     {m['zdir']}/{m['fname']}",
            f"(i, j)  = ({m['i']}, {m['j']})",
            f"(x, z)  = ({m['x']}, {m['z']})",
            f"segment:  {m['seg_start']} – {m['seg_end']}",
            "",
            f"E0 (sample):    {m['e0']:.2f} eV",
            f"E0 (mu_ref):    {m.get('mu_ref_e0', float('nan')):.2f} eV",
            f"edge step Δμ₀:  {m['edge_step']:.4f}",
            "",
            "-- quality metrics --",
            f"Q1 edge step:       {m['q1_edge_step']:.4f}",
            f"Q2 hf noise (RMS):  {m['q2_hf_noise']:.5f}",
            f"Q3 pre-edge flat:   {m['q3_pre_flatness']:.5f}",
            q4_line,
            f"Q5 glitches:        {m['q5_glitches']}",
            f"Q6 white line:      {m['q6_white_line']:.3f}",
            "",
            f"usable: {'YES' if m['usable'] else 'NO '}  (preliminary threshold)",
        ]
        self.info_text.insert(tk.END, "\n".join(lines))

    def _close_plot_windows(self):
        for w in list(self.plot_windows.values()):
            try:
                w.destroy()
            except tk.TclError:
                pass
        self.plot_windows.clear()
        if self.heatmap_window is not None:
            try:
                self.heatmap_window.destroy()
            except tk.TclError:
                pass
            self.heatmap_window = None

    def show_preedge(self):
        if self.current_section:
            self._open_plot("preedge")

    def show_norm(self):
        if self.current_section:
            self._open_plot("norm")

    def show_combined(self):
        if self.current_section:
            self._open_plot("combined")

    def _open_plot(self, kind: str):
        sec = self.current_section
        bundle = pl.cache_bundle(sec)
        if bundle is None:
            messagebox.showerror("Cache missing",
                                 "Cache not found. Click Reprocess.")
            return
        title = f"{sec.stem} — Ni K-edge"
        if kind == "preedge":
            fig = pl.plot_preedge_fig(bundle, title)
            win_title = f"Pre-edge — {sec.zdir}/{sec.stem}"
        elif kind == "norm":
            fig = pl.plot_norm_fig(bundle, title)
            win_title = f"Normalized — {sec.zdir}/{sec.stem}"
        else:  # combined
            fig = pl.plot_combined_fig(bundle, title)
            win_title = f"Combined — {sec.zdir}/{sec.stem}"

        win = self.plot_windows.get(kind)
        if win is None or not win.winfo_exists():
            win = tk.Toplevel(self.root)
            self.plot_windows[kind] = win
        else:
            for child in win.winfo_children():
                child.destroy()
        win.title(win_title)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, win).update()
        win.lift()

    def reprocess(self):
        if not self.current_section:
            return
        try:
            meta = pl.process_section(self.current_section, force=True)
        except Exception as e:
            messagebox.showerror("Reprocess error", str(e))
            return
        self._update_info(meta)
        for kind in list(self.plot_windows.keys()):
            if self.plot_windows[kind].winfo_exists():
                self._open_plot(kind)

    def process_all(self):
        if not self.dataset_root:
            messagebox.showwarning("No root", "Choose a dataset root first.")
            return

        def _progress(done: int, total: int) -> None:
            self.progress["maximum"] = total
            self.progress["value"] = done

        self.progress["value"] = 0
        n_ok, n_err = run_batch(
            self.dataset_root,
            status_cb=self.status.set,
            progress_cb=_progress,
            tk_root=self.root,
        )
        self.progress["value"] = 0
        messagebox.showinfo(
            "Batch done",
            f"processed: {n_ok}\nerrors:    {n_err}\n"
            f"data  -> {pl.DATA_ROOT}\nimage -> {pl.IMAGE_ROOT}"
        )

    def show_heatmap(self):
        if not pl.DATA_ROOT.exists():
            messagebox.showinfo("No data", "Run 'Process all' first.")
            return
        grid = np.full((11, 11), np.nan)
        for jf in pl.DATA_ROOT.rglob("*.json"):
            try:
                m = json.loads(jf.read_text(encoding="utf-8"))
            except Exception:
                continue
            i, j = m.get("i"), m.get("j")
            if i is None or j is None:
                continue
            # +z up, +x right:  row=i (origin='lower'), col=10-j
            grid[i, 10 - j] = m.get("edge_step", np.nan)

        win = self.heatmap_window
        if win is None or not win.winfo_exists():
            win = tk.Toplevel(self.root)
            self.heatmap_window = win
        else:
            for child in win.winfo_children():
                child.destroy()
        win.title("11×11 heatmap — edge_step")
        fig = Figure(figsize=(6.2, 5.6), dpi=100)
        ax = fig.add_subplot(111)
        im = ax.imshow(grid, cmap="viridis", origin="lower",
                        extent=(-5.5, 5.5, -5.5, 5.5))
        ax.set_xlabel("x")
        ax.set_ylabel("z")
        ax.set_title("edge step Δμ₀")
        ax.set_xticks(range(-5, 6))
        ax.set_yticks(range(-5, 6))
        fig.colorbar(im, ax=ax)
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, win).update()
        win.lift()


def run_batch(root: Path, status_cb=None, progress_cb=None,
              tk_root=None) -> tuple[int, int]:
    txts = sorted(root.rglob("X*_XANES.txt"))
    total = len(txts)
    n_ok = n_err = 0
    for i, txt in enumerate(txts, 1):
        sec = pl.parse_section(txt, root)
        if sec is None:
            if progress_cb:
                progress_cb(i, total)
            continue
        msg = f"[{i}/{total}] {sec.zdir}/{sec.stem}"
        if status_cb:
            status_cb(msg)
        else:
            print(msg)
        try:
            pl.process_section(sec)
            n_ok += 1
        except Exception as e:
            n_err += 1
            print(f"[err] {sec.zdir}/{sec.stem}: {e}", file=sys.stderr)
        if progress_cb:
            progress_cb(i, total)
        if tk_root is not None:
            tk_root.update_idletasks()
    return n_ok, n_err


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--batch", metavar="ROOT", type=Path, default=None,
                    help="Run batch pipeline over ROOT and exit (no GUI)")
    args = ap.parse_args()
    if args.batch:
        if not args.batch.is_dir():
            sys.exit(f"root not found: {args.batch}")
        n_ok, n_err = run_batch(args.batch)
        print(f"\ndone: {n_ok} sections, {n_err} errors")
        return 0 if n_err == 0 else 1
    root = tk.Tk()
    XANESViewer(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

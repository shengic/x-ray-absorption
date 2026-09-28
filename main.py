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

version 1.6 by Albert Sheng
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
        self.config_window: tk.Toplevel | None = None
        self.rule_violations_window: tk.Toplevel | None = None
        self.edge_vars: dict[str, object] = {}
        self.config_save_var: tk.BooleanVar | None = None
        self.config: dict | None = None
        self.heatmap_metric = tk.StringVar(value="edge_step")
        self.rule_enabled_vars: dict[str, tk.BooleanVar] = {}
        self.rule_param_vars: dict[str, dict[str, tk.StringVar]] = {}

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
        ttk.Button(top, text="Rule violations",
                   command=self.show_rule_violations).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="11×11 heatmap",
                   command=self.show_heatmap).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Config...",
                   command=self.show_config_panel).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Examine 121",
                   command=self.run_examine_all).pack(side=tk.RIGHT, padx=4)
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
        report = pl.validate_root(self.dataset_root)
        z_dirs = pl.discover_z_dirs(self.dataset_root)
        for zd in z_dirs:
            self.lb_z.insert(tk.END, zd.name)
        incomplete = report.incomplete_z
        n_skipped = sum(len(v) for v in report.per_z_skipped.values())
        msg = (f"{len(z_dirs)} Z folder(s), {report.total_x}/"
               f"{pl.EXPECTED_Z_COUNT * pl.EXPECTED_X_PER_Z} X files")
        if incomplete:
            msg += f"  |  incomplete: {', '.join(incomplete)}"
        if n_skipped:
            msg += f"  |  {n_skipped} filename(s) skipped by regex"
        self.status.set(msg)

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
            f"usable (single-cell, legacy): {'YES' if m['usable'] else 'NO'}",
        ]
        ex = self._load_examine_for_current()
        if ex is not None:
            fail_hits = [rid for rid, r in ex.get("rules", {}).items()
                         if r.get("level_name") in ("WARN", "FAIL")]
            hint = f"  — {', '.join(fail_hits)}" if fail_hits else ""
            lines += [
                "",
                "-- examine (rule-based) --",
                f"smooth:     {ex['smooth']} "
                f"({ex.get('smooth_evaluated', 0)}/{ex.get('smooth_enabled', 0)}){hint}",
                f"consistent: {ex['consistent']} "
                f"({ex.get('consistent_evaluated', 0)}/{ex.get('consistent_enabled', 0)})",
                f"usable:     {'YES' if ex['usable'] else 'NO'}  (rule-based)",
            ]
        else:
            lines += ["", "examine: not run"]
        self.info_text.insert(tk.END, "\n".join(lines))

    def _load_examine_for_current(self) -> dict | None:
        if not self.current_section:
            return None
        sec = self.current_section
        p = pl.DATA_ROOT / sec.zdir / f"{sec.stem}.examine.json"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

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
        for attr in ("config_window", "rule_violations_window"):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.destroy()
                except tk.TclError:
                    pass
                setattr(self, attr, None)

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

    HEATMAP_CONTINUOUS = ("edge_step", "q1_edge_step", "q2_hf_noise",
                          "q3_pre_flatness", "q5_glitches", "q6_white_line")
    HEATMAP_FLAG = ("smooth", "consistent", "usable")
    FLAG_COLORS = {"PASS": "#4caf50", "WARN": "#ffc107",
                   "FAIL": "#f44336", "N/A": "#9e9e9e"}

    def show_heatmap(self):
        if not pl.DATA_ROOT.exists():
            messagebox.showinfo("No data", "Run 'Process all' first.")
            return
        win = self.heatmap_window
        if win is None or not win.winfo_exists():
            win = tk.Toplevel(self.root)
            self.heatmap_window = win
        else:
            for child in win.winfo_children():
                child.destroy()
        win.title("11×11 heatmap")

        bar = ttk.Frame(win, padding=4)
        bar.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(bar, text="Color by:").pack(side=tk.LEFT)
        options = list(self.HEATMAP_CONTINUOUS)
        if self._has_examine_results():
            options += list(self.HEATMAP_FLAG)
        cb = ttk.Combobox(bar, textvariable=self.heatmap_metric,
                          values=options, state="readonly", width=20)
        cb.pack(side=tk.LEFT, padx=6)
        if self.heatmap_metric.get() not in options:
            self.heatmap_metric.set(options[0])
        cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_heatmap())

        body = ttk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True)
        self._heatmap_body = body
        self._refresh_heatmap()
        win.lift()

    def _has_examine_results(self) -> bool:
        try:
            return any(pl.DATA_ROOT.rglob("*.examine.json"))
        except Exception:
            return False

    def _refresh_heatmap(self):
        for child in self._heatmap_body.winfo_children():
            child.destroy()
        metric = self.heatmap_metric.get()
        is_flag = metric in self.HEATMAP_FLAG

        grid = np.full((11, 11), np.nan)
        label_grid: dict[tuple[int, int], str] = {}
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
            row, col = i, 10 - j
            if is_flag:
                ex_path = pl.DATA_ROOT / m["zdir"] / f"{m['zdir'].replace('Z','')}_placeholder"
                ex_p = pl.DATA_ROOT / m["zdir"] / f"{jf.stem}.examine.json"
                if ex_p.exists():
                    try:
                        e = json.loads(ex_p.read_text(encoding="utf-8"))
                    except Exception:
                        continue
                    if metric == "usable":
                        grid[row, col] = 0.0 if e["usable"] else 2.0
                        label_grid[(row, col)] = "PASS" if e["usable"] else "FAIL"
                    else:
                        name = e.get(metric, "N/A")
                        grid[row, col] = {"PASS": 0.0, "WARN": 1.0,
                                          "FAIL": 2.0, "N/A": np.nan}.get(name, np.nan)
                        label_grid[(row, col)] = name
            else:
                grid[row, col] = m.get(metric, np.nan)

        fig = Figure(figsize=(6.4, 5.8), dpi=100)
        ax = fig.add_subplot(111)
        if is_flag:
            from matplotlib.colors import ListedColormap
            cmap = ListedColormap([self.FLAG_COLORS["PASS"],
                                   self.FLAG_COLORS["WARN"],
                                   self.FLAG_COLORS["FAIL"]])
            cmap.set_bad(self.FLAG_COLORS["N/A"])
            im = ax.imshow(grid, cmap=cmap, vmin=-0.5, vmax=2.5,
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
        ax.set_title(f"11×11 — {metric}")
        ax.set_xticks(range(-5, 6))
        ax.set_yticks(range(-5, 6))
        # Overlay flag text if flag mode
        if is_flag:
            for (row, col), name in label_grid.items():
                x_ = col - 5
                z_ = row - 5
                ax.text(x_, z_, name, ha="center", va="center",
                        fontsize=7, color="black")

        canvas = FigureCanvasTkAgg(fig, master=self._heatmap_body)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, self._heatmap_body).update()

        # Click-to-select
        def _on_click(event):
            if event.xdata is None or event.ydata is None:
                return
            x_r, z_r = int(round(event.xdata)), int(round(event.ydata))
            if not (-5 <= x_r <= 5 and -5 <= z_r <= 5):
                return
            self._select_cell_by_xz(x_r, z_r)
        canvas.mpl_connect("button_press_event", _on_click)

    def _select_cell_by_xz(self, x: int, z: int) -> None:
        i, j = z + 5, 5 - x
        zname = f"Z{i}_{z}"
        z_items = list(self.lb_z.get(0, tk.END))
        if zname not in z_items:
            self.status.set(f"({x},{z}) → {zname} not in list")
            return
        self.lb_z.selection_clear(0, tk.END)
        self.lb_z.selection_set(z_items.index(zname))
        self.on_z_select(None)
        x_items = list(self.lb_x.get(0, tk.END))
        prefix = f"X{j}_{x}_"
        match = [nm for nm in x_items
                 if nm.upper().startswith(prefix.upper())]
        if not match:
            self.status.set(f"({x},{z}) → no X{j}_{x} in {zname}")
            return
        self.lb_x.selection_clear(0, tk.END)
        self.lb_x.selection_set(x_items.index(match[0]))
        self.on_x_select(None)

    # ---------------- Examine (rule-based) ----------------

    def _ensure_config(self) -> dict | None:
        if self.config is not None:
            return self.config
        try:
            import yaml
        except ImportError:
            messagebox.showerror("PyYAML missing",
                                 "pip install pyyaml (needed for config.yaml)")
            return None
        cfg_path = Path("config.yaml")
        if not cfg_path.exists():
            messagebox.showerror("config.yaml missing",
                                 f"expected {cfg_path.resolve()}")
            return None
        self.config = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        return self.config

    def run_examine_all(self):
        if not self.dataset_root:
            messagebox.showwarning("No root", "Choose a dataset root first.")
            return
        cfg = self._ensure_config()
        if not cfg:
            return
        try:
            import examine
        except Exception as e:
            messagebox.showerror("examine import error", str(e))
            return
        self.status.set("Examining 121 cells...")
        self.root.update_idletasks()
        try:
            run = examine.run_examine(self.dataset_root, cfg)
        except Exception as e:
            self.status.set("Examine failed")
            messagebox.showerror("Examine error", str(e))
            return
        n_usable = sum(1 for v in run.verdicts.values() if v["usable"])
        self.status.set(
            f"Examine {run.run_id[:8]}: {n_usable}/{run.n_cells} usable"
        )
        if self.current_section:
            try:
                meta = pl.load_meta(self.current_section)
                if meta is not None:
                    self._update_info(meta)
            except Exception:
                pass
        if (self.heatmap_window is not None
                and self.heatmap_window.winfo_exists()):
            self.show_heatmap()

    def show_config_panel(self):
        """Unified config editor: Rules and Edge tabs, one Apply, one Save."""
        cfg = self._ensure_config()
        if not cfg:
            return
        if self.config_window is not None and self.config_window.winfo_exists():
            self.config_window.lift()
            return
        try:
            import rules as rl
        except Exception as e:
            messagebox.showerror("rules import error", str(e))
            return
        win = tk.Toplevel(self.root)
        self.config_window = win
        win.title("Config editor — config.yaml")
        win.geometry("640x560")

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 0))

        rules_tab = ttk.Frame(nb)
        nb.add(rules_tab, text="Rules")
        self._build_rules_tab(rules_tab, cfg, rl)

        edge_tab = ttk.Frame(nb)
        nb.add(edge_tab, text="Edge")
        self._build_edge_tab(edge_tab, cfg)

        self.config_save_var = tk.BooleanVar(value=False)
        footer = ttk.Frame(win, padding=6)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Checkbutton(footer, text="Save to config.yaml on Apply",
                        variable=self.config_save_var).pack(side=tk.LEFT)
        ttk.Button(footer, text="Close",
                   command=win.destroy).pack(side=tk.RIGHT, padx=4)
        ttk.Button(footer, text="Apply & Examine",
                   command=self._apply_config_and_examine).pack(side=tk.RIGHT, padx=4)

    def _link_label(self, parent, text, on_click):
        """A blue underlined label that runs `on_click()` when clicked.
        Cursor changes to 'hand2' on hover -- looks like a hyperlink."""
        from tkinter import font as tkfont
        lbl = ttk.Label(parent, text=text,
                        foreground="#0645ad", cursor="hand2")
        base = tkfont.nametofont("TkDefaultFont")
        linkfont = tkfont.Font(
            family=base.actual("family"),
            size=base.actual("size"),
            weight=base.actual("weight"),
            slant=base.actual("slant"),
            underline=True,
        )
        lbl.configure(font=linkfont)
        lbl.bind("<Button-1>", lambda _e: on_click())
        return lbl

    def _open_help_window(self, title: str, body: str):
        """Non-modal help panel with a Close button. Multiple can coexist;
        does not block the main window (no grab, no wait_window)."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("560x360")
        frame = ttk.Frame(win, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        text = tk.Text(frame, wrap="word",
                       font=("TkDefaultFont", 10), height=15,
                       padx=6, pady=4)
        scroll = ttk.Scrollbar(frame, orient="vertical",
                               command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        text.insert("1.0", body)
        text.configure(state="disabled")
        footer = ttk.Frame(win, padding=(8, 4))
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Button(footer, text="關閉 (Close)",
                   command=win.destroy).pack(side=tk.RIGHT)
        win.transient(self.root)

    def _show_rule_help(self, rid: str):
        import inspect
        try:
            import rules as rl
        except Exception as e:
            messagebox.showerror("rules import error", str(e))
            return
        r = rl.REGISTRY.get(rid)
        if r is None:
            self._open_help_window(f"說明 — {rid}", "（此規則未註冊）")
            return
        doc = inspect.getdoc(r.fn) or "（尚無描述）"
        req = ", ".join(r.requires) if r.requires else "（無）"
        body = (
            f"規則：     {rid}\n"
            f"旗標：     {r.flag}\n"
            f"作用範圍： {r.scope}\n"
            f"依賴規則： {req}\n"
            f"{'─' * 40}\n\n"
            f"{doc}"
        )
        self._open_help_window(f"說明 — {rid}", body)

    def _show_edge_help(self, key: str):
        msg = self.EDGE_HELP.get(key, "（尚無描述）")
        body = f"欄位：{key}\n{'─' * 40}\n\n{msg}"
        self._open_help_window(f"說明 — {key}", body)

    def _build_rules_tab(self, parent, cfg, rl):
        header = ttk.Frame(parent, padding=6)
        header.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(
            header,
            text="Enable/disable rules; edit z-score thresholds and other params.",
            wraplength=580, foreground="#444",
        ).pack(anchor=tk.W)
        body = ttk.Frame(parent, padding=6)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text="Rule（點名稱看說明）",
                  font=("TkDefaultFont", 9, "bold"),
                  width=24).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(body, text="On", font=("TkDefaultFont", 9, "bold")
                  ).grid(row=0, column=1)
        ttk.Label(body, text="Flag", font=("TkDefaultFont", 9, "bold")
                  ).grid(row=0, column=2, padx=4)
        ttk.Label(body, text="Params (editable)",
                  font=("TkDefaultFont", 9, "bold")
                  ).grid(row=0, column=3, sticky=tk.W, padx=4)

        rules_cfg = cfg.get("rules", {})
        self.rule_enabled_vars.clear()
        self.rule_param_vars.clear()
        for r_i, rid in enumerate(rl.REGISTRY.keys(), start=1):
            rc = rules_cfg.get(rid, {})
            enabled = bool(rc.get("enabled", False))
            var_en = tk.BooleanVar(value=enabled)
            self.rule_enabled_vars[rid] = var_en
            self._link_label(
                body, rid, lambda r=rid: self._show_rule_help(r)
            ).grid(row=r_i, column=0, sticky=tk.W)
            ttk.Checkbutton(body, variable=var_en).grid(row=r_i, column=1)
            ttk.Label(body, text=rl.REGISTRY[rid].flag,
                      foreground="#555").grid(row=r_i, column=2, padx=4)
            param_frame = ttk.Frame(body)
            param_frame.grid(row=r_i, column=3, sticky=tk.W)
            self.rule_param_vars[rid] = {}
            col = 0
            for pname, pval in rc.items():
                if pname == "enabled":
                    continue
                ttk.Label(param_frame, text=f"{pname}=").grid(row=0, column=col)
                col += 1
                sv = tk.StringVar(value=str(pval))
                ttk.Entry(param_frame, textvariable=sv, width=8
                          ).grid(row=0, column=col, padx=(0, 8))
                col += 1
                self.rule_param_vars[rid][pname] = sv

    def _build_edge_tab(self, parent, cfg):
        header = ttk.Frame(parent, padding=6)
        header.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(
            header,
            text=("Ni K-edge nominal energy + mu_ref calibration windows. "
                  "Affects CAL-EREF and every consistent rule."),
            wraplength=580, foreground="#444",
        ).pack(anchor=tk.W)
        body = ttk.Frame(parent, padding=6)
        body.pack(fill=tk.BOTH, expand=True)

        edge_cfg = cfg.setdefault("edge", {})
        self.edge_vars = {}
        for r, key in enumerate(self.EDGE_KEYS):
            val = edge_cfg.get(key)
            self._link_label(
                body, key, lambda k=key: self._show_edge_help(k)
            ).grid(row=r, column=0, sticky=tk.W, pady=2)
            if isinstance(val, list) and len(val) == 2:
                v1 = tk.StringVar(value=str(val[0]))
                v2 = tk.StringVar(value=str(val[1]))
                row_frame = ttk.Frame(body)
                row_frame.grid(row=r, column=1, sticky=tk.W)
                ttk.Label(row_frame, text="[").pack(side=tk.LEFT)
                ttk.Entry(row_frame, textvariable=v1, width=10).pack(side=tk.LEFT)
                ttk.Label(row_frame, text=" , ").pack(side=tk.LEFT)
                ttk.Entry(row_frame, textvariable=v2, width=10).pack(side=tk.LEFT)
                ttk.Label(row_frame, text="]").pack(side=tk.LEFT)
                self.edge_vars[key] = (v1, v2)
            else:
                v = tk.StringVar(value=str(val) if val is not None else "")
                ttk.Entry(body, textvariable=v, width=22).grid(
                    row=r, column=1, sticky=tk.W, padx=6)
                self.edge_vars[key] = v

    def _apply_config_and_examine(self):
        """Write both tabs' state into self.config, optionally save yaml,
        then run Examine exactly once."""
        if self.config is None:
            return
        for rid, var_en in self.rule_enabled_vars.items():
            self.config.setdefault("rules", {}).setdefault(rid, {})
            self.config["rules"][rid]["enabled"] = bool(var_en.get())
            for pname, sv in self.rule_param_vars.get(rid, {}).items():
                self.config["rules"][rid][pname] = _coerce(sv.get().strip())
        edge_cfg = self.config.setdefault("edge", {})
        for key, var in self.edge_vars.items():
            if isinstance(var, tuple):
                edge_cfg[key] = [_coerce(var[0].get().strip()),
                                 _coerce(var[1].get().strip())]
            else:
                edge_cfg[key] = _coerce(var.get().strip())
        if self.config_save_var and self.config_save_var.get():
            try:
                import yaml
                Path("config.yaml").write_text(
                    yaml.safe_dump(self.config, sort_keys=False,
                                    allow_unicode=True),
                    encoding="utf-8",
                )
                self.status.set("config.yaml saved")
            except Exception as e:
                messagebox.showerror("save config.yaml failed", str(e))
        self.run_examine_all()

    def _load_all_examine_verdicts(self) -> dict[tuple[int, int], dict]:
        verdicts: dict[tuple[int, int], dict] = {}
        if not pl.DATA_ROOT.exists():
            return verdicts
        for p in pl.DATA_ROOT.rglob("*.examine.json"):
            try:
                v = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            i, j = v.get("i"), v.get("j")
            if i is None or j is None:
                continue
            verdicts[(i, j)] = v
        return verdicts

    def show_rule_violations(self):
        verdicts = self._load_all_examine_verdicts()
        if not verdicts:
            messagebox.showinfo("No examine results",
                                 "Click 'Examine 121' first.")
            return
        sample = next(iter(verdicts.values()))
        rule_ids = list(sample.get("rules", {}).keys())
        if not rule_ids:
            messagebox.showinfo("No rules", "Examine results have no rules.")
            return

        win = self.rule_violations_window
        if win is None or not win.winfo_exists():
            win = tk.Toplevel(self.root)
            self.rule_violations_window = win
        else:
            for child in win.winfo_children():
                child.destroy()
        win.title("Rule violations — 11×11 per rule")

        # Summary header
        header = ttk.Frame(win, padding=(6, 4))
        header.pack(fill=tk.X, side=tk.TOP)
        n_cells = len(verdicts)
        n_usable = sum(1 for v in verdicts.values() if v.get("usable"))
        n_smooth_fail = sum(1 for v in verdicts.values()
                             if v.get("smooth") == "FAIL")
        n_consistent_fail = sum(1 for v in verdicts.values()
                                 if v.get("consistent") == "FAIL")
        ttk.Label(
            header,
            text=(f"{n_usable}/{n_cells} usable   |   "
                  f"smooth FAIL: {n_smooth_fail}   "
                  f"consistent FAIL: {n_consistent_fail}"),
            font=("TkDefaultFont", 9, "bold"),
        ).pack(anchor=tk.W)

        # Small-multiples grid
        from matplotlib.colors import ListedColormap
        cmap = ListedColormap([self.FLAG_COLORS["PASS"],
                                self.FLAG_COLORS["WARN"],
                                self.FLAG_COLORS["FAIL"]])
        cmap.set_bad(self.FLAG_COLORS["N/A"])
        ncols = 4
        nrows = (len(rule_ids) + ncols - 1) // ncols
        fig = Figure(figsize=(3.0 * ncols, 3.0 * nrows), dpi=95)

        for idx, rid in enumerate(rule_ids):
            ax = fig.add_subplot(nrows, ncols, idx + 1)
            grid = np.full((11, 11), np.nan)
            n_warn = n_fail = 0
            for (i, j), v in verdicts.items():
                r = v.get("rules", {}).get(rid, {})
                lvl = r.get("level")
                if lvl is None:
                    continue
                grid[i, 10 - j] = float(lvl)
                if lvl == 1:
                    n_warn += 1
                elif lvl == 2:
                    n_fail += 1
            ax.imshow(grid, cmap=cmap, vmin=-0.5, vmax=2.5,
                       origin="lower", extent=(-5.5, 5.5, -5.5, 5.5))
            ax.set_title(f"{rid}\nWARN={n_warn}  FAIL={n_fail}", fontsize=9)
            ax.set_xticks([-5, 0, 5])
            ax.set_yticks([-5, 0, 5])
            ax.tick_params(labelsize=7)

        fig.suptitle(
            "Rule violations — green=PASS, yellow=WARN, red=FAIL, grey=N/A",
            fontsize=9, y=0.995,
        )
        fig.tight_layout(rect=(0, 0, 1, 0.97))

        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, win).update()

        # Click-to-select on any subplot
        def _on_click(event):
            if event.xdata is None or event.ydata is None:
                return
            x_r = int(round(event.xdata))
            z_r = int(round(event.ydata))
            if not (-5 <= x_r <= 5 and -5 <= z_r <= 5):
                return
            self._select_cell_by_xz(x_r, z_r)
        canvas.mpl_connect("button_press_event", _on_click)
        win.lift()

    # ---------------- Edge / calibration panel ----------------

    EDGE_KEYS = (
        "element", "edge",
        "e0_nominal_eV", "e0_alt_eV", "e0_nominal_tol_eV",
        "mono_offset_window_eV", "ref_e0_search_eV", "ref_e0_spread_tol_eV",
    )

    EDGE_HELP = {
        "element":
            "吸收元素的化學符號（例：'Ni'）。用於參考查詢；目前無規則直接使用。",
        "edge":
            "吸收邊代號（K、L1、L2、L3）。Ni K 標稱值 = 8333 eV。留作追溯用。",
        "e0_nominal_eV":
            "參考標稱邊能（eV）。CAL-EREF 的 L1 檢查要求\n"
            "  mu_ref_e0 − e0_nominal_eV\n"
            "落在 mono_offset_window_eV 內。Ni K 預設 = 8333.0。",
        "e0_alt_eV":
            "來自光束線 Info.txt 的替代標稱值（本資料 = 8331.90）。\n"
            "列於此讓 8333 與 8331.90 之間 1.1 eV 的差距透明化；\n"
            "用 e0_nominal_tol_eV 涵蓋這段差距。",
        "e0_nominal_tol_eV":
            "L2 容差（eV）：|E0_ref_calibrated − e0_nominal_eV| 應小於此值。\n"
            "建議設 ≥ 1.5，以涵蓋 8333 與 8331.9 之間的差距。",
        "mono_offset_window_eV":
            "L1 窗 [low, high]（eV），套用於 mu_ref_e0 − e0_nominal_eV。\n"
            "預設寬 [-5, 25] 涵蓋此資料集約 +13 eV 的單色器刻度偏差。\n"
            "超窗 → CAL-EREF FAIL。",
        "ref_e0_search_eV":
            "find_e0 於 mu_ref 通道搜尋邊能的區間 [low, high]（eV）。\n"
            "應涵蓋真實參考 E₀，並避開已知的 pre-edge glitch。",
        "ref_e0_spread_tol_eV":
            "L3 容差（eV）：|mu_ref_e0[k] − median(mu_ref_e0)|。\n"
            "參考箔 E₀ 在 121 格應為常數，超過此值代表列間漂移。",
    }


def _coerce(raw: str):
    """Coerce an Entry string into int/float/bool/str for config params."""
    if raw.lower() in ("true", "false"):
        return raw.lower() == "true"
    try:
        v = int(raw)
        return v
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def run_batch(root: Path, status_cb=None, progress_cb=None,
              tk_root=None) -> tuple[int, int]:
    report = pl.validate_root(root)
    for line in report.as_lines():
        print(f"[validate] {line}", file=sys.stderr)
    txts = sorted(
        p for p in root.rglob("*_XANES.txt") if pl.FNAME_RE.match(p.name)
    )
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
                    help="Run pipeline batch over ROOT and exit (no GUI)")
    ap.add_argument("--examine", metavar="ROOT", type=Path, default=None,
                    help="Run rule-based examine over ROOT and exit (no GUI). "
                         "Combine with --batch to process then examine.")
    ap.add_argument("--config", type=Path, default=Path("config.yaml"),
                    help="Path to config.yaml (default: ./config.yaml)")
    args = ap.parse_args()

    ran_headless = False
    if args.batch:
        if not args.batch.is_dir():
            sys.exit(f"root not found: {args.batch}")
        n_ok, n_err = run_batch(args.batch)
        print(f"\nbatch done: {n_ok} sections, {n_err} errors")
        ran_headless = True
    if args.examine:
        if not args.examine.is_dir():
            sys.exit(f"root not found: {args.examine}")
        if not args.config.exists():
            sys.exit(f"config not found: {args.config}")
        import yaml
        import examine
        cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
        run = examine.run_examine(args.examine, cfg)
        n_usable = sum(1 for v in run.verdicts.values() if v["usable"])
        print(f"\nexamine done: run_id={run.run_id}  "
              f"cells={run.n_cells}  usable={n_usable}")
        ran_headless = True
    if ran_headless:
        return 0

    root = tk.Tk()
    XANESViewer(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

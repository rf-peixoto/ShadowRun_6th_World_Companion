"""Runs tab: the old standalone ``run_tracker.py``, merged in.

Behavior changes from the original tool:
- Runs are no longer tied to a character by file path (``character_file`` /
  ``character_name``) with "Load Character" / "Clear Character" buttons of
  their own. There's only ever one character loaded in the app now (via the
  footer's Save/Load/New Character buttons), so every run just belongs to
  whichever character is currently open, and completing a run always credits
  that character directly. Runs travel with the character's own .sr6 save
  file instead of a separate JSON export.
- "Import Runs" / "Export Runs" are kept as a way to share a run/mission
  template between characters or with your GM, but now import *adds* runs to
  the current character instead of requiring a whole separate run list.
"""

import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import theme
from dialogs import RunDialog
from runs import ShadowrunRun


class RunsTabMixin:
    def setup_runs_tab(self):
        tab = self.tabs["Runs"]
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=2)
        tab.rowconfigure(1, weight=1)

        header = ttk.Frame(tab)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        ttk.Button(header, text="New Run", command=self.new_run).pack(side=tk.LEFT, padx=2)
        ttk.Button(header, text="Import Runs", command=self.import_runs).pack(side=tk.LEFT, padx=2)
        ttk.Button(header, text="Export Runs", command=self.export_runs).pack(side=tk.LEFT, padx=2)

        left_frame = ttk.Frame(tab)
        left_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        ttk.Label(left_frame, text="Runs", font=("Arial", 12, "bold")).pack(anchor="w", padx=5, pady=(0, 5))

        cols = ("Name", "Status", "Reward")
        self.run_tree = ttk.Treeview(left_frame, columns=cols, show="headings", height=15)
        for c in cols:
            self.run_tree.heading(c, text=c)
            self.run_tree.column(c, anchor="w")
        self.run_tree.pack(fill=tk.BOTH, expand=True)
        self.run_tree.bind("<<TreeviewSelect>>", self._on_run_select)

        right_frame = ttk.Frame(tab)
        right_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.columnconfigure(0, weight=1)
        ttk.Label(right_frame, text="Run Details", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w", padx=5, pady=(0, 5))

        detail_frame = ttk.Frame(right_frame)
        detail_frame.grid(row=1, column=0, sticky="nsew")

        hdr = ttk.Frame(detail_frame)
        hdr.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(hdr, text="Name:").grid(row=0, column=0, sticky="w")
        self.run_detail_name = ttk.Label(hdr, text="", font=("Arial", 10, "bold"))
        self.run_detail_name.grid(row=0, column=1, sticky="w", padx=5)
        ttk.Label(hdr, text="Status:").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.run_detail_status = ttk.Label(hdr, text="", font=("Arial", 10, "bold"))
        self.run_detail_status.grid(row=1, column=1, sticky="w", padx=5, pady=(5, 0))

        prog = ttk.Frame(detail_frame)
        prog.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(prog, text="Progress:").pack(side=tk.LEFT)
        self.run_progress_var = tk.DoubleVar()
        ttk.Progressbar(prog, variable=self.run_progress_var, maximum=100, length=200).pack(side=tk.LEFT, padx=5)
        self.run_progress_lbl = ttk.Label(prog, text="0%")
        self.run_progress_lbl.pack(side=tk.LEFT)

        ttk.Label(detail_frame, text="Description:").pack(anchor="w", padx=5)
        self.run_detail_desc = tk.Text(detail_frame, width=60, height=5, wrap="word",
                                       bg=theme.ENTRY_BG, fg=theme.FG, insertbackground=theme.FG)
        self.run_detail_desc.pack(fill=tk.X, padx=5, pady=5)
        self.run_detail_desc.config(state="disabled")

        ttk.Label(detail_frame, text="Tasks:").pack(anchor="w", padx=5)
        tasks_container = ttk.Frame(detail_frame)
        tasks_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.run_tasks_canvas = tk.Canvas(tasks_container, bg=theme.BG, highlightthickness=0)
        self.run_tasks_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        run_tasks_scrollbar = ttk.Scrollbar(tasks_container, orient=tk.VERTICAL, command=self.run_tasks_canvas.yview)
        run_tasks_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.run_tasks_canvas.configure(yscrollcommand=run_tasks_scrollbar.set)
        self.run_tasks_inner = ttk.Frame(self.run_tasks_canvas)
        self.run_tasks_canvas.create_window((0, 0), window=self.run_tasks_inner, anchor="nw")
        self.run_tasks_inner.bind(
            "<Configure>", lambda e: self.run_tasks_canvas.configure(scrollregion=self.run_tasks_canvas.bbox("all"))
        )

        rc = ttk.Frame(detail_frame)
        rc.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(rc, text="Reward:").grid(row=0, column=0, sticky="w")
        self.run_detail_reward = ttk.Label(rc, text="0¥", font=("Arial", 10, "bold"))
        self.run_detail_reward.grid(row=0, column=1, sticky="w", padx=5)

        bottom_btns = ttk.Frame(right_frame)
        bottom_btns.grid(row=2, column=0, pady=10)
        self.run_edit_btn = ttk.Button(bottom_btns, text="Edit Run", command=self.edit_run, state="disabled", width=16)
        self.run_edit_btn.pack(side=tk.LEFT, padx=10)
        self.run_complete_btn = ttk.Button(bottom_btns, text="Complete Run", command=self.complete_run, state="disabled", width=16)
        self.run_complete_btn.pack(side=tk.LEFT, padx=10)
        self.run_abandon_btn = ttk.Button(bottom_btns, text="Abandon Run", command=self.abandon_run, state="disabled", width=16)
        self.run_abandon_btn.pack(side=tk.LEFT, padx=10)

        self.current_run = None
        self.run_task_vars = []

    # -- CRUD -------------------------------------------------------------

    def new_run(self):
        dialog = RunDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.run:
            self.character.runs.append(dialog.run)
            self.refresh_runs()
            self.on_character_changed()

    def edit_run(self):
        if not self.current_run:
            return
        dialog = RunDialog(self.root, self.current_run)
        self.root.wait_window(dialog)
        if dialog.run:
            self.refresh_runs()
            self._select_run(self.current_run)
            self.on_character_changed()

    def import_runs(self):
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            for rd in data:
                self.character.runs.append(ShadowrunRun.from_dict(rd))
            self.refresh_runs()
            self.on_character_changed()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import runs: {e}")

    def export_runs(self):
        if not self.character.runs:
            messagebox.showwarning("Warning", "No runs to export")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")])
        if not path:
            return
        try:
            with open(path, "w") as f:
                json.dump([r.to_dict() for r in self.character.runs], f, indent=2)
            messagebox.showinfo("Success", "Runs exported successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export runs: {e}")

    # -- Selection / display ------------------------------------------------

    def refresh_runs(self):
        for item in self.run_tree.get_children():
            self.run_tree.delete(item)
        for idx, run in enumerate(self.character.runs):
            self.run_tree.insert("", "end", iid=str(idx), values=(run.name, run.status, f"{run.reward}¥"))
        self.current_run = None
        self._clear_run_details()

    def _select_run(self, run):
        try:
            idx = self.character.runs.index(run)
        except ValueError:
            return
        self.run_tree.selection_set(str(idx))
        self._on_run_select()

    def _on_run_select(self, event=None):
        sel = self.run_tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self.current_run = self.character.runs[idx]
        self._update_run_details()

    def _update_run_details(self):
        run = self.current_run
        if not run:
            return
        self.run_detail_name.config(text=run.name)
        self.run_detail_status.config(text=run.status)
        self.run_detail_reward.config(text=f"{run.reward}¥")

        self.run_detail_desc.config(state="normal")
        self.run_detail_desc.delete("1.0", "end")
        self.run_detail_desc.insert("1.0", run.description)
        self.run_detail_desc.config(state="disabled")

        self._refresh_run_tasks()

        self.run_edit_btn.config(state="normal")
        self.run_abandon_btn.config(state="normal" if run.status == "Active" else "disabled")
        self._update_complete_button_state()

    def _clear_run_details(self):
        self.run_detail_name.config(text="")
        self.run_detail_status.config(text="")
        self.run_detail_desc.config(state="normal")
        self.run_detail_desc.delete("1.0", "end")
        self.run_detail_desc.config(state="disabled")
        for w in self.run_tasks_inner.winfo_children():
            w.destroy()
        self.run_edit_btn.config(state="disabled")
        self.run_abandon_btn.config(state="disabled")
        self.run_complete_btn.config(state="disabled")
        self.run_detail_reward.config(text="0¥")
        self.run_progress_var.set(0)
        self.run_progress_lbl.config(text="0%")

    def _refresh_run_tasks(self):
        for w in self.run_tasks_inner.winfo_children():
            w.destroy()
        self.run_task_vars = []
        run = self.current_run
        if not run or not run.tasks:
            self._update_run_progress()
            return
        for task in run.tasks:
            completed = task.get("completed", False)
            var = tk.BooleanVar(value=completed)
            txt = task["description"] + (" *" if task.get("mandatory") else "")
            cb = ttk.Checkbutton(self.run_tasks_inner, text=txt, variable=var, command=self._on_task_toggle)
            cb.pack(anchor="w", pady=2)
            if completed or run.status != "Active":
                cb.config(state="disabled")
            self.run_task_vars.append(var)
        self._update_run_progress()

    def _on_task_toggle(self):
        run = self.current_run
        if not run:
            return
        for i, var in enumerate(self.run_task_vars):
            run.tasks[i]["completed"] = var.get()
        self._update_run_progress()
        self._update_complete_button_state()
        self.on_character_changed()

    def _update_run_progress(self):
        run = self.current_run
        pct = run.progress_percent if run else 0
        self.run_progress_var.set(pct)
        self.run_progress_lbl.config(text=f"{pct}%")

    def _update_complete_button_state(self):
        run = self.current_run
        if not run or run.status != "Active":
            self.run_complete_btn.config(state="disabled")
            return
        self.run_complete_btn.config(state="normal" if run.mandatory_complete() else "disabled")

    # -- Actions ----------------------------------------------------------

    def complete_run(self):
        run = self.current_run
        if not run or run.status != "Active":
            return

        payout = run.payout()
        run.status = "Completed"
        self.character.nuyen += payout

        self.refresh_all()
        self._select_run(run)
        messagebox.showinfo("Run Completed", f"Completed! {payout}¥ awarded")

    def abandon_run(self):
        run = self.current_run
        if not run or run.status != "Active":
            return
        if not messagebox.askyesno("Confirm", "Are you sure you want to abandon this run?"):
            return
        run.status = "Abandoned"
        self.refresh_runs()
        self._select_run(run)
        self.on_character_changed()
        messagebox.showinfo("Run Abandoned", "Run has been abandoned")

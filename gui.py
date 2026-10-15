import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from auto_mode import AutoWatcher
from config import save_config
from excludes import add_excluded, remove_excluded
from memory import get_memory_stats
from processes import close_process, filter_processes, list_top_processes
from startup import list_startup_apps, set_startup_enabled
from trimmer import smart_trim


class App(ctk.CTk):
    def __init__(self, cfg: dict):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.cfg = cfg
        self.q: queue.Queue = queue.Queue()
        self._refreshing = False
        self._all_procs: list = []
        self.watcher = AutoWatcher(
            get_config=lambda: self.cfg,
            on_trim=lambda r: self.q.put(("auto_trim", r)))
        self.title("RAM Optimizer")
        self.geometry("760x700")
        self.minsize(640, 480)
        self.body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True)
        self._build_meter()
        self._build_processes()
        self._build_startup()
        self._build_excludes()
        self._build_clean()
        if self.cfg["auto_mode"]:
            self.watcher.start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)
        self._tick_meter()
        self.refresh_processes()
        self.refresh_startup()
        self.refresh_excludes()

    # ---- sections -------------------------------------------------
    def _section(self, title: str) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(self.body)
        frame.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 2))
        return frame

    def _build_meter(self) -> None:
        f = self._section("RAM")
        self.meter_bar = ctk.CTkProgressBar(f)
        self.meter_bar.pack(fill="x", padx=10, pady=4)
        self.meter_label = ctk.CTkLabel(f, text="...")
        self.meter_label.pack(anchor="w", padx=10, pady=(0, 8))

    def _build_processes(self) -> None:
        f = self._section("Processes")
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", fieldbackground="#2b2b2b",
                        foreground="white", rowheight=22, borderwidth=0)
        style.map("Treeview", background=[("selected", "#1f6aa5")])
        style.configure("Treeview.Heading", background="#3a3a3a",
                        foreground="white", relief="flat", borderwidth=0)
        style.map("Treeview.Heading", background=[("active", "#4a4a4a")])

        top = ctk.CTkFrame(f, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(0, 4))
        self.search_entry = ctk.CTkEntry(top, width=230,
                                         placeholder_text="Search by name or PID...")
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda e: self._render_procs())
        ctk.CTkLabel(top, text="Show").pack(side="left", padx=(12, 4))
        self.limit_menu = ctk.CTkOptionMenu(
            top, values=["15", "30", "50", "100", "All"], width=80,
            command=self._on_limit)
        limit = self.cfg["process_list_limit"]
        self.limit_menu.set("All" if limit == 0 else str(limit))
        self.limit_menu.pack(side="left")
        self.proc_count = ctk.CTkLabel(top, text="")
        self.proc_count.pack(side="left", padx=10)

        box = ctk.CTkFrame(f, fg_color="transparent")
        box.pack(fill="x", padx=10, pady=4)
        self.tree = ttk.Treeview(box, columns=("name", "pid", "mb"),
                                 show="headings", height=8)
        for col, text, w in (("name", "Name", 300), ("pid", "PID", 80), ("mb", "RAM (MB)", 100)):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=w, anchor="w")
        self.tree.tag_configure("protected", foreground="#777777")
        scrollbar = ctk.CTkScrollbar(box, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="x", expand=True)
        self.tree.bind("<MouseWheel>", self._on_tree_wheel)

        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkButton(row, text="Close process", command=self._close_selected).pack(side="left")
        ctk.CTkButton(row, text="Never trim", width=90, command=self._exclude_selected).pack(
            side="left", padx=8)
        ctk.CTkButton(row, text="Refresh", width=80, command=self.refresh_processes).pack(
            side="left")
        self.proc_status = ctk.CTkLabel(row, text="")
        self.proc_status.pack(side="left", padx=8)

    def _on_tree_wheel(self, event) -> str:
        """Scroll the table itself, not the whole window behind it."""
        self.tree.yview_scroll(-3 if event.delta > 0 else 3, "units")
        return "break"

    def _on_limit(self, choice: str) -> None:
        self.cfg["process_list_limit"] = 0 if choice == "All" else int(choice)
        save_config(self.cfg)
        self._render_procs()

    def _build_startup(self) -> None:
        f = self._section("Startup apps")
        self.startup_frame = ctk.CTkScrollableFrame(f, height=90)
        self.startup_frame.pack(fill="x", padx=10, pady=(0, 8))

    def _build_excludes(self) -> None:
        f = self._section("Never trim these apps")
        self.exclude_frame = ctk.CTkScrollableFrame(f, height=70)
        self.exclude_frame.pack(fill="x", padx=10, pady=(0, 8))

    def _build_clean(self) -> None:
        f = self._section("Smart clean and auto mode")
        row = ctk.CTkFrame(f, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=4)
        self.clean_btn = ctk.CTkButton(row, text="Smart clean now", command=self._clean_now)
        self.clean_btn.pack(side="left")
        self.clean_label = ctk.CTkLabel(row, text="")
        self.clean_label.pack(side="left", padx=10)
        self.auto_switch = ctk.CTkSwitch(f, text="Auto mode", command=self._toggle_auto)
        if self.cfg["auto_mode"]:
            self.auto_switch.select()
        self.auto_switch.pack(anchor="w", padx=10, pady=4)
        self.thr_label = ctk.CTkLabel(f, text="")
        self.thr_label.pack(anchor="w", padx=10)
        self.thr_slider = ctk.CTkSlider(f, from_=60, to=95, number_of_steps=35,
                                        command=self._on_threshold)
        self.thr_slider.set(self.cfg["trim_threshold_percent"])
        self.thr_slider.pack(fill="x", padx=10, pady=(0, 10))
        self.thr_slider.bind("<ButtonRelease-1>", lambda e: save_config(self.cfg), add=True)
        self._on_threshold(self.cfg["trim_threshold_percent"])

    # ---- actions --------------------------------------------------
    def _tick_meter(self) -> None:
        s = get_memory_stats()
        self.meter_bar.set(s["percent"] / 100)
        self.meter_label.configure(
            text=f"{s['used_gb']} / {s['total_gb']} GB used ({s['percent']}%)")
        self.after(2000, self._tick_meter)

    def refresh_processes(self) -> None:
        if self._refreshing:
            return
        self._refreshing = True
        threading.Thread(target=self._load_procs, daemon=True).start()

    def _load_procs(self) -> None:
        try:
            self.q.put(("procs", list_top_processes(limit=None)))
        except Exception as e:
            self.q.put(("procs_error", f"Process list failed: {e}"))

    def refresh_startup(self) -> None:
        for w in self.startup_frame.winfo_children():
            w.destroy()
        try:
            apps = list_startup_apps()
        except OSError as e:
            ctk.CTkLabel(self.startup_frame, text=str(e)).pack(anchor="w")
            return
        if not apps:
            ctk.CTkLabel(self.startup_frame, text="No startup apps found").pack(anchor="w")
        for app in apps:
            sw = ctk.CTkSwitch(self.startup_frame, text=app["name"])
            sw.configure(command=lambda s=sw, n=app["name"]: self._set_startup(s, n))
            if app["enabled"]:
                sw.select()
            sw.pack(anchor="w", pady=2)

    def _set_startup(self, switch: ctk.CTkSwitch, name: str) -> None:
        if not set_startup_enabled(name, bool(switch.get())):
            self.proc_status.configure(text=f"Could not change {name}")
            self.refresh_startup()

    def refresh_excludes(self) -> None:
        for w in self.exclude_frame.winfo_children():
            w.destroy()
        names = self.cfg["excluded_apps"]
        if not names:
            ctk.CTkLabel(self.exclude_frame,
                         text="None yet. Select a process above and press Never trim."
                         ).pack(anchor="w")
        for name in names:
            row = ctk.CTkFrame(self.exclude_frame, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=name).pack(side="left")
            ctk.CTkButton(row, text="Remove", width=70, height=22,
                          command=lambda n=name: self._remove_excluded(n)).pack(side="right")

    def _exclude_selected(self) -> None:
        sel = self.tree.selection()
        if sel:
            self._add_excluded(self.tree.item(sel[0], "values")[0])

    def _add_excluded(self, name: str) -> None:
        if add_excluded(self.cfg, name):
            save_config(self.cfg)
            self.refresh_excludes()
            self.proc_status.configure(text=f"{name} will never be trimmed")
        else:
            self.proc_status.configure(text="Already excluded (or empty name)")

    def _remove_excluded(self, name: str) -> None:
        if remove_excluded(self.cfg, name):
            save_config(self.cfg)
            self.refresh_excludes()

    def _close_selected(self) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        if "protected" in self.tree.item(sel[0], "tags"):
            self.proc_status.configure(text="Protected process, cannot close")
            return
        name = self.tree.item(sel[0], "values")[0]
        if not messagebox.askyesno("Close process", f"Close {name} (PID {pid})?\nUnsaved work in it may be lost."):
            return
        threading.Thread(target=lambda: self.q.put(("closed", close_process(pid))),
                         daemon=True).start()

    def _clean_now(self) -> None:
        self.clean_btn.configure(state="disabled")
        self.clean_label.configure(text="Cleaning...")

        def work():
            try:
                self.q.put(("clean", smart_trim(
                    self.cfg["min_process_mb_to_trim"],
                    excluded=list(self.cfg["excluded_apps"]))))
            except Exception as e:
                self.q.put(("error", f"Clean failed: {e}"))
        threading.Thread(target=work, daemon=True).start()

    def _toggle_auto(self) -> None:
        self.cfg["auto_mode"] = bool(self.auto_switch.get())
        save_config(self.cfg)
        (self.watcher.start if self.cfg["auto_mode"] else self.watcher.stop)()

    def _on_threshold(self, value) -> None:
        self.cfg["trim_threshold_percent"] = int(float(value))
        self.thr_label.configure(
            text=f"Trim when RAM use reaches {self.cfg['trim_threshold_percent']}%")

    # ---- thread results -------------------------------------------
    @staticmethod
    def _fmt(r: dict) -> str:
        mb = r["mb_freed"]
        freed = f"{mb / 1024:.1f} GB" if mb >= 1024 else f"{mb:.0f} MB"
        return (f"{r['processes_trimmed']} processes trimmed, about {freed} freed "
                f"({r['before_percent']}% -> {r['after_percent']}%)")

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "procs":
                    self._show_procs(data)
                elif kind == "procs_error":
                    self._refreshing = False
                    self.proc_status.configure(text=data)
                    self.after(5000, self.refresh_processes)
                elif kind == "clean":
                    self.clean_btn.configure(state="normal")
                    self.clean_label.configure(text=self._fmt(data))
                elif kind == "auto_trim":
                    self.clean_label.configure(text="Auto: " + self._fmt(data))
                elif kind == "closed":
                    self.proc_status.configure(text=data[1])
                    self.refresh_processes()
                elif kind == "error":
                    self.clean_btn.configure(state="normal")
                    self.proc_status.configure(text=data)
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    def _show_procs(self, rows: list) -> None:
        self._refreshing = False
        self._all_procs = rows
        self._render_procs()
        self.after(5000, self.refresh_processes)

    def _render_procs(self) -> None:
        """Apply the search text and the 'Show' limit to the last scan and redraw."""
        rows, total = filter_processes(
            self._all_procs, self.search_entry.get(), self.cfg["process_list_limit"])
        selected = self.tree.selection()
        scroll = self.tree.yview()[0]
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            tags = ("protected",) if r["protected"] else ()
            self.tree.insert("", "end", iid=str(r["pid"]), tags=tags,
                             values=(r["name"], r["pid"], r["memory_mb"]))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        self.tree.yview_moveto(scroll)
        self.proc_count.configure(text=f"Showing {len(rows)} of {total}")

    def _on_close(self) -> None:
        self.watcher.stop()
        save_config(self.cfg)
        self.destroy()

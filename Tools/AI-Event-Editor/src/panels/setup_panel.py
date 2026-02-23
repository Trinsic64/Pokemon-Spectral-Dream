"""Setup Panel: project folder selection, hg-engine toggle, API key."""

from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk


class SetupPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="Project Setup",
                             font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 20))

        # DSPRE Contents folder
        dspre_frame = ctk.CTkFrame(self)
        dspre_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(dspre_frame, text="DSPRE Contents Folder:",
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
        self.dspre_var = ctk.StringVar()
        ctk.CTkEntry(dspre_frame, textvariable=self.dspre_var,
                     width=500).pack(side="left", padx=5, expand=True, fill="x")
        ctk.CTkButton(dspre_frame, text="Browse", width=80,
                      command=self._browse_dspre).pack(side="left", padx=10)

        # hg-engine
        hg_frame = ctk.CTkFrame(self)
        hg_frame.pack(fill="x", padx=20, pady=5)
        self.hg_enabled = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(hg_frame, text="Using hg-engine",
                        variable=self.hg_enabled,
                        command=self._toggle_hg).pack(side="left", padx=10)
        self.hg_var = ctk.StringVar()
        self.hg_entry = ctk.CTkEntry(hg_frame, textvariable=self.hg_var,
                                     width=500)
        self.hg_entry.pack(side="left", padx=5, expand=True, fill="x")
        self.hg_browse_btn = ctk.CTkButton(hg_frame, text="Browse", width=80,
                                           command=self._browse_hg)
        self.hg_browse_btn.pack(side="left", padx=10)

        # API Key
        api_frame = ctk.CTkFrame(self)
        api_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(api_frame, text="AI API Key (optional):",
                     font=ctk.CTkFont(size=14)).pack(side="left", padx=10)
        self.api_var = ctk.StringVar()
        ctk.CTkEntry(api_frame, textvariable=self.api_var,
                     width=500, show="*").pack(side="left", padx=5,
                                               expand=True, fill="x")
        self.api_provider = ctk.StringVar(value="openai")
        ctk.CTkComboBox(api_frame, values=["anthropic", "openai"],
                        variable=self.api_provider,
                        width=120, state="readonly").pack(side="left", padx=10)

        # Load button
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        self.load_btn = ctk.CTkButton(btn_frame, text="Load Project",
                                      font=ctk.CTkFont(size=16, weight="bold"),
                                      width=200, height=45,
                                      command=self._load_project)
        self.load_btn.pack()

        # Progress
        self.progress = ctk.CTkProgressBar(self, width=600)
        self.progress.pack(pady=5)
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_label.pack(pady=2)

        # Status indicators
        self.status_frame = ctk.CTkFrame(self)
        self.status_frame.pack(fill="x", padx=20, pady=10)

        self.indicators: dict[str, ctk.CTkLabel] = {}
        sources = [
            "Headers", "Items", "Trainers", "Flags",
            "Sprites", "Text Archives", "Events", "Maps",
        ]
        for i, name in enumerate(sources):
            row, col = divmod(i, 4)
            lbl = ctk.CTkLabel(
                self.status_frame, text=f"  {name}: --",
                font=ctk.CTkFont(size=13),
                anchor="w",
            )
            lbl.grid(row=row, column=col, sticky="w", padx=15, pady=3)
            self.indicators[name] = lbl

    def _browse_dspre(self):
        path = filedialog.askdirectory(title="Select DSPRE Contents Folder")
        if path:
            self.dspre_var.set(path)
            # Auto-detect hg-engine
            p = Path(path)
            for parent in [p] + list(p.parents):
                hg = parent / "Tools" / "hg-engine"
                if hg.is_dir():
                    self.hg_var.set(str(hg))
                    break

    def _browse_hg(self):
        path = filedialog.askdirectory(title="Select hg-engine Directory")
        if path:
            self.hg_var.set(path)

    def _toggle_hg(self):
        enabled = self.hg_enabled.get()
        state = "normal" if enabled else "disabled"
        self.hg_entry.configure(state=state)
        self.hg_browse_btn.configure(state=state)

    def _load_project(self):
        dspre_path = self.dspre_var.get().strip()
        if not dspre_path:
            self.progress_label.configure(text="Please select DSPRE contents folder")
            return

        hg_path = None
        if self.hg_enabled.get():
            hg_str = self.hg_var.get().strip()
            if hg_str:
                hg_path = Path(hg_str)

        self.load_btn.configure(state="disabled")
        self.progress_label.configure(text="Loading...")

        def progress_cb(msg: str, pct: float):
            self.after(0, lambda: self._update_progress(msg, pct))

        def do_load():
            errors = self.app.project.load_all(
                Path(dspre_path), hg_path, progress_callback=progress_cb
            )
            self.after(0, lambda: self._on_load_complete(errors))

        thread = threading.Thread(target=do_load, daemon=True)
        thread.start()

    def _update_progress(self, msg: str, pct: float):
        self.progress.set(pct)
        self.progress_label.configure(text=msg)

    def _on_load_complete(self, errors: list[str]):
        self.load_btn.configure(state="normal")

        p = self.app.project
        status_map = {
            "Headers": len(p.headers.headers),
            "Items": len(p.items.items),
            "Trainers": len(p.trainers.trainers),
            "Flags": len(p.flags.flags),
            "Sprites": len(p.sprites.all_overlays),
            "Text Archives": len(p.text_archives.archives),
            "Events": len(p.events.overworlds),
            "Maps": len(p.maps_data),
        }

        for name, count in status_map.items():
            color = "#2ecc71" if count > 0 else "#e74c3c"
            symbol = "OK" if count > 0 else "FAIL"
            self.indicators[name].configure(
                text=f"  {name}: {count} [{symbol}]",
                text_color=color,
            )

        if errors:
            self.progress_label.configure(
                text=f"Loaded with {len(errors)} warning(s)",
                text_color="#f39c12",
            )
            for e in errors:
                print(f"[WARN] {e}")
        else:
            self.progress_label.configure(
                text="Project loaded successfully!",
                text_color="#2ecc71",
            )

        self.app.on_project_loaded()

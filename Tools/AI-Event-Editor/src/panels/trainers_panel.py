"""Trainer Editor Panel: class-based selection, sprite matching, placement."""

from __future__ import annotations

import random
import traceback

import customtkinter as ctk


MOVEMENT_TYPES = {
    "Stationary": 0,
    "Look Around": 2,
    "Random Walk (short)": 15,
    "Random Walk": 16,
    "Random Walk (wide)": 17,
    "Pace Horizontal": 6,
    "Pace Vertical": 7,
}


class TrainersPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._class_map: dict[str, str] = {}
        self._build()

    def _build(self):
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(self, text="Trainer Editor",
                             font=ctk.CTkFont(size=20, weight="bold"))
        title.grid(row=0, column=0, pady=(10, 5))

        self.target_label = ctk.CTkLabel(
            self, text="No headers selected. Go to Headers tab first.",
            font=ctk.CTkFont(size=13), text_color="#f39c12")
        self.target_label.grid(row=1, column=0, pady=5)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # === Left: trainer selection ===
        left = ctk.CTkFrame(main)
        left.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        ctk.CTkLabel(left, text="Mode",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        self.mode_var = ctk.StringVar(value="by_class")
        modes = ctk.CTkFrame(left, fg_color="transparent")
        modes.pack(fill="x", padx=10)
        ctk.CTkRadioButton(modes, text="By Trainer Class",
                           variable=self.mode_var, value="by_class",
                           command=self._on_mode_change).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(modes, text="Specific Trainer",
                           variable=self.mode_var, value="specific",
                           command=self._on_mode_change).pack(anchor="w", pady=2)

        # Container that swaps between class and specific
        self.mode_container = ctk.CTkFrame(left, fg_color="transparent")
        self.mode_container.pack(fill="both", expand=True, padx=10, pady=5)

        # --- Class selector ---
        self.class_frame = ctk.CTkFrame(self.mode_container)

        ctk.CTkLabel(self.class_frame, text="Trainer Class:").pack(
            anchor="w", padx=5, pady=(5, 0))
        self.class_var = ctk.StringVar(value="(load project first)")
        self.class_combo = ctk.CTkComboBox(
            self.class_frame, variable=self.class_var,
            values=["(load project first)"], width=300,
            command=self._on_class_change, state="readonly",
        )
        self.class_combo.pack(padx=5, pady=5, fill="x")

        ctk.CTkLabel(self.class_frame, text="Trainers per map:").pack(
            anchor="w", padx=5)
        self.trainer_qty = ctk.IntVar(value=1)
        qty_frame = ctk.CTkFrame(self.class_frame, fg_color="transparent")
        qty_frame.pack(fill="x", padx=5)
        ctk.CTkSlider(qty_frame, from_=1, to=4, number_of_steps=3,
                      variable=self.trainer_qty, width=150).pack(
            side="left", padx=5)
        self.tqty_label = ctk.CTkLabel(qty_frame, text="1")
        self.tqty_label.pack(side="left", padx=5)
        self.trainer_qty.trace_add("write",
                                   lambda *_: self.tqty_label.configure(
                                       text=str(self.trainer_qty.get())))

        self.randomize_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(self.class_frame, text="Randomize trainer selection",
                        variable=self.randomize_var).pack(anchor="w", padx=5, pady=5)

        self.class_info = ctk.CTkLabel(
            self.class_frame, text="", wraplength=350, justify="left",
            font=ctk.CTkFont(size=11))
        self.class_info.pack(padx=5, pady=3)

        # --- Specific trainer ---
        self.spec_frame = ctk.CTkFrame(self.mode_container)
        ctk.CTkLabel(self.spec_frame, text="Search Trainers:").pack(
            anchor="w", padx=5)
        self.trainer_search = ctk.StringVar()
        self.trainer_search.trace_add("write", lambda *_: self._filter_trainers())
        ctk.CTkEntry(self.spec_frame, textvariable=self.trainer_search,
                     width=300, placeholder_text="Type trainer name...").pack(padx=5, pady=5)
        self.trainer_listbox = ctk.CTkScrollableFrame(self.spec_frame, height=200)
        self.trainer_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.selected_trainer_id = ctk.IntVar(value=-1)

        # === Right: settings ===
        right = ctk.CTkFrame(main)
        right.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        ctk.CTkLabel(right, text="Settings",
                     font=ctk.CTkFont(size=15, weight="bold")).pack(pady=5)

        settings = ctk.CTkFrame(right, fg_color="transparent")
        settings.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(settings, text="Movement:").grid(
            row=0, column=0, sticky="w", padx=5, pady=5)
        self.movement_var = ctk.StringVar(value="Random Walk")
        ctk.CTkComboBox(settings, values=list(MOVEMENT_TYPES.keys()),
                        variable=self.movement_var, width=180,
                        state="readonly").grid(
            row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(settings, text="Sight Range:").grid(
            row=1, column=0, sticky="w", padx=5, pady=5)
        self.sight_var = ctk.IntVar(value=3)
        ctk.CTkSlider(settings, from_=0, to=8, number_of_steps=8,
                      variable=self.sight_var, width=150).grid(
            row=1, column=1, padx=5, pady=5)
        self.sight_label = ctk.CTkLabel(settings, text="3")
        self.sight_label.grid(row=1, column=2, padx=5)
        self.sight_var.trace_add("write",
                                 lambda *_: self.sight_label.configure(
                                     text=str(self.sight_var.get())))

        self.auto_sprite = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings, text="Auto-match sprite to class",
                        variable=self.auto_sprite).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        self.auto_place = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(settings, text="Auto-place (collision aware)",
                        variable=self.auto_place).grid(
            row=3, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        # Level filter
        level_frame = ctk.CTkFrame(right)
        level_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(level_frame, text="Level Filter:",
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=5)
        lf_inner = ctk.CTkFrame(level_frame, fg_color="transparent")
        lf_inner.pack(fill="x", padx=5, pady=3)
        ctk.CTkLabel(lf_inner, text="Min:").pack(side="left", padx=5)
        self.level_min = ctk.IntVar(value=1)
        ctk.CTkEntry(lf_inner, textvariable=self.level_min,
                     width=50).pack(side="left", padx=5)
        ctk.CTkLabel(lf_inner, text="Max:").pack(side="left", padx=5)
        self.level_max = ctk.IntVar(value=100)
        ctk.CTkEntry(lf_inner, textvariable=self.level_max,
                     width=50).pack(side="left", padx=5)

        # Info
        info = ctk.CTkFrame(right)
        info.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(info, text="Formula: script = 2999 + trainer#",
                     font=ctk.CTkFont(size=12),
                     text_color="#7f8c8d").pack(padx=5, pady=3)

        # Add button
        ctk.CTkButton(right, text="Add Trainers to Selected Maps",
                      font=ctk.CTkFont(size=14, weight="bold"),
                      height=40, fg_color="#2ecc71", hover_color="#27ae60",
                      command=self._add_trainers).pack(pady=15, padx=20, fill="x")

        # === Bottom: results ===
        self.result_text = ctk.CTkTextbox(self, height=120)
        self.result_text.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        self._on_mode_change()

    def _on_mode_change(self):
        for child in self.mode_container.winfo_children():
            child.pack_forget()

        if self.mode_var.get() == "by_class":
            self.class_frame.pack(fill="both", expand=True)
        else:
            self.spec_frame.pack(fill="both", expand=True)

    def on_headers_changed(self):
        selected = self.app.selected_headers
        if selected:
            names = []
            for h_num in selected[:5]:
                h = self.app.project.headers.headers.get(h_num)
                if h:
                    names.append(h.name)
            suffix = f" (+{len(selected)-5} more)" if len(selected) > 5 else ""
            self.target_label.configure(
                text=f"Target: {', '.join(names)}{suffix}",
                text_color="#2ecc71",
            )
        else:
            self.target_label.configure(
                text="No headers selected.",
                text_color="#f39c12",
            )

        classes = self.app.project.trainers.get_classes()
        if classes:
            display = [c.replace("TRAINERCLASS_", "").replace("_", " ").title()
                       for c in classes]
            self.class_combo.configure(values=display)
            self._class_map = dict(zip(display, classes))
            if display:
                self.class_var.set(display[0])

    def _on_class_change(self, display_name: str):
        real_class = self._class_map.get(display_name, "")
        if not real_class:
            return
        trainers = self.app.project.trainers.get_by_class(real_class)
        if trainers:
            lvls = [t.avg_level for t in trainers if t.num_mons > 0]
            if lvls:
                overlay = self.app.project.sprites.get_overlay_for_class(real_class)
                self.class_info.configure(
                    text=f"{len(trainers)} trainers | "
                         f"Levels: {min(lvls):.0f}-{max(lvls):.0f} | "
                         f"Sprite overlay: {overlay}")
            else:
                self.class_info.configure(text=f"{len(trainers)} trainers (no mons)")

    def _filter_trainers(self):
        for w in self.trainer_listbox.winfo_children():
            w.destroy()
        query = self.trainer_search.get().lower()
        if not query or len(query) < 2:
            return
        count = 0
        for tid, t in self.app.project.trainers.trainers.items():
            if query in t.name.lower() or query in t.trainer_class.lower():
                lo, hi = t.level_range
                btn = ctk.CTkButton(
                    self.trainer_listbox,
                    text=f"#{tid} {t.name} ({t.trainer_class.replace('TRAINERCLASS_', '')}) Lv{lo}-{hi}",
                    anchor="w", height=24,
                    fg_color="transparent", hover_color="#2c3e50",
                    text_color="#ecf0f1",
                    command=lambda i=tid: self.selected_trainer_id.set(i),
                )
                btn.pack(fill="x", pady=1)
                count += 1
                if count >= 50:
                    break

    def _add_trainers(self):
        selected = self.app.selected_headers
        if not selected:
            self.result_text.delete("0.0", "end")
            self.result_text.insert("0.0", "No headers selected!")
            return

        mode = self.mode_var.get()
        results: list[str] = []
        try:
            min_lv = self.level_min.get()
        except Exception:
            min_lv = 1
        try:
            max_lv = self.level_max.get()
        except Exception:
            max_lv = 100

        for h_num in selected:
            h = self.app.project.headers.headers.get(h_num)
            if not h:
                continue

            ef = str(h.event_file).zfill(4)
            existing_ows = self.app.project.get_overworlds_for_event(ef)
            next_ow_id = max((e.index for e in existing_ows), default=-1) + 1

            existing_pos = []
            for e in existing_ows:
                try:
                    existing_pos.append((
                        int(e.data.get("x_map", 0)),
                        int(e.data.get("y_map", 0))))
                except ValueError:
                    pass

            if mode == "by_class":
                display = self.class_var.get()
                real_class = self._class_map.get(display, "")
                pool = self.app.project.trainers.get_by_class(real_class)
                pool = [t for t in pool if t.num_mons > 0]
                if min_lv > 1 or max_lv < 100:
                    pool = [t for t in pool
                            if t.level_range[0] >= min_lv
                            and t.level_range[1] <= max_lv]
                qty = self.trainer_qty.get()
            else:
                tid = self.selected_trainer_id.get()
                t = self.app.project.trainers.trainers.get(tid)
                pool = [t] if t else []
                qty = 1

            if not pool:
                results.append(f"  {h.name}: No matching trainers found")
                continue

            positions = self.app.placement_engine.suggest_positions(
                h.matrix, existing_pos, count=qty)

            for i in range(qty):
                if self.randomize_var.get():
                    trainer = random.choice(pool)
                else:
                    trainer = pool[i % len(pool)]

                if self.auto_sprite.get():
                    overlay = self.app.project.sprites.get_overlay_for_class(
                        trainer.trainer_class)
                else:
                    overlay = 0

                movement = MOVEMENT_TYPES.get(self.movement_var.get(), 16)
                sight = self.sight_var.get()

                pos = positions[i] if i < len(positions) else None
                x_map = pos.x_map if pos else 10 + i * 4
                y_map = pos.y_map if pos else 10 + i * 4

                edit = {
                    "action": "add_overworld",
                    "event_file": ef,
                    "data": {
                        "ow_id": str(next_ow_id + i),
                        "overlay_entry": str(overlay),
                        "type": "TRAINER",
                        "movement": str(movement),
                        "flag": "0",
                        "script": str(trainer.script_number),
                        "orientation": str(random.choice([1, 2, 3, 4])),
                        "sight_range": str(sight),
                        "x_range": "0",
                        "y_range": "0",
                        "x_map": str(x_map),
                        "x_matrix": "0",
                        "y_map": str(y_map),
                        "y_matrix": "0",
                        "z": "0",
                    },
                    "comment": f"Trainer#{trainer.id} {trainer.name} "
                               f"({trainer.trainer_class})",
                }
                self.app.add_pending_edit(edit)
                lo, hi = trainer.level_range
                results.append(
                    f"  {h.name}: {trainer.name} ({trainer.trainer_class.replace('TRAINERCLASS_','')}) "
                    f"Lv{lo}-{hi} at ({x_map},{y_map})")

        self.result_text.delete("0.0", "end")
        self.result_text.insert("0.0",
                                f"Added {len(results)} trainer(s):\n"
                                + "\n".join(results))

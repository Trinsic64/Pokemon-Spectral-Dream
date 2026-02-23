"""Item Ball Editor Panel: category presets, specific items, placement."""

from __future__ import annotations

import random

import customtkinter as ctk

from ..data.items import ITEM_CATEGORIES


class ItemsPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        # === TOP SECTION ===
        title = ctk.CTkLabel(
            self, text="Item Ball Editor",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(pady=(10, 5))

        self.target_label = ctk.CTkLabel(
            self, text="No headers selected. Go to Headers tab first.",
            font=ctk.CTkFont(size=13), text_color="#f39c12"
        )
        self.target_label.pack(pady=5)

        # === TWO COLUMN LAYOUT ===
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        left = ctk.CTkFrame(main)
        left.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        right = ctk.CTkFrame(main)
        right.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        # === LEFT COLUMN ===
        ctk.CTkLabel(
            left, text="Mode",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=5)

        self.mode_var = ctk.StringVar(value="category")
        modes_frame = ctk.CTkFrame(left)
        modes_frame.pack(fill="x", padx=10)
        ctk.CTkRadioButton(
            modes_frame, text="Category Preset",
            variable=self.mode_var, value="category",
            command=self._on_mode_change
        ).pack(anchor="w", pady=2)
        ctk.CTkRadioButton(
            modes_frame, text="Specific Item",
            variable=self.mode_var, value="specific",
            command=self._on_mode_change
        ).pack(anchor="w", pady=2)

        self.mode_container = ctk.CTkFrame(left)
        self.mode_container.pack(fill="both", expand=True, padx=10, pady=5)

        # Category mode content
        self.cat_frame = ctk.CTkFrame(self.mode_container)
        ctk.CTkLabel(self.cat_frame, text="Category:").pack(anchor="w", padx=5, pady=(5, 2))

        categories = list(ITEM_CATEGORIES.keys()) + ["Mega Stones", "TMs"]
        self.cat_var = ctk.StringVar(value=categories[0] if categories else "")

        for i in range(0, len(categories), 3):
            row_frame = ctk.CTkFrame(self.cat_frame, fg_color="transparent")
            row_frame.pack(fill="x")
            for j in range(3):
                idx = i + j
                if idx < len(categories):
                    cat = categories[idx]
                    ctk.CTkRadioButton(
                        row_frame, text=cat, variable=self.cat_var, value=cat,
                        command=lambda c=cat: self._on_category_change(c),
                        font=ctk.CTkFont(size=12),
                    ).pack(side="left", padx=5, pady=2)

        self.cat_items_label = ctk.CTkLabel(
            self.cat_frame, text="", wraplength=350, justify="left",
            font=ctk.CTkFont(size=11)
        )
        self.cat_items_label.pack(padx=5, pady=5)

        # Specific mode content
        self.spec_frame = ctk.CTkFrame(self.mode_container)
        ctk.CTkLabel(self.spec_frame, text="Search Items:").pack(anchor="w", padx=5, pady=(5, 2))
        self.item_search_var = ctk.StringVar()
        self.item_search_var.trace_add("write", lambda *_: self._filter_items())
        ctk.CTkEntry(
            self.spec_frame, textvariable=self.item_search_var,
            width=300, placeholder_text="Type item name..."
        ).pack(padx=5, pady=5)
        self.item_listbox = ctk.CTkScrollableFrame(self.spec_frame, height=200)
        self.item_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.selected_item_var = ctk.StringVar()

        # === RIGHT COLUMN ===
        ctk.CTkLabel(
            right, text="Settings",
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(pady=5)

        settings = ctk.CTkFrame(right)
        settings.pack(fill="x", padx=10, pady=5)

        qty_row = ctk.CTkFrame(settings, fg_color="transparent")
        qty_row.pack(fill="x", pady=5)
        ctk.CTkLabel(qty_row, text="Items per map:").pack(side="left", padx=5)
        self.qty_var = ctk.IntVar(value=1)
        ctk.CTkSlider(
            qty_row, from_=1, to=5, number_of_steps=4,
            variable=self.qty_var, width=150,
            command=lambda v: self.qty_label.configure(text=str(int(v)))
        ).pack(side="left", padx=5)
        self.qty_label = ctk.CTkLabel(qty_row, text="1")
        self.qty_label.pack(side="left", padx=5)

        self.randomize_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            settings, text="Randomize from pool",
            variable=self.randomize_var
        ).pack(anchor="w", padx=5, pady=5)

        self.auto_flag_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            settings, text="Auto-allocate flags",
            variable=self.auto_flag_var
        ).pack(anchor="w", padx=5, pady=5)

        self.auto_place_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            settings, text="Auto-place (collision aware)",
            variable=self.auto_place_var
        ).pack(anchor="w", padx=5, pady=5)

        info_frame = ctk.CTkFrame(right)
        info_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(
            info_frame, text="Formula: script = 7000 + item_ID",
            font=ctk.CTkFont(size=12), text_color="#7f8c8d"
        ).pack(padx=5, pady=3)
        ctk.CTkLabel(
            info_frame, text="Sprite: overlay_entry = 87 (item ball)",
            font=ctk.CTkFont(size=12), text_color="#7f8c8d"
        ).pack(padx=5, pady=3)

        ctk.CTkButton(
            right, text="Add Item Balls to Selected Maps",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40, fg_color="#2ecc71", hover_color="#27ae60",
            command=self._add_items
        ).pack(pady=15, padx=20, fill="x")

        # === BOTTOM SECTION ===
        self.result_text = ctk.CTkTextbox(self, height=120)
        self.result_text.pack(fill="x", padx=10, pady=5)

        self._on_mode_change()

    def _on_mode_change(self):
        for child in self.mode_container.winfo_children():
            child.pack_forget()

        if self.mode_var.get() == "category":
            self.cat_frame.pack(fill="both", expand=True)
            self._on_category_change(self.cat_var.get())
        else:
            self.spec_frame.pack(fill="both", expand=True)
            self._filter_items()

    def _on_category_change(self, cat: str):
        try:
            if cat == "Mega Stones":
                items = self.app.project.items.get_mega_stones()
            elif cat == "TMs":
                items = self.app.project.items.get_tms()
            else:
                items = self.app.project.items.get_category(cat)
            names = [it.display_name for it in items[:15]]
            self.cat_items_label.configure(
                text=f"Pool ({len(items)} items): {', '.join(names)}"
                + ("..." if len(items) > 15 else "")
            )
        except Exception:
            self.cat_items_label.configure(text="Load a project to see items")

    def _filter_items(self):
        for w in self.item_listbox.winfo_children():
            w.destroy()
        query = self.item_search_var.get()
        if not query or len(query) < 2:
            return
        try:
            results = self.app.project.items.search(query)[:50]
        except Exception:
            return
        for it in results:
            btn = ctk.CTkButton(
                self.item_listbox,
                text=f"{it.display_name} (ID: {it.id}, script: {it.script_number})",
                anchor="w", height=28,
                fg_color="transparent", hover_color="#2c3e50",
                text_color="#ecf0f1",
                command=lambda i=it: self.selected_item_var.set(i.name),
            )
            btn.pack(fill="x", pady=1)

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
                text="No headers selected. Go to Headers tab first.",
                text_color="#f39c12",
            )

    def _add_items(self):
        selected = self.app.selected_headers
        if not selected:
            self.result_text.delete("0.0", "end")
            self.result_text.insert("0.0", "No headers selected!")
            return

        qty = self.qty_var.get()
        mode = self.mode_var.get()
        results: list[str] = []

        if mode == "category":
            cat = self.cat_var.get()
            if cat == "Mega Stones":
                pool = self.app.project.items.get_mega_stones()
            elif cat == "TMs":
                pool = self.app.project.items.get_tms()
            else:
                pool = self.app.project.items.get_category(cat)
        else:
            name = self.selected_item_var.get()
            item = self.app.project.items.get_by_name(name)
            pool = [item] if item else []

        if not pool:
            self.result_text.delete("0.0", "end")
            self.result_text.insert("0.0", "No items in pool!")
            return

        total_needed = len(selected) * qty
        if self.auto_flag_var.get():
            flags = self.app.project.flags.allocate(
                total_needed, description="Item ball (AI Editor)")
            if len(flags) < total_needed:
                self.result_text.delete("0.0", "end")
                self.result_text.insert(
                    "0.0",
                    f"Not enough flags! Need {total_needed}, have {len(flags)}")
                return
        else:
            flags = [0] * total_needed

        flag_idx = 0
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
            positions = self.app.placement_engine.suggest_positions(
                h.matrix, existing_pos, count=qty)

            for i in range(qty):
                item = random.choice(pool) if self.randomize_var.get() else pool[i % len(pool)]
                pos = positions[i] if i < len(positions) else None
                x_map = pos.x_map if pos else 10 + i * 3
                y_map = pos.y_map if pos else 10 + i * 3
                edit = {
                    "action": "add_overworld",
                    "event_file": ef,
                    "data": {
                        "ow_id": str(next_ow_id + i),
                        "overlay_entry": "87",
                        "type": "ITEM",
                        "movement": "0",
                        "flag": str(flags[flag_idx]),
                        "script": str(item.script_number),
                        "orientation": "1",
                        "sight_range": "0",
                        "x_range": "0", "y_range": "0",
                        "x_map": str(x_map), "x_matrix": "0",
                        "y_map": str(y_map), "y_matrix": "0",
                        "z": "0",
                    },
                    "comment": f"{item.display_name} (script={item.script_number})",
                }
                self.app.add_pending_edit(edit)
                results.append(
                    f"  {h.name}: {item.display_name} at ({x_map},{y_map}) flag={flags[flag_idx]}")
                flag_idx += 1

        self.result_text.delete("0.0", "end")
        self.result_text.insert("0.0", f"Added {len(results)} item ball(s):\n" + "\n".join(results))

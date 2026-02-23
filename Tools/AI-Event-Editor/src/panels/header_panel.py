"""Header Browser Panel: searchable/filterable header list with multi-select."""

from __future__ import annotations

import customtkinter as ctk


class HeaderPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._check_vars: dict[int, ctk.BooleanVar] = {}
        self._visible_rows: list[int] = []
        self._build()

    def _build(self):
        # Top bar: search + filters
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(top, text="Search:", font=ctk.CTkFont(size=13)).pack(
            side="left", padx=5)
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(top, textvariable=self.search_var, width=250).pack(
            side="left", padx=5)

        ctk.CTkLabel(top, text="Type:").pack(side="left", padx=(20, 5))
        self.type_filter = ctk.StringVar(value="All")
        self.type_entry = ctk.CTkEntry(
            top, textvariable=self.type_filter, width=140,
            placeholder_text="All")
        self.type_entry.pack(side="left", padx=5)
        self.type_filter.trace_add("write", lambda *_: self._apply_filter())
        self._type_buttons_frame = ctk.CTkFrame(top, fg_color="transparent")
        self._type_buttons_frame.pack(side="left", padx=2)

        # Select controls
        ctk.CTkButton(top, text="Select All Visible", width=130,
                      command=self._select_all).pack(side="right", padx=5)
        ctk.CTkButton(top, text="Deselect All", width=110,
                      command=self._deselect_all).pack(side="right", padx=5)
        ctk.CTkButton(top, text="Apply Selection", width=130,
                      fg_color="#2ecc71", hover_color="#27ae60",
                      command=self._apply_selection).pack(side="right", padx=5)

        self.sel_label = ctk.CTkLabel(top, text="0 selected",
                                      font=ctk.CTkFont(size=13, weight="bold"))
        self.sel_label.pack(side="right", padx=10)

        # Column headers
        col_header = ctk.CTkFrame(self, height=30)
        col_header.pack(fill="x", padx=10, pady=(5, 0))
        cols = [("", 40), ("H#", 50), ("Name", 250), ("Type", 100),
                ("Event File", 80), ("Text Archive", 90), ("Matrix", 60)]
        for text, w in cols:
            ctk.CTkLabel(col_header, text=text, width=w,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         anchor="w").pack(side="left", padx=2)

        # Scrollable list
        self.scroll_frame = ctk.CTkScrollableFrame(self, height=500)
        self.scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh(self):
        types = ["All"] + self.app.project.headers.get_types()
        for w in self._type_buttons_frame.winfo_children():
            w.destroy()
        for t in types[:8]:
            ctk.CTkButton(
                self._type_buttons_frame, text=t, width=70, height=24,
                font=ctk.CTkFont(size=11),
                fg_color="transparent" if t != "All" else "#1f6aa5",
                hover_color="#2c3e50",
                command=lambda v=t: self._set_type_filter(v),
            ).pack(side="left", padx=1)

        for w in self.scroll_frame.winfo_children():
            w.destroy()
        self._check_vars.clear()

        for h_num in sorted(self.app.project.headers.headers.keys()):
            h = self.app.project.headers.headers[h_num]
            var = ctk.BooleanVar(value=False)
            self._check_vars[h_num] = var

            row = ctk.CTkFrame(self.scroll_frame, height=28)
            row.pack(fill="x", pady=1)
            row._header_num = h_num

            ctk.CTkCheckBox(row, text="", variable=var, width=40,
                            command=self._update_count).pack(side="left")
            ctk.CTkLabel(row, text=str(h.number), width=50,
                         anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=h.name, width=250,
                         anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=h.map_type, width=100,
                         anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=str(h.event_file), width=80,
                         anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=str(h.text_archive), width=90,
                         anchor="w").pack(side="left", padx=2)
            ctk.CTkLabel(row, text=str(h.matrix), width=60,
                         anchor="w").pack(side="left", padx=2)

        self._apply_filter()

    def _apply_filter(self):
        query = self.search_var.get().lower()
        type_filter = self.type_filter.get()
        self._visible_rows.clear()

        for widget in self.scroll_frame.winfo_children():
            h_num = getattr(widget, "_header_num", None)
            if h_num is None:
                continue

            h = self.app.project.headers.headers.get(h_num)
            if not h:
                continue

            visible = True
            if query and query not in h.name.lower() and query not in str(h.number):
                visible = False
            if type_filter != "All" and h.map_type != type_filter:
                visible = False

            if visible:
                widget.pack(fill="x", pady=1)
                self._visible_rows.append(h_num)
            else:
                widget.pack_forget()

    def _select_all(self):
        for h_num in self._visible_rows:
            if h_num in self._check_vars:
                self._check_vars[h_num].set(True)
        self._update_count()

    def _deselect_all(self):
        for var in self._check_vars.values():
            var.set(False)
        self._update_count()

    def _update_count(self):
        count = sum(1 for v in self._check_vars.values() if v.get())
        self.sel_label.configure(text=f"{count} selected")

    def _apply_selection(self):
        selected = [h_num for h_num, var in self._check_vars.items() if var.get()]
        self.app.on_headers_selected(selected)
        self.app.set_status(f"{len(selected)} header(s) selected")

    def _set_type_filter(self, value: str):
        self.type_filter.set(value)
        for w in self._type_buttons_frame.winfo_children():
            if hasattr(w, 'cget') and w.cget("text") == value:
                w.configure(fg_color="#1f6aa5")
            else:
                w.configure(fg_color="transparent")

    def get_selected(self) -> list[int]:
        return [h_num for h_num, var in self._check_vars.items() if var.get()]

"""Keyboard path capture panel for NPC movement authoring."""

from __future__ import annotations

import customtkinter as ctk


class PathingPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._bound = False
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="Pathing Recorder", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(10, 6))
        ctk.CTkLabel(
            self,
            text="Click Start Recording then use arrow keys. Stop when done.",
            text_color="#bdc3c7",
        ).pack(pady=(0, 8))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(row, text="Speed").pack(side="left", padx=5)
        self.speed_var = ctk.StringVar(value="normal")
        ctk.CTkOptionMenu(
            row, values=["slow", "normal", "fast"], variable=self.speed_var, width=120,
            command=lambda v: self.app.path_capture.set_speed(v),
        ).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Start Recording", command=self._start).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Stop", command=self._stop).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Clear", fg_color="#e67e22", command=self._clear).pack(
            side="left", padx=5
        )

        self.path_text = ctk.CTkTextbox(self, height=430)
        self.path_text.pack(fill="both", expand=True, padx=10, pady=8)
        self._refresh()

    def _start(self) -> None:
        self.app.path_capture.set_speed(self.speed_var.get())
        if not self._bound:
            self.bind_all("<Up>", lambda _e: self._push("UP"))
            self.bind_all("<Down>", lambda _e: self._push("DOWN"))
            self.bind_all("<Left>", lambda _e: self._push("LEFT"))
            self.bind_all("<Right>", lambda _e: self._push("RIGHT"))
            self._bound = True
        self.path_text.insert("end", "\n[recording started]\n")

    def _stop(self) -> None:
        if self._bound:
            self.unbind_all("<Up>")
            self.unbind_all("<Down>")
            self.unbind_all("<Left>")
            self.unbind_all("<Right>")
            self._bound = False
        self.path_text.insert("end", "[recording stopped]\n")
        self._refresh()

    def _clear(self) -> None:
        self.app.path_capture.clear()
        self._refresh()

    def _push(self, direction: str) -> None:
        self.app.path_capture.push_direction(direction)
        self._refresh()

    def _refresh(self) -> None:
        self.path_text.delete("0.0", "end")
        if not self.app.path_capture.steps:
            self.path_text.insert("0.0", "No steps recorded.\n")
            return
        self.path_text.insert("end", "Steps:\n")
        for i, st in enumerate(self.app.path_capture.steps):
            self.path_text.insert(
                "end", f"{i:02d} | {st.direction:<5} | {st.frames_per_tile}f | {st.action_name}\n"
            )
        self.path_text.insert("end", "\nGenerated Action Lines:\n")
        for line in self.app.path_capture.to_action_lines():
            self.path_text.insert("end", f"{line}\n")


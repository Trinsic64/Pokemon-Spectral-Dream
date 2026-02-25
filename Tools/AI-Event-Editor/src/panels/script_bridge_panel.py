"""Preview deterministic bridge outputs for scripts/actions."""

from __future__ import annotations

import customtkinter as ctk


class ScriptBridgePanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="Script Bridge Preview", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(10, 6))
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(controls, text="Build From Sub-Events", command=self.refresh).pack(
            side="left", padx=4
        )
        ctk.CTkButton(
            controls, text="Copy to Clipboard", command=self._copy
        ).pack(side="left", padx=4)

        self.out_text = ctk.CTkTextbox(self, height=470)
        self.out_text.pack(fill="both", expand=True, padx=10, pady=8)

    def refresh(self) -> None:
        chain = getattr(self.app, "current_chain", None)
        self.out_text.delete("0.0", "end")
        if not chain:
            self.out_text.insert("0.0", "No sub-event chain yet.\n")
            return
        artifact = self.app.script_bridge.build(chain)
        self.app.latest_script_artifact = artifact
        self.out_text.insert("end", "=== Script Lines ===\n")
        for line in artifact.script_lines:
            self.out_text.insert("end", f"{line}\n")
        self.out_text.insert("end", "\n=== Movement Lines ===\n")
        for line in artifact.movement_lines:
            self.out_text.insert("end", f"{line}\n")

    def _copy(self) -> None:
        txt = self.out_text.get("0.0", "end").strip()
        if not txt:
            return
        self.clipboard_clear()
        self.clipboard_append(txt)


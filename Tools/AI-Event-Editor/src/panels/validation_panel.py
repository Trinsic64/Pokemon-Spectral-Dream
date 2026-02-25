"""Preflight compatibility validation panel."""

from __future__ import annotations

import customtkinter as ctk


class ValidationPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="Validation", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(10, 6))
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=5)
        ctk.CTkButton(row, text="Validate Sub-Event Chain", command=self._validate_chain).pack(
            side="left", padx=4
        )
        ctk.CTkButton(row, text="Validate Pending Edits", command=self._validate_edits).pack(
            side="left", padx=4
        )
        self.out_text = ctk.CTkTextbox(self, height=470)
        self.out_text.pack(fill="both", expand=True, padx=10, pady=8)

    def _render(self, title: str, report) -> None:
        self.out_text.delete("0.0", "end")
        self.out_text.insert("end", f"{title}\n")
        self.out_text.insert("end", "=" * len(title) + "\n\n")
        if report.ok:
            self.out_text.insert("end", "OK: no validation errors.\n")
        if report.warnings:
            self.out_text.insert("end", "Warnings:\n")
            for w in report.warnings:
                self.out_text.insert("end", f"  - {w}\n")
            self.out_text.insert("end", "\n")
        if report.errors:
            self.out_text.insert("end", "Errors:\n")
            for e in report.errors:
                self.out_text.insert("end", f"  - {e}\n")

    def _validate_chain(self) -> None:
        chain = getattr(self.app, "current_chain", None)
        if not chain:
            self.out_text.delete("0.0", "end")
            self.out_text.insert("0.0", "No chain available.\n")
            return
        rep = self.app.compat_validator.validate_chain(chain)
        self._render("Sub-Event Chain Validation", rep)

    def _validate_edits(self) -> None:
        rep = self.app.compat_validator.validate_pending_edits(self.app.pending_edits)
        self._render("Pending Edit Validation", rep)


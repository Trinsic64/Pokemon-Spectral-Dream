"""Reusable gift widgets for item and pokemon sub-events."""

from __future__ import annotations

import customtkinter as ctk


class ItemGiftWidget(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.item_var = ctk.StringVar(value="")
        self.qty_var = ctk.IntVar(value=1)
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Gift Item").pack(anchor="w", padx=6, pady=(4, 2))
        self.item_entry = ctk.CTkEntry(
            self, textvariable=self.item_var, placeholder_text="ITEM_POTION"
        )
        self.item_entry.pack(fill="x", padx=6, pady=2)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=(2, 6))
        ctk.CTkLabel(row, text="Qty").pack(side="left")
        ctk.CTkEntry(row, width=70, textvariable=self.qty_var).pack(side="left", padx=6)

    def to_params(self) -> dict[str, object]:
        item_name = self.item_var.get().strip().upper()
        item = self.app.project.items.get_by_name(item_name)
        return {
            "item_name": item_name,
            "item_id": item.id if item else 0,
            "quantity": max(1, int(self.qty_var.get() or 1)),
        }


class PokemonGiftWidget(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.species_var = ctk.StringVar(value="")
        self.level_var = ctk.IntVar(value=5)
        self.held_item_var = ctk.StringVar(value="ITEM_NONE")
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(self, text="Gift Pokemon").pack(anchor="w", padx=6, pady=(4, 2))
        self.species_entry = ctk.CTkEntry(
            self, textvariable=self.species_var, placeholder_text="SPECIES_BULBASAUR"
        )
        self.species_entry.pack(fill="x", padx=6, pady=2)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=2)
        ctk.CTkLabel(row, text="Level").pack(side="left")
        ctk.CTkEntry(row, width=70, textvariable=self.level_var).pack(side="left", padx=6)
        ctk.CTkLabel(row, text="Held Item").pack(side="left", padx=(6, 2))
        ctk.CTkEntry(row, width=160, textvariable=self.held_item_var).pack(side="left")

    def to_params(self) -> dict[str, object]:
        species_name = self.species_var.get().strip().upper()
        species = self.app.project.species.get_by_name(species_name)
        held_name = self.held_item_var.get().strip().upper()
        held = self.app.project.items.get_by_name(held_name)
        return {
            "species_name": species_name,
            "species_id": species.value if species else 0,
            "level": max(1, int(self.level_var.get() or 1)),
            "held_item_name": held_name,
            "held_item": held.id if held else 0,
        }


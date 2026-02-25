"""Composable sub-event chain editor."""

from __future__ import annotations

import customtkinter as ctk

from ..model.sub_events import SubEventChain
from .gift_widgets import ItemGiftWidget, PokemonGiftWidget


class SubEventsPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.chain = SubEventChain(name="npc_chain")
        self._build()

    def _build(self) -> None:
        ctk.CTkLabel(
            self, text="Sub-Events Builder", font=ctk.CTkFont(size=20, weight="bold")
        ).pack(pady=(10, 6))

        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(top, text="Dialogue Message ID").pack(side="left", padx=5)
        self.msg_var = ctk.IntVar(value=0)
        ctk.CTkEntry(top, width=90, textvariable=self.msg_var).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Add Dialogue", command=self._add_dialogue).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Add Path", command=self._add_path).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Add End", command=self._add_end).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Clear Chain", fg_color="#e67e22", command=self._clear).pack(
            side="right", padx=5
        )

        mid = ctk.CTkFrame(self)
        mid.pack(fill="x", padx=10, pady=5)
        self.item_widget = ItemGiftWidget(mid, self.app)
        self.item_widget.pack(side="left", fill="x", expand=True, padx=4)
        self.pokemon_widget = PokemonGiftWidget(mid, self.app)
        self.pokemon_widget.pack(side="left", fill="x", expand=True, padx=4)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=4)
        ctk.CTkButton(row, text="Add Item Gift", command=self._add_item).pack(side="left", padx=5)
        ctk.CTkButton(row, text="Add Pokemon Gift", command=self._add_pokemon).pack(side="left", padx=5)

        self.chain_text = ctk.CTkTextbox(self, height=330)
        self.chain_text.pack(fill="both", expand=True, padx=10, pady=8)
        self._refresh_chain_view()

    def _add_dialogue(self) -> None:
        self.chain.append("dialogue", message_id=int(self.msg_var.get() or 0))
        self._refresh_chain_view()

    def _add_path(self) -> None:
        lines = self.app.path_capture.to_action_lines()
        self.chain.append("movement_path", action_lines=lines)
        self._refresh_chain_view()

    def _add_item(self) -> None:
        self.chain.append("give_item", **self.item_widget.to_params())
        self._refresh_chain_view()

    def _add_pokemon(self) -> None:
        self.chain.append("give_pokemon", **self.pokemon_widget.to_params())
        self._refresh_chain_view()

    def _add_end(self) -> None:
        self.chain.append("end")
        self._refresh_chain_view()

    def _clear(self) -> None:
        self.chain.events.clear()
        self._refresh_chain_view()

    def _refresh_chain_view(self) -> None:
        self.chain_text.delete("0.0", "end")
        if not self.chain.events:
            self.chain_text.insert("0.0", "No sub-events yet.\n")
            return
        for idx, ev in enumerate(self.chain.events):
            self.chain_text.insert("end", f"{idx:02d} | {ev.kind} | {ev.params}\n")
        self.app.current_chain = self.chain


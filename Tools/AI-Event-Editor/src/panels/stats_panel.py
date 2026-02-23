"""Statistics Dashboard: global entity counts with subtype breakdowns."""

from __future__ import annotations

import customtkinter as ctk


class StatsPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="Global Event Statistics",
                             font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 5))

        ctk.CTkButton(self, text="Refresh", width=100,
                      command=self.refresh).pack(pady=5)

        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # Summary cards - two rows of three
        self.cards: dict[str, ctk.CTkLabel] = {}
        card_defs_row0 = [
            ("items_card", "Items"),
            ("trainers_card", "Trainers"),
            ("npcs_card", "NPCs"),
        ]
        card_defs_row1 = [
            ("warps_card", "Warps"),
            ("spawnables_card", "Spawnables"),
            ("flags_card", "Flags"),
        ]

        def make_card(parent, card_id, label):
            card = ctk.CTkFrame(parent)
            card.pack(side="left", fill="both", expand=True, padx=5, pady=5)

            ctk.CTkLabel(card, text=label,
                         font=ctk.CTkFont(size=15, weight="bold")).pack(
                pady=(8, 2))
            count_label = ctk.CTkLabel(
                card, text="--",
                font=ctk.CTkFont(size=28, weight="bold"),
                text_color="#3498db")
            count_label.pack(pady=2)
            self.cards[f"{card_id}_count"] = count_label

            detail_label = ctk.CTkLabel(
                card, text="", wraplength=300, justify="left",
                font=ctk.CTkFont(size=11),
                text_color="#bdc3c7")
            detail_label.pack(padx=10, pady=(2, 8))
            self.cards[f"{card_id}_detail"] = detail_label

        row0 = ctk.CTkFrame(main, fg_color="transparent")
        row0.pack(fill="x", padx=5, pady=5)
        for card_id, label in card_defs_row0:
            make_card(row0, card_id, label)

        row1 = ctk.CTkFrame(main, fg_color="transparent")
        row1.pack(fill="x", padx=5, pady=5)
        for card_id, label in card_defs_row1:
            make_card(row1, card_id, label)

        # Full breakdown
        self.breakdown_text = ctk.CTkTextbox(self, height=200)
        self.breakdown_text.pack(fill="both", expand=True, padx=10, pady=5)

    def refresh(self):
        if not self.app.project.loaded:
            return

        stats = self.app.stats_engine.compute(self.app.project)

        self.cards["items_card_count"].configure(text=str(stats.items.total))
        top_items = stats.items.by_subtype.most_common(8)
        self.cards["items_card_detail"].configure(
            text=", ".join(f"{n}: {c}" for n, c in top_items))

        self.cards["trainers_card_count"].configure(text=str(stats.trainers.total))
        top_trainers = stats.trainers.by_subtype.most_common(8)
        self.cards["trainers_card_detail"].configure(
            text=", ".join(f"{n}: {c}" for n, c in top_trainers))

        self.cards["npcs_card_count"].configure(text=str(stats.npcs.total))
        self.cards["npcs_card_detail"].configure(
            text=f"{len(stats.npcs.by_subtype)} unique sprites")

        self.cards["warps_card_count"].configure(text=str(stats.warps.total))
        self.cards["warps_card_detail"].configure(
            text=f"Across {len(stats.warps.per_event_file)} event files")

        self.cards["spawnables_card_count"].configure(
            text=str(stats.spawnables.total))
        self.cards["spawnables_card_detail"].configure(
            text=f"Across {len(stats.spawnables.per_event_file)} event files")

        flag_color = "#2ecc71" if stats.flags_available > 20 else (
            "#f39c12" if stats.flags_available > 5 else "#e74c3c")
        self.cards["flags_card_count"].configure(
            text=f"{stats.flags_used}/{stats.flags_total}",
            text_color=flag_color)
        self.cards["flags_card_detail"].configure(
            text=f"{stats.flags_available} available")

        # Full breakdown
        self.breakdown_text.delete("0.0", "end")
        lines = self.app.stats_engine.get_summary_lines()
        self.breakdown_text.insert("0.0", "\n".join(lines))

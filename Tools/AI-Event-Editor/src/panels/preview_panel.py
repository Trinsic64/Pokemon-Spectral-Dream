"""Map Preview Panel: collision grid canvas with entity overlay."""

from __future__ import annotations

import customtkinter as ctk
from tkinter import Canvas


TILE_SIZE = 18
COLORS = {
    "walkable": "#315a73",
    "blocked": "#202330",
    "item": "#f1c40f",
    "trainer": "#e74c3c",
    "npc": "#3498db",
    "warp": "#9b59b6",
    "spawnable": "#1abc9c",
    "pending": "#e67e22",
    "selected": "#2ecc71",
    "grid": "#34495e",
    "empty_bg": "#16213e",
}


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._current_header = None
        self._click_callback = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=5)

        self.map_label = ctk.CTkLabel(
            top, text="Select a header and click 'Apply Selection' to preview a map",
            font=ctk.CTkFont(size=16, weight="bold"))
        self.map_label.pack(side="left", padx=10)

        ctk.CTkButton(top, text="Refresh", width=80,
                      command=self._refresh).pack(side="right", padx=5)

        self.status_hint = ctk.CTkLabel(
            self,
            text="Select a header in the Headers tab, then click Apply Selection.",
            font=ctk.CTkFont(size=12),
            text_color="#f39c12",
        )
        self.status_hint.pack(fill="x", padx=12, pady=(0, 4))

        # Legend
        legend = ctk.CTkFrame(self, fg_color="transparent")
        legend.pack(fill="x", padx=10, pady=3)
        legend_items = [
            ("Walkable", COLORS["walkable"]),
            ("Blocked", COLORS["blocked"]),
            ("Item", COLORS["item"]),
            ("Trainer", COLORS["trainer"]),
            ("NPC", COLORS["npc"]),
            ("Warp", COLORS["warp"]),
            ("Pending", COLORS["pending"]),
        ]
        for text, color in legend_items:
            f = ctk.CTkFrame(legend, fg_color="transparent")
            f.pack(side="left", padx=8)
            swatch = ctk.CTkFrame(f, width=16, height=16,
                                  fg_color=color, corner_radius=3)
            swatch.pack(side="left", padx=2)
            swatch.pack_propagate(False)
            ctk.CTkLabel(f, text=text, font=ctk.CTkFont(size=11)).pack(side="left")

        # Canvas in a scrollable container
        canvas_container = ctk.CTkFrame(self)
        canvas_container.pack(fill="both", expand=True, padx=10, pady=5)

        canvas_size = 32 * TILE_SIZE + 2
        self.canvas = Canvas(
            canvas_container,
            width=canvas_size,
            height=canvas_size,
            bg=COLORS["empty_bg"],
            highlightthickness=0,
        )
        self.canvas.pack(padx=5, pady=5)
        self.canvas.bind("<Button-1>", self._on_click)

        # Draw empty state message
        self.canvas.create_text(
            canvas_size // 2, canvas_size // 2,
            text="No map loaded\n\nSelect headers in the Headers tab\nthen click 'Apply Selection'",
            fill="#7f8c8d", font=("Arial", 14), justify="center",
            tags="empty_msg")

        # Info bar
        info_bar = ctk.CTkFrame(self, fg_color="transparent")
        info_bar.pack(fill="x", padx=10, pady=3)

        self.info_label = ctk.CTkLabel(info_bar, text="",
                                       font=ctk.CTkFont(size=12))
        self.info_label.pack(side="left", padx=10)

        self.coord_label = ctk.CTkLabel(
            info_bar, text="Click a tile to select position",
            font=ctk.CTkFont(size=12), text_color="#7f8c8d")
        self.coord_label.pack(side="right", padx=10)

    def show_map(self, header):
        self._current_header = header
        self.status_hint.configure(text="", text_color="#7f8c8d")
        self.map_label.configure(
            text=f"Map: {header.name} (H{header.number}, EF {header.event_file})")
        self._refresh()

    def _refresh(self):
        if not self._current_header:
            self.status_hint.configure(
                text="No header selected. Go to Headers -> check maps -> Apply Selection.",
                text_color="#f39c12",
            )
            return
        try:
            self.canvas.delete("all")
            h = self._current_header

            grid = self.app.placement_engine.get_collision_grid(h.matrix)
            if not grid:
                for map_id in range(max(0, h.matrix - 5), h.matrix + 300):
                    if map_id in self.app.project.maps_data:
                        self.app.placement_engine.load_map(
                            map_id, self.app.project.maps_data[map_id])
                grid = self.app.placement_engine.get_collision_grid(h.matrix)

            if grid:
                for y in range(32):
                    for x in range(32):
                        val = grid[y][x]
                        walkable = val == 0x00 or val == 0x80
                        color = COLORS["walkable"] if walkable else COLORS["blocked"]
                        x1 = x * TILE_SIZE
                        y1 = y * TILE_SIZE
                        self.canvas.create_rectangle(
                            x1, y1, x1 + TILE_SIZE, y1 + TILE_SIZE,
                            fill=color, outline=COLORS["grid"], width=0.5)
            else:
                self.canvas.create_text(
                    16 * TILE_SIZE, 16 * TILE_SIZE,
                    text="Collision grid unavailable for this matrix.\n"
                         "You can still add entities; placement will fallback.",
                    fill="#f39c12", font=("Arial", 14), justify="center")

            # Draw existing entities
            ef = str(h.event_file).zfill(4)

            for e in self.app.project.get_overworlds_for_event(ef):
                try:
                    x = int(e.data.get("x_map", 0))
                    y = int(e.data.get("y_map", 0))
                    ow_type = e.data.get("type", "NORMAL")
                    color = {
                        "ITEM": COLORS["item"],
                        "TRAINER": COLORS["trainer"],
                    }.get(ow_type, COLORS["npc"])
                    self._draw_entity(x, y, color, "O")
                except ValueError:
                    pass

            for e in self.app.project.get_warps_for_event(ef):
                try:
                    x = int(e.data.get("x_map", e.data.get("x", 0)))
                    y = int(e.data.get("y_map", e.data.get("y", 0)))
                    self._draw_entity(x, y, COLORS["warp"], "W")
                except ValueError:
                    pass

            for e in self.app.project.get_spawnables_for_event(ef):
                try:
                    x = int(e.data.get("x_map", e.data.get("x", 0)))
                    y = int(e.data.get("y_map", e.data.get("y", 0)))
                    self._draw_entity(x, y, COLORS["spawnable"], "S")
                except ValueError:
                    pass

            # Draw pending edits for this event file
            for edit in self.app.pending_edits:
                if edit.get("event_file") == ef and edit.get("action") == "add_overworld":
                    data = edit.get("data", {})
                    try:
                        x = int(data.get("x_map", 0))
                        y = int(data.get("y_map", 0))
                        self._draw_entity(x, y, COLORS["pending"], "+")
                    except ValueError:
                        pass

            ow_count = len(self.app.project.get_overworlds_for_event(ef))
            warp_count = len(self.app.project.get_warps_for_event(ef))
            sp_count = len(self.app.project.get_spawnables_for_event(ef))
            pending = sum(1 for e in self.app.pending_edits if e.get("event_file") == ef)
            self.info_label.configure(
                text=f"Entities: {ow_count} OW, {warp_count} warps, "
                     f"{sp_count} spawnables"
                     + (f", {pending} pending" if pending else ""))
        except Exception as e:
            self.info_label.configure(text=f"Preview error: {e}")
            self.canvas.delete("all")
            self.canvas.create_text(
                16 * TILE_SIZE, 16 * TILE_SIZE,
                text=f"Preview failed:\n{e}",
                fill="#e74c3c", font=("Arial", 13), justify="center")

    def _draw_entity(self, x: int, y: int, color: str, label: str):
        if x < 0 or x >= 32 or y < 0 or y >= 32:
            return
        x1 = x * TILE_SIZE + 2
        y1 = y * TILE_SIZE + 2
        self.canvas.create_oval(
            x1, y1, x1 + TILE_SIZE - 4, y1 + TILE_SIZE - 4,
            fill=color, outline="white", width=1)
        self.canvas.create_text(
            x1 + TILE_SIZE // 2 - 2, y1 + TILE_SIZE // 2 - 2,
            text=label, fill="white", font=("Arial", 7, "bold"))

    def _on_click(self, event):
        x = event.x // TILE_SIZE
        y = event.y // TILE_SIZE
        if 0 <= x < 32 and 0 <= y < 32:
            self.coord_label.configure(
                text=f"Selected: x_map={x}, y_map={y}",
                text_color="#2ecc71",
            )
            if self._click_callback:
                self._click_callback(x, y)

    def set_click_callback(self, callback):
        self._click_callback = callback

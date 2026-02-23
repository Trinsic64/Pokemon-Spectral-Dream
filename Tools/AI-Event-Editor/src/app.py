"""Main application window with tabbed navigation."""

from __future__ import annotations

import sys
import traceback

import customtkinter as ctk

from .data.loader import ProjectData
from .engine.stats import StatsEngine
from .engine.backup import BackupManager
from .engine.placement import PlacementEngine

from .panels.setup_panel import SetupPanel
from .panels.header_panel import HeaderPanel
from .panels.items_panel import ItemsPanel
from .panels.trainers_panel import TrainersPanel
from .panels.npc_panel import NPCPanel
from .panels.preview_panel import PreviewPanel
from .panels.stats_panel import StatsPanel
from .panels.execute_panel import ExecutePanel


class App(ctk.CTk):
    """AI Event Editor main window."""

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("AI Event Editor")
        self.geometry("1280x800")
        self.minsize(1024, 700)

        self.project = ProjectData()
        self.stats_engine = StatsEngine()
        self.placement_engine = PlacementEngine()
        self.backup_manager: BackupManager | None = None

        self.selected_headers: list[int] = []
        self.pending_edits: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

        tab_setup = self.tabview.add("Setup")
        tab_headers = self.tabview.add("Headers")
        tab_items = self.tabview.add("Items")
        tab_trainers = self.tabview.add("Trainers")
        tab_npcs = self.tabview.add("NPCs")
        tab_preview = self.tabview.add("Map Preview")
        tab_stats = self.tabview.add("Statistics")
        tab_execute = self.tabview.add("Execute")

        self._panel_errors: list[str] = []

        self.setup_panel = self._safe_create_panel(SetupPanel, tab_setup, "Setup")
        self.header_panel = self._safe_create_panel(HeaderPanel, tab_headers, "Headers")
        self.items_panel = self._safe_create_panel(ItemsPanel, tab_items, "Items")
        self.trainers_panel = self._safe_create_panel(TrainersPanel, tab_trainers, "Trainers")
        self.npc_panel = self._safe_create_panel(NPCPanel, tab_npcs, "NPCs")
        self.preview_panel = self._safe_create_panel(PreviewPanel, tab_preview, "Map Preview")
        self.stats_panel = self._safe_create_panel(StatsPanel, tab_stats, "Statistics")
        self.execute_panel = self._safe_create_panel(ExecutePanel, tab_execute, "Execute")

        if self._panel_errors:
            print("=" * 60, file=sys.stderr)
            print("PANEL CREATION ERRORS:", file=sys.stderr)
            for err in self._panel_errors:
                print(err, file=sys.stderr)
            print("=" * 60, file=sys.stderr)

        # Status bar
        self.status_var = ctk.StringVar(value="No project loaded")
        status_bar = ctk.CTkLabel(self, textvariable=self.status_var,
                                  anchor="w", height=24)
        status_bar.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 4))

    def _safe_create_panel(self, panel_class, parent, name: str):
        """Create a panel with error handling so one broken panel doesn't kill the app."""
        try:
            panel = panel_class(parent, self)
            panel.pack(fill="both", expand=True, padx=4, pady=4)
            return panel
        except Exception as e:
            error_msg = f"[{name}] {traceback.format_exc()}"
            self._panel_errors.append(error_msg)
            print(f"ERROR creating {name} panel: {e}", file=sys.stderr)
            traceback.print_exc()
            fallback = ctk.CTkFrame(parent)
            fallback.pack(fill="both", expand=True, padx=4, pady=4)
            ctk.CTkLabel(
                fallback,
                text=f"Error loading {name} panel:\n{e}",
                font=ctk.CTkFont(size=14),
                text_color="#e74c3c",
                wraplength=600,
            ).pack(expand=True, pady=20)
            return fallback

    def set_status(self, text: str):
        self.status_var.set(text)
        self.update_idletasks()

    def on_project_loaded(self):
        """Called after project data is successfully loaded."""
        if self.project.analysis_path:
            events_dir = self.project.analysis_path / "events"
            if events_dir.is_dir():
                self.backup_manager = BackupManager(events_dir)

        for map_id, data in self.project.maps_data.items():
            self.placement_engine.load_map(map_id, data)

        if hasattr(self.header_panel, 'refresh'):
            try:
                self.header_panel.refresh()
            except Exception as e:
                print(f"Error refreshing header panel: {e}", file=sys.stderr)

        if hasattr(self.stats_panel, 'refresh'):
            try:
                self.stats_panel.refresh()
            except Exception as e:
                print(f"Error refreshing stats panel: {e}", file=sys.stderr)

        self.set_status(
            f"Project loaded: {len(self.project.headers.headers)} headers, "
            f"{len(self.project.trainers.trainers)} trainers, "
            f"{len(self.project.items.items)} items"
        )

    def on_headers_selected(self, header_numbers: list[int]):
        """Called when header selection changes."""
        self.selected_headers = header_numbers

        for panel_name in ['items_panel', 'trainers_panel', 'npc_panel']:
            panel = getattr(self, panel_name, None)
            if panel and hasattr(panel, 'on_headers_changed'):
                try:
                    panel.on_headers_changed()
                except Exception as e:
                    print(f"Error updating {panel_name}: {e}", file=sys.stderr)

        if header_numbers:
            h = self.project.headers.headers.get(header_numbers[0])
            if h and hasattr(self.preview_panel, 'show_map'):
                try:
                    self.preview_panel.show_map(h)
                except Exception as e:
                    print(f"Error showing map preview: {e}", file=sys.stderr)

    def add_pending_edit(self, edit: dict):
        self.pending_edits.append(edit)
        if hasattr(self.execute_panel, 'refresh'):
            self.execute_panel.refresh()
        self.set_status(f"{len(self.pending_edits)} pending edit(s)")

    def clear_pending_edits(self):
        self.pending_edits.clear()
        if hasattr(self.execute_panel, 'refresh'):
            self.execute_panel.refresh()

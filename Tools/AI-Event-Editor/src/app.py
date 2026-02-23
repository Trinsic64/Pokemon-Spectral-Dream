"""Main application window with manual tab navigation (no CTkTabview)."""

from __future__ import annotations

import sys
import traceback
import tkinter as tk

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

APP_VERSION = "2.5"


class App(ctk.CTk):
    """AI Event Editor main window."""

    def __init__(self):
        super().__init__()

        self.title(f"AI Event Editor v{APP_VERSION}")
        self.geometry("1280x800")
        self.minsize(1024, 700)

        self.project = ProjectData()
        self.stats_engine = StatsEngine()
        self.placement_engine = PlacementEngine()
        self.backup_manager: BackupManager | None = None

        self.selected_headers: list[int] = []
        self.pending_edits: list[dict] = []

        self._panel_errors: list[str] = []
        self._tabs: dict[str, ctk.CTkFrame] = {}
        self._tab_buttons: dict[str, ctk.CTkButton] = {}
        self._active_tab: str = ""

        self._suppress_phantom_windows()
        self._build_ui()
        self._install_window_diagnostics()

        print(f"[AI Event Editor v{APP_VERSION}] App initialized, "
              f"{len(self._panel_errors)} panel errors")

    def _install_window_diagnostics(self):
        self._last_win_state = None

        def on_configure(_event=None):
            try:
                state = self.state()
            except Exception:
                state = "unknown"

            if state != self._last_win_state:
                self._last_win_state = state
                try:
                    geo = self.winfo_geometry()
                except Exception:
                    geo = "unknown"
                print(f"[window] state={state} geometry={geo}")

        try:
            self.bind("<Configure>", on_configure)
            on_configure()
        except Exception:
            pass

    def _suppress_phantom_windows(self):
        """Monitor and log any unexpected Toplevel window creation."""
        original_init = tk.Toplevel.__init__

        def patched_init(toplevel_self, master=None, **kw):
            original_init(toplevel_self, master, **kw)
            try:
                title = toplevel_self.title()
                geo = toplevel_self.geometry()
                print(f"[TOPLEVEL] Created: title='{title}', "
                      f"geometry={geo}, master={master}")
            except Exception:
                pass

        tk.Toplevel.__init__ = patched_init

    def _build_ui(self):
        # === Tab button bar ===
        tab_bar = ctk.CTkFrame(self, height=40, corner_radius=0)
        tab_bar.pack(side="top", fill="x", padx=0, pady=0)
        tab_bar.pack_propagate(False)

        tab_names = [
            "Setup", "Headers", "Items", "Trainers",
            "NPCs", "Map Preview", "Statistics", "Execute",
        ]

        for i, name in enumerate(tab_names):
            btn = ctk.CTkButton(
                tab_bar, text=name, width=110, height=32,
                corner_radius=0,
                fg_color="transparent",
                hover_color="#2c3e50",
                text_color="#bdc3c7",
                font=ctk.CTkFont(size=13),
                command=lambda n=name: self._switch_tab(n),
            )
            btn.pack(side="left", padx=1, pady=4)
            self._tab_buttons[name] = btn

        # === Tab content container ===
        self._content_area = ctk.CTkFrame(self, corner_radius=0)
        self._content_area.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        # === Create tab frames ===
        for name in tab_names:
            frame = ctk.CTkFrame(self._content_area, corner_radius=0)
            self._tabs[name] = frame

        # === Create panels inside tab frames ===
        self.setup_panel = self._safe_create(
            SetupPanel, self._tabs["Setup"], "Setup")
        self.header_panel = self._safe_create(
            HeaderPanel, self._tabs["Headers"], "Headers")
        self.items_panel = self._safe_create(
            ItemsPanel, self._tabs["Items"], "Items")
        self.trainers_panel = self._safe_create(
            TrainersPanel, self._tabs["Trainers"], "Trainers")
        self.npc_panel = self._safe_create(
            NPCPanel, self._tabs["NPCs"], "NPCs")
        self.preview_panel = self._safe_create(
            PreviewPanel, self._tabs["Map Preview"], "Map Preview")
        self.stats_panel = self._safe_create(
            StatsPanel, self._tabs["Statistics"], "Statistics")
        self.execute_panel = self._safe_create(
            ExecutePanel, self._tabs["Execute"], "Execute")

        if self._panel_errors:
            print("=" * 50, file=sys.stderr)
            for err in self._panel_errors:
                print(err, file=sys.stderr)
            print("=" * 50, file=sys.stderr)

        # === Status bar ===
        self.status_var = ctk.StringVar(value="No project loaded")
        status_bar = ctk.CTkLabel(self, textvariable=self.status_var,
                                  anchor="w", height=24,
                                  font=ctk.CTkFont(size=12))
        status_bar.pack(side="bottom", fill="x", padx=8, pady=(0, 4))

        # Show first tab
        self._switch_tab("Setup")
        self.after(200, self._tab_health_check)

    def _safe_create(self, panel_class, parent, name: str):
        try:
            panel = panel_class(parent, self)
            panel.pack(fill="both", expand=True)
            print(f"[OK] {name} panel created")
            return panel
        except Exception as e:
            msg = f"[{name}] {traceback.format_exc()}"
            self._panel_errors.append(msg)
            print(f"[FAIL] {name} panel: {e}", file=sys.stderr)
            traceback.print_exc()
            fallback = ctk.CTkFrame(parent)
            fallback.pack(fill="both", expand=True)
            ctk.CTkLabel(
                fallback,
                text=f"Error loading {name} panel:\n\n{e}",
                font=ctk.CTkFont(size=14),
                text_color="#e74c3c",
                wraplength=600,
            ).pack(expand=True, pady=20)
            return fallback

    def _switch_tab(self, name: str):
        if name == self._active_tab:
            return

        # Hide all tabs
        for tab_name, frame in self._tabs.items():
            frame.pack_forget()

        # Show selected tab
        self._tabs[name].pack(fill="both", expand=True)

        # Update button colors
        for btn_name, btn in self._tab_buttons.items():
            if btn_name == name:
                btn.configure(fg_color="#1f6aa5", text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color="#bdc3c7")

        self._active_tab = name
        try:
            self.update_idletasks()
        except Exception:
            pass

    def _tab_health_check(self):
        """Re-pack active tab if platform rendering dropped it."""
        try:
            active = self._tabs.get(self._active_tab)
            if active is not None and not active.winfo_ismapped():
                active.pack(fill="both", expand=True)
                self.update_idletasks()
        except Exception:
            pass
        finally:
            # Keep a lightweight periodic health check while app is open.
            self.after(750, self._tab_health_check)

    # Public method for programmatic tab switching (used by NPC "Pick from Map")
    def set_tab(self, name: str):
        self._switch_tab(name)

    def set_status(self, text: str):
        self.status_var.set(text)
        self.update_idletasks()

    def on_project_loaded(self):
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
                print(f"Error refreshing headers: {e}", file=sys.stderr)

        if hasattr(self.stats_panel, 'refresh'):
            try:
                self.stats_panel.refresh()
            except Exception as e:
                print(f"Error refreshing stats: {e}", file=sys.stderr)

        self.set_status(
            f"Project loaded: {len(self.project.headers.headers)} headers, "
            f"{len(self.project.trainers.trainers)} trainers, "
            f"{len(self.project.items.items)} items"
        )

    def on_headers_selected(self, header_numbers: list[int]):
        self.selected_headers = header_numbers

        for panel_name in ['items_panel', 'trainers_panel', 'npc_panel']:
            panel = getattr(self, panel_name, None)
            if panel and hasattr(panel, 'on_headers_changed'):
                try:
                    panel.on_headers_changed()
                except Exception as e:
                    print(f"Error in {panel_name}: {e}", file=sys.stderr)

        if header_numbers:
            h = self.project.headers.headers.get(header_numbers[0])
            if h and hasattr(self.preview_panel, 'show_map'):
                try:
                    self.preview_panel.show_map(h)
                except Exception as e:
                    print(f"Error showing map: {e}", file=sys.stderr)

    def add_pending_edit(self, edit: dict):
        self.pending_edits.append(edit)
        if hasattr(self.execute_panel, 'refresh'):
            self.execute_panel.refresh()
        self.set_status(f"{len(self.pending_edits)} pending edit(s)")

    def clear_pending_edits(self):
        self.pending_edits.clear()
        if hasattr(self.execute_panel, 'refresh'):
            self.execute_panel.refresh()

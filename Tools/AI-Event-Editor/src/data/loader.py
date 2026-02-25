"""Central data loader that coordinates loading from all sources."""

from __future__ import annotations

import csv
import struct
from dataclasses import dataclass, field
from pathlib import Path

from .trainers import TrainerDatabase
from .headers import HeaderDatabase
from .items import ItemDatabase
from .flags import FlagRegistry
from .text_archives import TextArchiveDatabase
from .sprites import SpriteDatabase
from .variables import VariableDatabase
from .species import SpeciesDatabase
from .moves import MoveDatabase
from .abilities import AbilityDatabase
from .script_commands import ScriptCommandDatabase


@dataclass
class EventEntity:
    event_file: str
    index: int
    data: dict[str, str]


@dataclass
class EventData:
    overworlds: list[EventEntity] = field(default_factory=list)
    warps: list[EventEntity] = field(default_factory=list)
    spawnables: list[EventEntity] = field(default_factory=list)
    triggers: list[EventEntity] = field(default_factory=list)


class ProjectData:
    """Holds all loaded project data."""

    def __init__(self):
        self.trainers = TrainerDatabase()
        self.headers = HeaderDatabase()
        self.items = ItemDatabase()
        self.flags = FlagRegistry()
        self.text_archives = TextArchiveDatabase()
        self.sprites = SpriteDatabase()
        self.variables = VariableDatabase()
        self.species = SpeciesDatabase()
        self.moves = MoveDatabase()
        self.abilities = AbilityDatabase()
        self.script_commands = ScriptCommandDatabase()
        self.events = EventData()

        self.dspre_contents_path: Path | None = None
        self.hg_engine_path: Path | None = None
        self.project_root: Path | None = None
        self.analysis_path: Path | None = None

        self.maps_data: dict[int, bytes] = {}
        self.loaded = False
        self.load_errors: list[str] = []

    def detect_project_root(self, dspre_path: Path) -> Path | None:
        """Walk up from DSPRE_contents to find the project root (has Data/ and Tools/)."""
        for parent in [dspre_path] + list(dspre_path.parents):
            if (parent / "Data").is_dir() and (parent / "Tools").is_dir():
                return parent
        return None

    def load_all(self, dspre_contents: Path, hg_engine: Path | None = None,
                 progress_callback=None) -> list[str]:
        errors: list[str] = []
        self.dspre_contents_path = dspre_contents
        self.hg_engine_path = hg_engine
        self.project_root = self.detect_project_root(dspre_contents)

        if not self.project_root:
            errors.append("Could not detect project root (needs Data/ and Tools/ dirs)")
            self.load_errors = errors
            return errors

        self.analysis_path = self.project_root / "DSPRE-Contents-Analysis"

        steps = [
            ("Loading headers...", self._load_headers),
            ("Loading items...", self._load_items),
            ("Loading trainers...", self._load_trainers),
            ("Loading flags...", self._load_flags),
            ("Loading variables...", self._load_variables),
            ("Loading species/moves/abilities...", self._load_battle_constants),
            ("Loading script command metadata...", self._load_script_commands),
            ("Loading sprites...", self._load_sprites),
            ("Loading text archives...", self._load_text_archives),
            ("Loading event CSVs...", self._load_events),
            ("Loading map data...", self._load_maps),
        ]

        for i, (msg, func) in enumerate(steps):
            if progress_callback:
                progress_callback(msg, i / len(steps))
            try:
                func()
            except Exception as e:
                errors.append(f"{msg} FAILED: {e}")

        self.loaded = len(errors) == 0
        self.load_errors = errors
        if progress_callback:
            progress_callback("Done!", 1.0)
        return errors

    def _load_headers(self) -> None:
        csv_path = self.project_root / "Data" / "Header-Data" / "Header-Data-Main.csv"
        self.headers.load(csv_path)

    def _load_items(self) -> None:
        if self.hg_engine_path:
            inc_path = self.hg_engine_path / "asm" / "include" / "items.inc"
            if inc_path.exists():
                self.items.load(inc_path)
                return
        csv_path = self.analysis_path / "constants" / "items.csv"
        if csv_path and csv_path.exists():
            self.items.load_from_csv(csv_path)

    def _load_trainers(self) -> None:
        if self.hg_engine_path:
            trainers_s = self.hg_engine_path / "armips" / "data" / "trainers" / "trainers.s"
            if trainers_s.exists():
                self.trainers.load(trainers_s)

    def _load_flags(self) -> None:
        csv_path = self.project_root / "Data" / "Flag-Data" / "Flag-Data-Main.csv"
        if csv_path.exists():
            self.flags.load(csv_path)

    def _load_variables(self) -> None:
        csv_path = self.project_root / "Data" / "Variable-Data" / "Variable-Data-Main.csv"
        if csv_path.exists():
            self.variables.load(csv_path)

    def _load_battle_constants(self) -> None:
        if not self.hg_engine_path:
            return
        inc_dir = self.hg_engine_path / "asm" / "include"
        species_inc = inc_dir / "species.inc"
        moves_inc = inc_dir / "moves.inc"
        abilities_inc = inc_dir / "abilities.inc"
        if species_inc.exists():
            self.species.load(species_inc)
        if moves_inc.exists():
            self.moves.load(moves_inc)
        if abilities_inc.exists():
            self.abilities.load(abilities_inc)

    def _load_script_commands(self) -> None:
        if not self.project_root:
            return
        data_dir = self.project_root / "Data" / "Script-Data"
        cmd_csv = data_dir / "SCRCMD Database - HGSS.csv"
        action_csv = data_dir / "SCRCMD Database - Actions.csv"
        if cmd_csv.exists():
            self.script_commands.load_commands(cmd_csv)
        if action_csv.exists():
            self.script_commands.load_actions(action_csv)

    def _load_sprites(self) -> None:
        trainer_csv = self.project_root / "Data" / "Trainer-Data" / "Trainer-Data-Main.csv"
        if trainer_csv.exists():
            self.sprites.load_from_trainer_csv(trainer_csv)
        if self.hg_engine_path:
            ow_table = self.hg_engine_path / "src" / "field" / "overworld_table.c"
            if ow_table.exists():
                self.sprites.load_overworld_table(ow_table)

    def _load_text_archives(self) -> None:
        if not self.analysis_path:
            return
        ta_dir = self.analysis_path / "textArchives"
        if ta_dir.is_dir():
            self.text_archives.load(ta_dir)

    def _load_events(self) -> None:
        if not self.analysis_path:
            return
        events_dir = self.analysis_path / "events"
        for name, target_list in [
            ("overworlds.csv", self.events.overworlds),
            ("warps.csv", self.events.warps),
            ("spawnables.csv", self.events.spawnables),
            ("triggers.csv", self.events.triggers),
        ]:
            csv_path = events_dir / name
            if not csv_path.exists():
                continue
            target_list.clear()
            with csv_path.open(encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    target_list.append(EventEntity(
                        event_file=row.get("event_file", ""),
                        index=int(row.get("index", 0)),
                        data=dict(row),
                    ))

    def _load_maps(self) -> None:
        if not self.analysis_path:
            return
        maps_dir = self.analysis_path / "unpacked" / "maps"
        if not maps_dir.is_dir():
            maps_dir = self.dspre_contents_path / "unpacked" / "maps"
        if not maps_dir.is_dir():
            return

        for p in maps_dir.iterdir():
            try:
                map_id = int(p.name)
                self.maps_data[map_id] = p.read_bytes()
            except (ValueError, OSError):
                continue

    def get_overworlds_for_event(self, event_file: str) -> list[EventEntity]:
        ef = event_file.zfill(4)
        return [e for e in self.events.overworlds if e.event_file == ef]

    def get_warps_for_event(self, event_file: str) -> list[EventEntity]:
        ef = event_file.zfill(4)
        return [e for e in self.events.warps if e.event_file == ef]

    def get_spawnables_for_event(self, event_file: str) -> list[EventEntity]:
        ef = event_file.zfill(4)
        return [e for e in self.events.spawnables if e.event_file == ef]

    def get_triggers_for_event(self, event_file: str) -> list[EventEntity]:
        ef = event_file.zfill(4)
        return [e for e in self.events.triggers if e.event_file == ef]

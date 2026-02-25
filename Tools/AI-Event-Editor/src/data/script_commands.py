"""Script command and action metadata from SCRCMD CSVs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ScriptCommandInfo:
    opcode_hex: str
    decomp_name: str
    dspre_name: str
    parameters: str
    function: str


@dataclass
class ActionCommandInfo:
    opcode_hex: str
    decomp_name: str
    dspre_name: str
    function: str
    notes: str


class ScriptCommandDatabase:
    def __init__(self):
        self.commands: dict[str, ScriptCommandInfo] = {}
        self.actions: dict[str, ActionCommandInfo] = {}

    def load_commands(self, csv_path: Path) -> None:
        self.commands.clear()
        with csv_path.open(encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                opcode = (row.get("") or "").strip().upper()
                if not opcode:
                    continue
                self.commands[opcode] = ScriptCommandInfo(
                    opcode_hex=opcode,
                    decomp_name=(row.get("Decomp Names") or "").strip(),
                    dspre_name=(row.get("DSPRE Names") or "").strip(),
                    parameters=(row.get("Parameters") or "").strip(),
                    function=(row.get("Function") or "").strip(),
                )

    def load_actions(self, csv_path: Path) -> None:
        self.actions.clear()
        with csv_path.open(encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                opcode = (row.get("") or "").strip().upper()
                if not opcode:
                    continue
                self.actions[opcode] = ActionCommandInfo(
                    opcode_hex=opcode,
                    decomp_name=(row.get("Decomp Names") or "").strip(),
                    dspre_name=(row.get("DSPRE Names") or "").strip(),
                    function=(row.get("Function") or "").strip(),
                    notes=(row.get("Notes") or "").strip(),
                )


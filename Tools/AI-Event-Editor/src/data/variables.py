"""Variable registry from Variable-Data-Main.csv."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Variable:
    name: str
    value: int
    hex_str: str
    var_type: str

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()


class VariableDatabase:
    def __init__(self):
        self.variables: dict[int, Variable] = {}
        self._by_name: dict[str, Variable] = {}

    def load(self, csv_path: Path) -> None:
        self.variables.clear()
        self._by_name.clear()
        with csv_path.open(encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = (row.get("Variabled Name") or "").strip()
                dec_str = (row.get("Dec") or "").strip()
                hex_str = (row.get("Hex") or "").strip()
                var_type = (row.get("Variable Type") or "").strip()
                if not name or not dec_str:
                    continue
                try:
                    value = int(dec_str)
                except ValueError:
                    continue
                var = Variable(name=name, value=value, hex_str=hex_str, var_type=var_type)
                self.variables[value] = var
                self._by_name[name] = var

    def search(self, query: str, limit: int = 100) -> list[Variable]:
        q = query.upper().strip()
        if not q:
            return []
        out = [v for v in self.variables.values() if q in v.name]
        return sorted(out, key=lambda v: v.value)[:limit]

    def get_by_name(self, name: str) -> Variable | None:
        return self._by_name.get(name)


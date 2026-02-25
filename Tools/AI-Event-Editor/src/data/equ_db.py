"""Utility parser for .equ include files used by hg-engine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EquEntry:
    name: str
    value: int

    @property
    def display_name(self) -> str:
        if "_" not in self.name:
            return self.name.title()
        prefix, rest = self.name.split("_", 1)
        _ = prefix
        return rest.replace("_", " ").title()


class EquDatabase:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.entries: dict[int, EquEntry] = {}
        self._by_name: dict[str, EquEntry] = {}

    def load(self, path: Path) -> None:
        self.entries.clear()
        self._by_name.clear()
        text = path.read_text(encoding="utf-8", errors="replace")
        pattern = rf"\.equ\s+({self.prefix}_\w+),\s*([0-9]+)"
        for m in re.finditer(pattern, text):
            name = m.group(1).strip()
            value = int(m.group(2))
            entry = EquEntry(name=name, value=value)
            self.entries[value] = entry
            self._by_name[name] = entry

    def search(self, query: str, limit: int = 100) -> list[EquEntry]:
        q = query.upper().strip()
        if not q:
            return []
        out = [e for e in self.entries.values() if q in e.name]
        return sorted(out, key=lambda e: e.value)[:limit]

    def get_by_name(self, name: str) -> EquEntry | None:
        return self._by_name.get(name)


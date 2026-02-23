"""Manage flag allocation from Flag-Data-Main.csv."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Flag:
    decimal: int
    hex_str: str
    name: str
    flag_type: str
    category: str
    event_file: str
    ow_id: str
    description: str

    @property
    def is_available(self) -> bool:
        return not self.name or self.name.startswith("MAPTEMP_")


class FlagRegistry:
    def __init__(self):
        self.flags: dict[int, Flag] = {}
        self._csv_path: Path | None = None

    def load(self, csv_path: Path) -> None:
        self._csv_path = csv_path
        self.flags.clear()

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dec_str = row.get("Decimal", "").strip()
                if not dec_str:
                    continue
                try:
                    dec = int(dec_str)
                except ValueError:
                    continue
                self.flags[dec] = Flag(
                    decimal=dec,
                    hex_str=row.get("Hex", ""),
                    name=row.get("Name", ""),
                    flag_type=row.get("Type", ""),
                    category=row.get("CATEGORY", ""),
                    event_file=row.get("Event File", ""),
                    ow_id=row.get("OWID", ""),
                    description=row.get("Description", ""),
                )

    def available_count(self) -> int:
        return sum(1 for f in self.flags.values() if f.is_available)

    def used_count(self) -> int:
        return sum(1 for f in self.flags.values() if not f.is_available)

    def allocate(self, count: int = 1,
                 description: str = "", event_file: str = "") -> list[int]:
        allocated: list[int] = []
        for dec in sorted(self.flags.keys()):
            if len(allocated) >= count:
                break
            flag = self.flags[dec]
            if flag.is_available:
                flag.name = f"AI_ITEM_{dec}"
                flag.flag_type = "ITEM FLAG"
                flag.category = "AI_GENERATED"
                flag.description = description
                flag.event_file = event_file
                allocated.append(dec)

        return allocated

    def release(self, flag_id: int) -> None:
        if flag_id in self.flags:
            f = self.flags[flag_id]
            f.name = f"MAPTEMP_{flag_id:03d}"
            f.flag_type = "MAP FLAG"
            f.category = ""
            f.description = ""
            f.event_file = ""
            f.ow_id = ""

    def save(self) -> None:
        if not self._csv_path:
            return
        fieldnames = [
            "Story Point", "Hex", "Decimal", "Name", "Type",
            "CATEGORY", "Event File", "OWID", "Description",
        ]
        rows = []
        for dec in sorted(self.flags.keys()):
            f = self.flags[dec]
            rows.append({
                "Story Point": "",
                "Hex": f.hex_str,
                "Decimal": str(f.decimal),
                "Name": f.name,
                "Type": f.flag_type,
                "CATEGORY": f.category,
                "Event File": f.event_file,
                "OWID": f.ow_id,
                "Description": f.description,
            })
        with self._csv_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

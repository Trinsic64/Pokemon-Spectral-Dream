"""Parse Header-Data-Main.csv for map header information."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Header:
    number: int
    name: str
    map_type: str
    matrix: int
    script_file: int
    level_script_file: int
    event_file: int
    text_archive: int
    wild_file: int
    area_data: int
    music_day: int
    music_night: int
    weather: str
    fly_allowed: bool
    is_kanto: bool

    @property
    def display_name(self) -> str:
        return f"H{self.number}: {self.name}"


class HeaderDatabase:
    def __init__(self):
        self.headers: dict[int, Header] = {}
        self._by_event_file: dict[int, list[int]] = {}
        self._by_type: dict[str, list[int]] = {}

    def load(self, csv_path: Path) -> None:
        self.headers.clear()
        self._by_event_file.clear()
        self._by_type.clear()

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    h = Header(
                        number=int(row["HEADER #"]),
                        name=row.get("Internal Name", ""),
                        map_type=row.get("Type", ""),
                        matrix=int(row.get("Matrix", 0)),
                        script_file=int(row.get("Script File", 0)),
                        level_script_file=int(row.get("Level Script File", 0)),
                        event_file=int(row.get("Event File", 0)),
                        text_archive=int(row.get("Text Archive", 0)),
                        wild_file=int(row.get("Wild File", 255)),
                        area_data=int(row.get("Area Data", 0)),
                        music_day=int(row.get("Music Day", 0)),
                        music_night=int(row.get("Music Night", 0)),
                        weather=row.get("Weather", "Normal"),
                        fly_allowed=row.get("FlyAllowed", "FALSE").upper() == "TRUE",
                        is_kanto=row.get("IsKanto", "FALSE").upper() == "TRUE",
                    )
                    self.headers[h.number] = h
                    self._by_event_file.setdefault(h.event_file, []).append(h.number)
                    self._by_type.setdefault(h.map_type, []).append(h.number)
                except (ValueError, KeyError):
                    continue

    def get_by_event_file(self, ef: int) -> list[Header]:
        return [self.headers[i] for i in self._by_event_file.get(ef, [])]

    def get_by_type(self, map_type: str) -> list[Header]:
        return [self.headers[i] for i in self._by_type.get(map_type, [])]

    def get_types(self) -> list[str]:
        return sorted(self._by_type.keys())

    def search(self, query: str) -> list[Header]:
        q = query.lower()
        return [h for h in self.headers.values()
                if q in h.name.lower() or q in str(h.number)]

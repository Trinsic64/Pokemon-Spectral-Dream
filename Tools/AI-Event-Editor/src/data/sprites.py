"""TrainerClass -> overlay_entry (OWID) sprite mapping."""

from __future__ import annotations

import csv
import re
from pathlib import Path


class SpriteDatabase:
    """Maps trainer classes to their overworld sprite overlay_entry values."""

    def __init__(self):
        self._class_to_overlay: dict[str, list[int]] = {}
        self._overlay_to_classes: dict[int, list[str]] = {}
        self.all_overlays: set[int] = set()

    def load_from_trainer_csv(self, csv_path: Path) -> None:
        """Build mapping from Trainer-Data-Main.csv OWID column."""
        self._class_to_overlay.clear()
        self._overlay_to_classes.clear()

        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tc = row.get("TrainerClass", "").strip()
                owid_str = row.get("OWID", "").strip()
                if not tc or not owid_str:
                    continue
                try:
                    owid = int(owid_str)
                except ValueError:
                    continue

                self.all_overlays.add(owid)

                if owid not in self._class_to_overlay.get(tc, []):
                    self._class_to_overlay.setdefault(tc, []).append(owid)
                if tc not in self._overlay_to_classes.get(owid, []):
                    self._overlay_to_classes.setdefault(owid, []).append(tc)

    def load_overworld_table(self, overworld_table_path: Path) -> None:
        """Parse overworld_table.c to get all valid overlay tags."""
        text = overworld_table_path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\.tag\s*=\s*(\d+)", text):
            self.all_overlays.add(int(m.group(1)))

    def get_overlay_for_class(self, trainer_class: str) -> int:
        overlays = self._class_to_overlay.get(trainer_class, [])
        if overlays:
            return overlays[0]
        return 0

    def get_all_overlays_for_class(self, trainer_class: str) -> list[int]:
        return self._class_to_overlay.get(trainer_class, [])

    def get_classes_for_overlay(self, overlay: int) -> list[str]:
        return self._overlay_to_classes.get(overlay, [])

    ITEM_BALL_OVERLAY = 87

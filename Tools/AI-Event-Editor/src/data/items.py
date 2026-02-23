"""Parse item constants from hg-engine items.inc."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Item:
    name: str
    id: int

    @property
    def script_number(self) -> int:
        """Event file script field = 7000 + item_ID."""
        return 7000 + self.id

    @property
    def display_name(self) -> str:
        clean = self.name.replace("ITEM_", "").replace("_", " ").title()
        return clean


ITEM_CATEGORIES = {
    "Early Healing": [
        "ITEM_POTION", "ITEM_ANTIDOTE", "ITEM_BURN_HEAL", "ITEM_ICE_HEAL",
        "ITEM_AWAKENING", "ITEM_PARALYZE_HEAL", "ITEM_ORAN_BERRY",
        "ITEM_PECHA_BERRY", "ITEM_CHERI_BERRY", "ITEM_CHESTO_BERRY",
        "ITEM_RAWST_BERRY", "ITEM_ASPEAR_BERRY",
    ],
    "Mid Healing": [
        "ITEM_SUPER_POTION", "ITEM_HYPER_POTION", "ITEM_FULL_HEAL",
        "ITEM_REVIVE", "ITEM_LEMONADE", "ITEM_MOOMOO_MILK",
        "ITEM_SITRUS_BERRY", "ITEM_LUM_BERRY",
    ],
    "Late Healing": [
        "ITEM_MAX_POTION", "ITEM_FULL_RESTORE", "ITEM_MAX_REVIVE",
        "ITEM_RARE_CANDY", "ITEM_PP_MAX", "ITEM_PP_UP",
    ],
    "Battle Items": [
        "ITEM_X_ATTACK", "ITEM_X_DEFENSE", "ITEM_X_SP_ATK",
        "ITEM_X_SP_DEF", "ITEM_X_SPEED", "ITEM_X_ACCURACY",
        "ITEM_GUARD_SPEC", "ITEM_DIRE_HIT",
    ],
    "Hold Items": [
        "ITEM_LEFTOVERS", "ITEM_LIFE_ORB", "ITEM_CHOICE_BAND",
        "ITEM_CHOICE_SPECS", "ITEM_CHOICE_SCARF", "ITEM_FOCUS_SASH",
        "ITEM_EVIOLITE", "ITEM_ASSAULT_VEST", "ITEM_ROCKY_HELMET",
        "ITEM_EXPERT_BELT", "ITEM_MUSCLE_BAND", "ITEM_WISE_GLASSES",
    ],
    "Pokeballs": [
        "ITEM_POKE_BALL", "ITEM_GREAT_BALL", "ITEM_ULTRA_BALL",
        "ITEM_QUICK_BALL", "ITEM_DUSK_BALL", "ITEM_TIMER_BALL",
        "ITEM_NET_BALL", "ITEM_LUXURY_BALL",
    ],
    "Evolution Stones": [
        "ITEM_FIRE_STONE", "ITEM_WATER_STONE", "ITEM_THUNDER_STONE",
        "ITEM_LEAF_STONE", "ITEM_MOON_STONE", "ITEM_SUN_STONE",
        "ITEM_SHINY_STONE", "ITEM_DUSK_STONE", "ITEM_DAWN_STONE",
    ],
}


class ItemDatabase:
    def __init__(self):
        self.items: dict[int, Item] = {}
        self._by_name: dict[str, Item] = {}

    def load(self, items_inc_path: Path) -> None:
        self.items.clear()
        self._by_name.clear()

        text = items_inc_path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\.equ\s+(ITEM_\w+),\s*(\d+)", text):
            name = m.group(1)
            val = int(m.group(2))
            item = Item(name=name, id=val)
            self.items[val] = item
            self._by_name[name] = item

    def load_from_csv(self, csv_path: Path) -> None:
        """Alternative: load from constants/items.csv."""
        import csv
        self.items.clear()
        self._by_name.clear()
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row["name"]
                val = int(row["numeric_id"])
                item = Item(name=name, id=val)
                self.items[val] = item
                self._by_name[name] = item

    def get_by_name(self, name: str) -> Item | None:
        return self._by_name.get(name)

    def get_category(self, category: str) -> list[Item]:
        names = ITEM_CATEGORIES.get(category, [])
        return [self._by_name[n] for n in names if n in self._by_name]

    def get_mega_stones(self) -> list[Item]:
        return [it for it in self.items.values()
                if it.name.endswith("ITE") and "MEGA" not in it.name
                and it.name not in ("ITEM_DYNAMITE", "ITEM_WHITE")]

    def get_tms(self) -> list[Item]:
        return sorted(
            [it for it in self.items.values() if it.name.startswith("ITEM_TM")],
            key=lambda x: x.id,
        )

    def search(self, query: str) -> list[Item]:
        q = query.upper()
        return [it for it in self.items.values() if q in it.name]

    def get_categories(self) -> list[str]:
        return list(ITEM_CATEGORIES.keys())

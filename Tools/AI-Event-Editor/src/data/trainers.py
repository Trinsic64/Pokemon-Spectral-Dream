"""Parse trainers.s from hg-engine to build trainer database."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Pokemon:
    species: str
    level: int
    moves: list[str] = field(default_factory=list)
    ability: str = ""
    ivs: int = 0


@dataclass
class Trainer:
    id: int
    name: str
    trainer_class: str
    num_mons: int
    pokemon: list[Pokemon] = field(default_factory=list)
    items: list[str] = field(default_factory=list)
    ai_flags: str = ""
    battle_type: str = "SINGLE_BATTLE"
    mon_type_flags: str = ""

    @property
    def level_range(self) -> tuple[int, int]:
        if not self.pokemon:
            return (0, 0)
        levels = [p.level for p in self.pokemon]
        return (min(levels), max(levels))

    @property
    def avg_level(self) -> float:
        if not self.pokemon:
            return 0.0
        return sum(p.level for p in self.pokemon) / len(self.pokemon)

    @property
    def script_number(self) -> int:
        return 2999 + self.id

    @property
    def partner_script_number(self) -> int:
        return 4999 + self.id


class TrainerDatabase:
    def __init__(self):
        self.trainers: dict[int, Trainer] = {}
        self._by_class: dict[str, list[int]] = {}

    def load(self, trainers_s_path: Path) -> None:
        text = trainers_s_path.read_text(encoding="utf-8", errors="replace")
        self.trainers.clear()
        self._by_class.clear()

        trainer_blocks = re.split(r"(?=^trainerdata\s)", text, flags=re.MULTILINE)

        for block in trainer_blocks:
            block = block.strip()
            if not block.startswith("trainerdata"):
                continue

            trainer = self._parse_block(block)
            if trainer:
                self.trainers[trainer.id] = trainer
                self._by_class.setdefault(trainer.trainer_class, []).append(trainer.id)

    def _parse_block(self, block: str) -> Trainer | None:
        header = re.match(r'trainerdata\s+(\d+),\s*"([^"]*)"', block)
        if not header:
            return None

        tid = int(header.group(1))
        name = header.group(2)

        def _find(pattern: str, default: str = "") -> str:
            m = re.search(pattern, block)
            return m.group(1).strip() if m else default

        trainer_class = _find(r"trainerclass\s+(\S+)")
        num_mons = int(_find(r"nummons\s+(\d+)", "0"))
        mon_type = _find(r"trainermontype\s+(.+?)$", "")
        ai = _find(r"aiflags\s+(.+?)$", "0")
        btype = _find(r"battletype\s+(\S+)", "SINGLE_BATTLE")

        items_raw = re.findall(r"^\s+item\s+(\S+)", block, re.MULTILINE)

        pokemon: list[Pokemon] = []
        party_match = re.search(r"party\s+\d+(.+?)endparty", block, re.DOTALL)
        if party_match:
            party_text = party_match.group(1)
            mon_sections = re.split(r"//\s*mon\s+\d+", party_text)
            for section in mon_sections:
                section = section.strip()
                if not section:
                    continue
                species_m = re.search(r"(?:pokemon|monwithform)\s+(\S+)", section)
                level_m = re.search(r"level\s+(\d+)", section)
                if not species_m or not level_m:
                    continue
                moves = re.findall(r"move\s+(\S+)", section)
                ability_m = re.search(r"ability\s+(\S+)", section)
                ivs_m = re.search(r"ivs\s+(\d+)", section)
                pokemon.append(Pokemon(
                    species=species_m.group(1),
                    level=int(level_m.group(1)),
                    moves=moves,
                    ability=ability_m.group(1) if ability_m else "",
                    ivs=int(ivs_m.group(1)) if ivs_m else 0,
                ))

        return Trainer(
            id=tid, name=name, trainer_class=trainer_class,
            num_mons=num_mons, pokemon=pokemon, items=items_raw,
            ai_flags=ai, battle_type=btype, mon_type_flags=mon_type,
        )

    def get_by_class(self, trainer_class: str) -> list[Trainer]:
        ids = self._by_class.get(trainer_class, [])
        return [self.trainers[i] for i in ids]

    def get_classes(self) -> list[str]:
        return sorted(self._by_class.keys())

    def get_by_level_range(self, min_lv: int, max_lv: int) -> list[Trainer]:
        result = []
        for t in self.trainers.values():
            if t.num_mons == 0:
                continue
            lo, hi = t.level_range
            if lo >= min_lv and hi <= max_lv:
                result.append(t)
        return result

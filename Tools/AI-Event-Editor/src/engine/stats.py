"""Global event statistics tracking."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..data.loader import ProjectData


@dataclass
class EntityStats:
    total: int = 0
    by_type: Counter = field(default_factory=Counter)
    by_subtype: Counter = field(default_factory=Counter)
    per_event_file: Counter = field(default_factory=Counter)


@dataclass
class GlobalStats:
    overworlds: EntityStats = field(default_factory=EntityStats)
    items: EntityStats = field(default_factory=EntityStats)
    trainers: EntityStats = field(default_factory=EntityStats)
    npcs: EntityStats = field(default_factory=EntityStats)
    warps: EntityStats = field(default_factory=EntityStats)
    spawnables: EntityStats = field(default_factory=EntityStats)
    triggers: EntityStats = field(default_factory=EntityStats)
    flags_used: int = 0
    flags_available: int = 0
    flags_total: int = 0


class StatsEngine:
    """Computes and tracks global event statistics."""

    def __init__(self):
        self.stats = GlobalStats()

    def compute(self, project: ProjectData) -> GlobalStats:
        self.stats = GlobalStats()

        # Overworld breakdown
        for ow in project.events.overworlds:
            ef = ow.event_file
            ow_type = ow.data.get("type", "NORMAL")
            overlay = ow.data.get("overlay_entry", "0")
            script = ow.data.get("script", "0")

            self.stats.overworlds.total += 1
            self.stats.overworlds.by_type[ow_type] += 1
            self.stats.overworlds.per_event_file[ef] += 1

            if ow_type == "ITEM":
                self.stats.items.total += 1
                self.stats.items.per_event_file[ef] += 1
                try:
                    script_num = int(script)
                    if script_num >= 7000:
                        item_id = script_num - 7000
                        item_obj = project.items.items.get(item_id)
                        if item_obj:
                            self.stats.items.by_subtype[item_obj.display_name] += 1
                        else:
                            self.stats.items.by_subtype[f"Item #{item_id}"] += 1
                except ValueError:
                    pass

            elif ow_type == "TRAINER":
                self.stats.trainers.total += 1
                self.stats.trainers.per_event_file[ef] += 1
                try:
                    script_num = int(script)
                    trainer_id = script_num - 2999
                    trainer = project.trainers.trainers.get(trainer_id)
                    if trainer:
                        class_name = trainer.trainer_class.replace(
                            "TRAINERCLASS_", "").replace("_", " ").title()
                        self.stats.trainers.by_subtype[class_name] += 1
                    else:
                        self.stats.trainers.by_subtype[f"Trainer #{trainer_id}"] += 1
                except ValueError:
                    pass

            else:
                self.stats.npcs.total += 1
                self.stats.npcs.per_event_file[ef] += 1
                self.stats.npcs.by_subtype[f"Sprite {overlay}"] += 1

        # Warps
        self.stats.warps.total = len(project.events.warps)
        for w in project.events.warps:
            self.stats.warps.per_event_file[w.event_file] += 1

        # Spawnables
        self.stats.spawnables.total = len(project.events.spawnables)
        for s in project.events.spawnables:
            self.stats.spawnables.per_event_file[s.event_file] += 1

        # Triggers
        self.stats.triggers.total = len(project.events.triggers)
        for t in project.events.triggers:
            self.stats.triggers.per_event_file[t.event_file] += 1

        # Flags
        self.stats.flags_used = project.flags.used_count()
        self.stats.flags_available = project.flags.available_count()
        self.stats.flags_total = len(project.flags.flags)

        return self.stats

    def get_summary_lines(self) -> list[str]:
        s = self.stats
        lines = [
            f"=== Global Event Statistics ===",
            f"",
            f"OW Total: {s.overworlds.total}",
            f"  Items: {s.items.total}",
        ]
        for name, count in s.items.by_subtype.most_common(20):
            lines.append(f"    {name}: {count}")
        lines.append(f"  Trainers: {s.trainers.total}")
        for name, count in s.trainers.by_subtype.most_common(20):
            lines.append(f"    {name}: {count}")
        lines.append(f"  NPCs: {s.npcs.total}")
        lines.extend([
            f"",
            f"Warps: {s.warps.total}",
            f"Spawnables: {s.spawnables.total}",
            f"Triggers: {s.triggers.total}",
            f"",
            f"Flags: {s.flags_used}/{s.flags_total} used"
            f" ({s.flags_available} available)",
        ])
        return lines

"""Canonical sub-event schema and deterministic script pipeline input."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

SubEventKind = Literal[
    "dialogue",
    "movement_path",
    "give_item",
    "give_pokemon",
    "set_flag",
    "set_var",
    "check_flag",
    "check_var",
    "branch_label",
    "end",
]


@dataclass
class SubEvent:
    kind: SubEventKind
    params: dict[str, object] = field(default_factory=dict)
    comment: str = ""


@dataclass
class SubEventChain:
    """Named chain of scriptable sub-events for one NPC interaction."""

    name: str
    events: list[SubEvent] = field(default_factory=list)

    def append(self, kind: SubEventKind, **params: object) -> None:
        self.events.append(SubEvent(kind=kind, params=params))

    def to_manifest(self) -> dict[str, object]:
        return {
            "name": self.name,
            "events": [
                {
                    "kind": ev.kind,
                    "params": ev.params,
                    "comment": ev.comment,
                }
                for ev in self.events
            ],
        }


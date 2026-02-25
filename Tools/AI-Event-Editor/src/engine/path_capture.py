"""Arrow-key path capture model and action mapping helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["UP", "DOWN", "LEFT", "RIGHT"]
Speed = Literal["slow", "normal", "fast"]


@dataclass
class PathStep:
    direction: Direction
    frames_per_tile: int

    @property
    def action_name(self) -> str:
        suffix = {
            16: "16",
            8: "8",
            4: "4",
        }.get(self.frames_per_tile, "8")
        name = {
            "UP": "WalkNorth",
            "DOWN": "WalkSouth",
            "LEFT": "WalkWest",
            "RIGHT": "WalkEast",
        }[self.direction]
        return f"{name}{suffix}"


class PathCapture:
    def __init__(self):
        self.steps: list[PathStep] = []
        self.speed: Speed = "normal"

    def clear(self) -> None:
        self.steps.clear()

    def set_speed(self, speed: Speed) -> None:
        self.speed = speed

    def push_direction(self, direction: Direction) -> None:
        frames = {
            "slow": 16,
            "normal": 8,
            "fast": 4,
        }[self.speed]
        self.steps.append(PathStep(direction=direction, frames_per_tile=frames))

    def to_action_lines(self, object_var: str = "LAST_TALKED") -> list[str]:
        if not self.steps:
            return []
        lines = [f"ApplyMovement {object_var}, _MOVE_PATH"]
        for step in self.steps:
            lines.append(f"Action {step.action_name}")
        lines.append("Action EndMovement")
        lines.append("WaitMovement")
        return lines


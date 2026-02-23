"""Collision-aware entity placement engine."""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Tile:
    x: int
    y: int
    collision: int

    @property
    def is_walkable(self) -> bool:
        return self.collision == 0x00 or self.collision == 0x80


@dataclass
class PlacementSuggestion:
    x_map: int
    y_map: int
    x_matrix: int
    y_matrix: int
    score: float  # higher = better placement


class MapGrid:
    """32x32 collision grid for a single map tile."""

    def __init__(self, map_id: int):
        self.map_id = map_id
        self.tiles: list[list[int]] = [[0] * 32 for _ in range(32)]
        self.width = 32
        self.height = 32

    def load_from_bytes(self, data: bytes) -> None:
        if len(data) < 2:
            return
        # Map permission format: 32x32 grid of 2-byte permission values
        # The collision byte is at offset 1 of each 2-byte entry
        for y in range(32):
            for x in range(32):
                offset = (y * 32 + x) * 2
                if offset + 1 < len(data):
                    self.tiles[y][x] = data[offset + 1]

    def is_walkable(self, x: int, y: int) -> bool:
        if 0 <= x < 32 and 0 <= y < 32:
            val = self.tiles[y][x]
            return val == 0x00 or val == 0x80
        return False

    def is_blocked(self, x: int, y: int) -> bool:
        return not self.is_walkable(x, y)


class PlacementEngine:
    """Suggests valid positions for entities on maps."""

    def __init__(self):
        self._grids: dict[int, MapGrid] = {}

    def load_map(self, map_id: int, data: bytes) -> MapGrid:
        grid = MapGrid(map_id)
        grid.load_from_bytes(data)
        self._grids[map_id] = grid
        return grid

    def get_grid(self, map_id: int) -> MapGrid | None:
        return self._grids.get(map_id)

    def suggest_positions(self, map_id: int,
                          existing_positions: list[tuple[int, int]],
                          count: int = 5,
                          min_distance_from_blocked: int = 1,
                          x_matrix: int = 0,
                          y_matrix: int = 0) -> list[PlacementSuggestion]:
        grid = self._grids.get(map_id)
        if not grid:
            return []

        occupied = set(existing_positions)
        candidates: list[PlacementSuggestion] = []

        # Find playable bounding box
        min_x, max_x, min_y, max_y = 31, 0, 31, 0
        for y in range(32):
            for x in range(32):
                if grid.is_walkable(x, y):
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)

        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                if not grid.is_walkable(x, y):
                    continue
                if (x, y) in occupied:
                    continue

                # Score: prefer tiles further from edges and blocked tiles
                blocked_neighbors = 0
                for dx in range(-min_distance_from_blocked, min_distance_from_blocked + 1):
                    for dy in range(-min_distance_from_blocked, min_distance_from_blocked + 1):
                        if dx == 0 and dy == 0:
                            continue
                        if grid.is_blocked(x + dx, y + dy):
                            blocked_neighbors += 1

                # Prefer tiles near walls (alcoves) but not directly adjacent
                alcove_score = 0
                if blocked_neighbors >= 2 and blocked_neighbors <= 4:
                    alcove_score = 2.0
                elif blocked_neighbors >= 1:
                    alcove_score = 1.0

                dist_from_center = abs(x - (min_x + max_x) / 2) + abs(y - (min_y + max_y) / 2)
                center_score = 1.0 / (1.0 + dist_from_center * 0.1)

                min_dist_to_existing = float("inf")
                for ex, ey in occupied:
                    d = abs(x - ex) + abs(y - ey)
                    min_dist_to_existing = min(min_dist_to_existing, d)
                spacing_score = min(min_dist_to_existing / 5.0, 2.0) if occupied else 1.0

                score = alcove_score + center_score + spacing_score

                if blocked_neighbors == 0 or min_distance_from_blocked == 0:
                    candidates.append(PlacementSuggestion(
                        x_map=x, y_map=y,
                        x_matrix=x_matrix, y_matrix=y_matrix,
                        score=score,
                    ))

        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:count]

    def get_collision_grid(self, map_id: int) -> list[list[int]] | None:
        grid = self._grids.get(map_id)
        return grid.tiles if grid else None

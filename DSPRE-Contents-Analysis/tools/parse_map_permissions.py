#!/usr/bin/env python3
"""
parse_map_permissions.py

Extracts 32x32 collision grids from unpacked/maps/ binary files.

Usage:
    python tools/parse_map_permissions.py                  # parse all maps, summary CSV
    python tools/parse_map_permissions.py --map 0000       # show one map's grid
    python tools/parse_map_permissions.py --map 0000 --visual  # ASCII art grid

Output: events/map-permissions.csv (map_id, walkable_count, blocked_count, special_count)

The collision grid for any map can also be queried programmatically via
parse_map_file() which returns a 32x32 list of (type, collision) tuples.

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
UNPACKED_MAPS = ANALYSIS_ROOT / "unpacked" / "maps"
OUTPUT_CSV = ANALYSIS_ROOT / "events" / "map-permissions.csv"

MAP_SIZE = 32
COLLISION_WALKABLE = 0x00
COLLISION_BLOCKED = 0x80


def parse_map_file(data: bytes) -> list[list[tuple[int, int]]]:
    """
    Parse a map binary file and return a 32x32 grid of (tile_type, collision).
    Handles the HGSS BGS header if present.
    """
    perms_len = struct.unpack_from("<I", data, 0)[0]
    if perms_len != MAP_SIZE * MAP_SIZE * 2:
        return []

    pos = 16  # after the 4 section-length uint32s

    # HGSS: check for BGS header (signature 0x1234)
    if len(data) > pos + 2:
        bgs_sig = struct.unpack_from("<H", data, pos)[0]
        if bgs_sig == 0x1234:
            bgs_data_len = struct.unpack_from("<H", data, pos + 2)[0]
            pos += 4 + bgs_data_len

    grid: list[list[tuple[int, int]]] = []
    for row in range(MAP_SIZE):
        row_data = []
        for col in range(MAP_SIZE):
            idx = pos + (row * MAP_SIZE + col) * 2
            if idx + 1 >= len(data):
                row_data.append((0, COLLISION_BLOCKED))
            else:
                tile_type = data[idx]
                collision = data[idx + 1]
                row_data.append((tile_type, collision))
        grid.append(row_data)
    return grid


def grid_stats(grid: list[list[tuple[int, int]]]) -> tuple[int, int, int]:
    """Return (walkable, blocked, special) counts."""
    walkable = blocked = special = 0
    for row in grid:
        for _, coll in row:
            if coll == COLLISION_WALKABLE:
                walkable += 1
            elif coll == COLLISION_BLOCKED:
                blocked += 1
            else:
                special += 1
    return walkable, blocked, special


def print_visual(grid: list[list[tuple[int, int]]], map_id: str) -> None:
    """Print an ASCII visualization of the collision grid."""
    print(f"Map {map_id} collision grid (. = walkable, # = blocked, ? = special):")
    for row in grid:
        line = ""
        for _, coll in row:
            if coll == COLLISION_WALKABLE:
                line += "."
            elif coll == COLLISION_BLOCKED:
                line += "#"
            else:
                line += "?"
        print(line)


def walkable_positions(grid: list[list[tuple[int, int]]]) -> list[tuple[int, int]]:
    """Return list of (x, y) positions that are walkable (collision == 0x00)."""
    positions = []
    for y, row in enumerate(grid):
        for x, (_, coll) in enumerate(row):
            if coll == COLLISION_WALKABLE:
                positions.append((x, y))
    return positions


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse map permission/collision data.")
    parser.add_argument("--map", metavar="NNNN", help="Show one specific map.")
    parser.add_argument("--visual", action="store_true", help="Show ASCII grid visualization.")
    args = parser.parse_args()

    if not UNPACKED_MAPS.exists():
        print(f"[ERROR] Maps directory not found: {UNPACKED_MAPS}", file=sys.stderr)
        sys.exit(1)

    if args.map:
        map_id = args.map.zfill(4)
        map_path = UNPACKED_MAPS / map_id
        if not map_path.exists():
            print(f"[ERROR] Map file not found: {map_path}", file=sys.stderr)
            sys.exit(1)
        grid = parse_map_file(map_path.read_bytes())
        if not grid:
            print(f"[ERROR] Could not parse map {map_id}", file=sys.stderr)
            sys.exit(1)
        w, b, s = grid_stats(grid)
        print(f"Map {map_id}: walkable={w}, blocked={b}, special={s}")
        if args.visual:
            print()
            print_visual(grid, map_id)
        else:
            wp = walkable_positions(grid)
            print(f"Walkable positions: {len(wp)}")
            if wp:
                cx = sum(x for x, _ in wp) // len(wp)
                cy = sum(y for _, y in wp) // len(wp)
                print(f"Center of walkable area: ({cx}, {cy})")
        return

    # Parse all maps and generate summary CSV
    map_files = sorted(f for f in UNPACKED_MAPS.iterdir() if f.is_file())
    rows = []
    parsed = 0
    for mf in map_files:
        try:
            grid = parse_map_file(mf.read_bytes())
            if not grid:
                continue
            w, b, s = grid_stats(grid)
            rows.append({
                "map_id": mf.stem,
                "walkable": w,
                "blocked": b,
                "special": s,
            })
            parsed += 1
        except Exception:
            continue

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["map_id", "walkable", "blocked", "special"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Parsed {parsed}/{len(map_files)} map files.")
    print(f"Wrote {len(rows)} entries to events/map-permissions.csv")
    avg_w = sum(r["walkable"] for r in rows) / len(rows) if rows else 0
    print(f"Average walkable tiles per map: {avg_w:.0f}/1024")


if __name__ == "__main__":
    main()

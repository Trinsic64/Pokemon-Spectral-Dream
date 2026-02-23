#!/usr/bin/env python3
"""
map_lookup.py

Resolves the full chain: event_file -> header -> matrix -> map file numbers
-> collision data. Tells an AI which tiles are walkable for a given event file.

Usage:
    python tools/map_lookup.py --event 0057                       # show map info for event 0057
    python tools/map_lookup.py --event 0057 --visual              # show collision grids
    python tools/map_lookup.py --event 0057 --walkable            # list all walkable positions
    python tools/map_lookup.py --header 10                        # look up by header number
    python tools/map_lookup.py --header 10 --matrix-pos 30,38     # drill into overworld cell [row,col]
    python tools/map_lookup.py --header 11 --suggest-placement    # suggest safe event positions
    python tools/map_lookup.py --event 0060 --suggest-placement   # suggest placement avoiding existing events

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

HEADER_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"
UNPACKED_MATRICES = ANALYSIS_ROOT / "unpacked" / "matrices"
UNPACKED_MAPS = ANALYSIS_ROOT / "unpacked" / "maps"
OVERWORLDS_CSV = ANALYSIS_ROOT / "events" / "overworlds.csv"
SPAWNABLES_CSV = ANALYSIS_ROOT / "events" / "spawnables.csv"

MAP_SIZE = 32
MATRIX_EMPTY = 0xFFFF


def load_header_data() -> list[dict]:
    if not HEADER_CSV.exists():
        return []
    with HEADER_CSV.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def find_headers_for_event(headers: list[dict], event_file: str) -> list[dict]:
    """Find all headers that reference a given event file number."""
    target = str(int(float(event_file)))
    return [h for h in headers if h.get("Event File", "").strip() == target]


def parse_matrix(data: bytes) -> dict:
    """Parse a matrix binary file. Returns width, height, name, maps grid."""
    width = data[0]
    height = data[1]
    has_headers = bool(data[2])
    has_heights = bool(data[3])
    name_len = data[4]
    name = data[5:5 + name_len].decode("utf-8", errors="replace")
    pos = 5 + name_len

    if has_headers:
        pos += height * width * 2
    if has_heights:
        pos += height * width

    maps: list[list[int]] = []
    for row in range(height):
        row_data = []
        for col in range(width):
            v = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            row_data.append(v)
        maps.append(row_data)

    return {"width": width, "height": height, "name": name, "maps": maps}


def parse_map_collision(data: bytes) -> list[list[tuple[int, int]]] | None:
    """Parse map binary, return 32x32 grid of (type, collision) or None."""
    if len(data) < 16:
        return None
    perms_len = struct.unpack_from("<I", data, 0)[0]
    if perms_len != MAP_SIZE * MAP_SIZE * 2:
        return None

    pos = 16
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
                row_data.append((0, 0x80))
            else:
                row_data.append((data[idx], data[idx + 1]))
        grid.append(row_data)
    return grid


def find_playable_bounds(grid: list[list[tuple[int, int]]]) -> tuple[int, int, int, int]:
    """Find the bounding box of non-empty content in a collision grid.

    Scans for the tightest rectangle containing all blocked (0x80) and special
    tiles, then expands by 1 in each direction. This filters out large empty
    walkable regions outside the actual map geometry (common in indoor maps
    where the 32x32 grid is larger than the room).
    """
    min_x, min_y, max_x, max_y = MAP_SIZE, MAP_SIZE, 0, 0
    has_structure = False
    for y, row in enumerate(grid):
        for x, (_, c) in enumerate(row):
            if c != 0x00:
                has_structure = True
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if not has_structure:
        return (0, 0, MAP_SIZE - 1, MAP_SIZE - 1)

    min_x = max(0, min_x - 1)
    min_y = max(0, min_y - 1)
    max_x = min(MAP_SIZE - 1, max_x + 1)
    max_y = min(MAP_SIZE - 1, max_y + 1)
    return (min_x, min_y, max_x, max_y)


def load_existing_event_positions(event_file: str) -> set[tuple[int, int, int, int]]:
    """Load positions of existing overworlds and spawnables for a given event file."""
    occupied: set[tuple[int, int, int, int]] = set()
    ef_key = event_file.lstrip("0") or "0"
    ef_padded = event_file.zfill(4)

    for csv_path in (OVERWORLDS_CSV, SPAWNABLES_CSV):
        if not csv_path.exists():
            continue
        with csv_path.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                ef = row.get("event_file", "")
                if ef != ef_padded and ef.lstrip("0") != ef_key:
                    continue
                try:
                    pos = (
                        int(row.get("x_map", 0)),
                        int(row.get("y_map", 0)),
                        int(row.get("x_matrix", 0)),
                        int(row.get("y_matrix", 0)),
                    )
                    occupied.add(pos)
                except (ValueError, KeyError):
                    pass
    return occupied


def suggest_placements(
    grid: list[list[tuple[int, int]]],
    mx: int,
    my: int,
    occupied: set[tuple[int, int, int, int]],
    is_overworld_matrix: bool,
    count: int = 10,
) -> list[dict]:
    """Suggest walkable tiles suitable for placing a new event.

    Prefers tiles that are:
    - Walkable (collision == 0x00)
    - Inside the playable bounding box (for indoor maps)
    - Not already occupied by an existing event
    - At least 1 tile from any wall/blocked tile (so the NPC isn't flush against a wall)
    """
    bounds = find_playable_bounds(grid) if not is_overworld_matrix else (0, 0, 31, 31)
    bx0, by0, bx1, by1 = bounds

    candidates: list[tuple[int, int, int]] = []
    for y in range(by0, by1 + 1):
        for x in range(bx0, bx1 + 1):
            _, c = grid[y][x]
            if c != 0x00:
                continue
            if (x, y, mx, my) in occupied:
                continue

            wall_dist = MAP_SIZE
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < MAP_SIZE and 0 <= nx < MAP_SIZE:
                        _, nc = grid[ny][nx]
                        if nc == 0x80:
                            d = abs(dx) + abs(dy)
                            wall_dist = min(wall_dist, d)

            if wall_dist >= 2:
                candidates.append((wall_dist, x, y))

    candidates.sort(key=lambda t: (-t[0], t[1], t[2]))

    results = []
    for _, x, y in candidates[:count]:
        results.append({
            "x_map": x, "y_map": y,
            "x_matrix": mx, "y_matrix": my,
        })
    return results


def process_grid(
    grid: list[list[tuple[int, int]]],
    map_id: int,
    mx: int,
    my: int,
    args,
    event_file: str | None,
    is_overworld: bool,
) -> None:
    """Process and display a single map grid."""
    w = sum(1 for r in grid for _, c in r if c == 0x00)
    b = sum(1 for r in grid for _, c in r if c == 0x80)
    s = 1024 - w - b
    print(f"  Map [{my},{mx}] = {map_id}: walkable={w}, blocked={b}, special={s}")

    if args.visual or args.suggest_placement:
        occupied = set()
        if event_file:
            occupied = load_existing_event_positions(event_file)

        bounds = find_playable_bounds(grid) if not is_overworld else (0, 0, 31, 31)
        bx0, by0, bx1, by1 = bounds

        if args.suggest_placement:
            suggestions = suggest_placements(grid, mx, my, occupied, is_overworld)
            suggestion_set = {(s["x_map"], s["y_map"]) for s in suggestions}
        else:
            suggestions = []
            suggestion_set = set()

        occupied_local = {(p[0], p[1]) for p in occupied if p[2] == mx and p[3] == my}

        if args.visual:
            print(f"  Grid for map {map_id} (matrix pos [{my},{mx}]):")
            if not is_overworld:
                print(f"  Playable bounds: x=[{bx0}..{bx1}], y=[{by0}..{by1}]")
            print("  Legend: . walkable  # blocked  ? special  @ existing_event  * suggested")
            for y, gr in enumerate(grid):
                line = "    "
                for x, (_, c) in enumerate(gr):
                    if (x, y) in suggestion_set:
                        line += "*"
                    elif (x, y) in occupied_local:
                        line += "@"
                    elif c == 0x00:
                        line += "."
                    elif c == 0x80:
                        line += "#"
                    else:
                        line += "?"
                print(line)

        if args.suggest_placement:
            ef_display = event_file.zfill(4) if event_file else "?"
            print(f"\n  Suggested placement positions for event file {ef_display}:")
            print(f"  (Avoiding {len(occupied_local)} existing event position(s))")
            for i, s in enumerate(suggestions, 1):
                print(f"    {i}. x_map={s['x_map']}, y_map={s['y_map']}, "
                      f"x_matrix={s['x_matrix']}, y_matrix={s['y_matrix']}")
            if not suggestions:
                print("    (No suitable positions found in this map tile)")

    if args.walkable:
        bounds = find_playable_bounds(grid) if not is_overworld else (0, 0, 31, 31)
        bx0, by0, bx1, by1 = bounds
        for y in range(by0, by1 + 1):
            for x in range(bx0, bx1 + 1):
                _, c = grid[y][x]
                if c == 0x00:
                    print(f"    walkable: x_map={x}, y_map={y}, x_matrix={mx}, y_matrix={my}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Map lookup: event -> header -> matrix -> collision.")
    parser.add_argument("--event", metavar="NNNN", help="Event file number.")
    parser.add_argument("--header", metavar="N", help="Header number directly.")
    parser.add_argument("--visual", action="store_true", help="Show collision grid ASCII art.")
    parser.add_argument("--walkable", action="store_true", help="List all walkable positions.")
    parser.add_argument("--matrix-pos", metavar="ROW,COL",
                        help="For large matrices, drill into specific cell [row,col].")
    parser.add_argument("--suggest-placement", action="store_true",
                        help="Suggest safe positions for new events, avoiding collisions and existing events.")
    args = parser.parse_args()

    if not args.event and not args.header:
        parser.print_help()
        sys.exit(1)

    all_headers = load_header_data()

    if args.event:
        matched = find_headers_for_event(all_headers, args.event)
        if not matched:
            print(f"[ERROR] No header found for event file {args.event}", file=sys.stderr)
            sys.exit(1)
    else:
        matched = [h for h in all_headers if h.get("HEADER #", "").strip() == args.header]
        if not matched:
            print(f"[ERROR] Header {args.header} not found.", file=sys.stderr)
            sys.exit(1)

    target_mpos = None
    if args.matrix_pos:
        parts = args.matrix_pos.split(",")
        if len(parts) == 2:
            target_mpos = (int(parts[0]), int(parts[1]))

    for hdr in matched:
        hdr_num = hdr.get("HEADER #", "").strip()
        name = hdr.get("Internal Name", "").strip()
        matrix_id = hdr.get("Matrix", "").strip()
        event_file = hdr.get("Event File", "").strip()

        print(f"Header {hdr_num}: {name}")
        print(f"  Event File: {event_file}, Matrix: {matrix_id}")

        try:
            mid = str(int(float(matrix_id))).zfill(4)
        except ValueError:
            print(f"  [WARN] Invalid matrix ID: {matrix_id}")
            continue

        matrix_path = UNPACKED_MATRICES / mid
        if not matrix_path.exists():
            print(f"  [WARN] Matrix file not found: {matrix_path}")
            continue

        mat = parse_matrix(matrix_path.read_bytes())
        print(f"  Matrix: {mat['name']} ({mat['width']}x{mat['height']})")

        unique_maps = set()
        for row in mat["maps"]:
            for m in row:
                if m != MATRIX_EMPTY:
                    unique_maps.add(m)

        print(f"  Unique map tiles: {len(unique_maps)}")

        is_large = mat["width"] > 3 or mat["height"] > 3

        if target_mpos and is_large:
            trow, tcol = target_mpos
            if trow < mat["height"] and tcol < mat["width"]:
                map_id = mat["maps"][trow][tcol]
                if map_id == MATRIX_EMPTY:
                    print(f"  Matrix cell [{trow},{tcol}] is empty (0xFFFF)")
                    continue
                map_path = UNPACKED_MAPS / str(map_id).zfill(4)
                if not map_path.exists():
                    print(f"  Map [{trow},{tcol}] = {map_id} (file missing)")
                    continue
                grid = parse_map_collision(map_path.read_bytes())
                if not grid:
                    print(f"  Map [{trow},{tcol}] = {map_id} (parse error)")
                    continue
                process_grid(grid, map_id, tcol, trow, args, event_file, True)
            else:
                print(f"  [ERROR] Matrix position [{trow},{tcol}] out of bounds "
                      f"(matrix is {mat['height']}x{mat['width']})")
            continue

        if not is_large:
            for my, row in enumerate(mat["maps"]):
                for mx, map_id in enumerate(row):
                    if map_id == MATRIX_EMPTY:
                        continue
                    map_path = UNPACKED_MAPS / str(map_id).zfill(4)
                    if not map_path.exists():
                        print(f"  Map [{my},{mx}] = {map_id} (file missing)")
                        continue
                    grid = parse_map_collision(map_path.read_bytes())
                    if not grid:
                        print(f"  Map [{my},{mx}] = {map_id} (parse error)")
                        continue
                    process_grid(grid, map_id, mx, my, args, event_file, False)
        else:
            print(f"  (Large matrix - use --matrix-pos ROW,COL to drill into a cell)")
            if args.walkable or args.visual or args.suggest_placement:
                print(f"  Example cells with maps (first 10):")
                count = 0
                for my, row in enumerate(mat["maps"]):
                    for mx, map_id in enumerate(row):
                        if map_id != MATRIX_EMPTY and count < 10:
                            print(f"    [{my},{mx}] = map {map_id}")
                            count += 1


if __name__ == "__main__":
    main()

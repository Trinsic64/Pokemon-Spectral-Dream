#!/usr/bin/env python3
"""
map_lookup.py

Resolves the full chain: event_file -> header -> matrix -> map file numbers
-> collision data. Tells an AI which tiles are walkable for a given event file.

Usage:
    python tools/map_lookup.py --event 0057                # show map info for event 0057
    python tools/map_lookup.py --event 0057 --visual       # show collision grids
    python tools/map_lookup.py --event 0057 --walkable     # list all walkable (x_map, y_map, x_matrix, y_matrix)
    python tools/map_lookup.py --header 10                  # look up by header number

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Map lookup: event -> header -> matrix -> collision.")
    parser.add_argument("--event", metavar="NNNN", help="Event file number.")
    parser.add_argument("--header", metavar="N", help="Header number directly.")
    parser.add_argument("--visual", action="store_true", help="Show collision grid ASCII art.")
    parser.add_argument("--walkable", action="store_true", help="List all walkable positions.")
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

        if mat["width"] <= 3 and mat["height"] <= 3:
            # Small matrix - show all grids
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
                    w = sum(1 for r in grid for _, c in r if c == 0x00)
                    b = sum(1 for r in grid for _, c in r if c == 0x80)
                    s = 1024 - w - b
                    print(f"  Map [{my},{mx}] = {map_id}: walkable={w}, blocked={b}, special={s}")

                    if args.visual:
                        print(f"  Grid for map {map_id} (matrix pos [{my},{mx}]):")
                        for gr in grid:
                            line = "    "
                            for _, c in gr:
                                line += "." if c == 0x00 else "#" if c == 0x80 else "?"
                            print(line)

                    if args.walkable:
                        for y, gr in enumerate(grid):
                            for x, (_, c) in enumerate(gr):
                                if c == 0x00:
                                    print(f"    walkable: x_map={x}, y_map={y}, x_matrix={mx}, y_matrix={my}")
        else:
            # Large matrix (overworld) - just report which matrix cells have maps
            print(f"  (Large matrix - use --header for specific indoor maps)")
            if args.walkable or args.visual:
                print(f"  For overworld maps, specify a target matrix position.")
                print(f"  Example cells with maps (first 10):")
                count = 0
                for my, row in enumerate(mat["maps"]):
                    for mx, map_id in enumerate(row):
                        if map_id != MATRIX_EMPTY and count < 10:
                            print(f"    [{my},{mx}] = map {map_id}")
                            count += 1


if __name__ == "__main__":
    main()

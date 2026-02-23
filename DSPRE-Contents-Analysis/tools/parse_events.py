#!/usr/bin/env python3
"""
parse_events.py

Parses all binary event files in events/raw/ (or unpacked/eventFiles/ as
fallback) and outputs structured CSV data.

Binary format ported directly from DSPRE's EventFile.cs (little-endian):

  [uint32 spawnable_count]
  [spawnable_count × 20 bytes each]
    u16 scriptNumber
    u16 type          (0=MISC, 1=BOARD, 2=HIDDENITEM)
    i16 xPos          (decompose: xMap=pos%32, xMatrix=pos//32)
    u16 unknown2
    i16 yPos          (decompose: yMap=pos%32, yMatrix=pos//32)
    i32 zPos          (fixed point)
    u16 unknown4
    u16 dir
    u16 unknown5

  [uint32 overworld_count]
  [overworld_count × 32 bytes each]
    u16 owID
    u16 overlayTableEntry
    u16 movement
    u16 type          (0=NORMAL, 1=TRAINER, 3=ITEM)
    u16 flag
    u16 scriptNumber  (0xFFFF = alias of another OW)
    u16 orientation
    u16 sightRange
    u16 unknown1
    u16 unknown2
    u16 xRange
    u16 yRange
    i16 xPos          (decompose: xMap=pos%32, xMatrix=pos//32)
    i16 yPos          (decompose: yMap=pos%32, yMatrix=pos//32)
    i32 zPos

  [uint32 warp_count]
  [warp_count × 12 bytes each]
    i16 xPos
    i16 yPos
    u16 header        (destination map header number)
    u16 anchor        (destination warp anchor ID)
    u32 height

  [uint32 trigger_count]
  [trigger_count × 16 bytes each]
    u16 scriptNumber
    i16 xPos
    i16 yPos
    u16 widthX
    u16 heightY
    u16 zPos
    u16 expectedVarValue
    u16 variableWatched

MAP_SIZE = 32 (used for coordinate decomposition)

Standard-library only.
"""

from __future__ import annotations

import csv
import struct
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

EVENTS_RAW_DIR  = ANALYSIS_ROOT / "events" / "raw"
UNPACKED_EVENTS = ANALYSIS_ROOT / "unpacked" / "eventFiles"
EVENTS_DIR      = ANALYSIS_ROOT / "events"
CONSTANTS_DIR   = ANALYSIS_ROOT / "constants"
HEADER_CSV      = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"

MAP_SIZE = 32


# ---------------------------------------------------------------------------
# Cross-reference helpers
# ---------------------------------------------------------------------------

def load_header_event_map(header_csv: Path) -> dict[str, list[str]]:
    """Return {event_file_num_str (zero-padded 4): [Internal Name, ...]}."""
    mapping: dict[str, list[str]] = defaultdict(list)
    if not header_csv.exists():
        return mapping
    with header_csv.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ev_ref  = row.get("Event File", "").strip()
            name    = row.get("Internal Name", "").strip()
            hdr_num = row.get("HEADER #", "").strip()
            if ev_ref and name:
                try:
                    key = str(int(ev_ref)).zfill(4)
                except ValueError:
                    key = ev_ref
                mapping[key].append(f"{name}(H{hdr_num})")
    return mapping


def load_header_name_by_num(header_csv: Path) -> dict[str, str]:
    """Return {header_num_str: Internal Name} for warp destination lookups."""
    mapping: dict[str, str] = {}
    if not header_csv.exists():
        return mapping
    with header_csv.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            hdr_num = row.get("HEADER #", "").strip()
            name    = row.get("Internal Name", "").strip()
            if hdr_num and name:
                mapping[hdr_num] = name
    return mapping


# ---------------------------------------------------------------------------
# Binary parsing
# ---------------------------------------------------------------------------

def decompose(pos: int) -> tuple[int, int]:
    """Split a raw position into (map_pos, matrix_pos)."""
    # Use signed interpretation for the position
    if pos < 0:
        # Python keeps the sign; just decompose the absolute then re-apply
        map_pos    = pos % MAP_SIZE
        matrix_pos = pos // MAP_SIZE
    else:
        map_pos    = pos % MAP_SIZE
        matrix_pos = pos // MAP_SIZE
    return map_pos, matrix_pos


def parse_event_file(data: bytes) -> dict:
    """Parse a binary event file. Returns dict with four lists."""
    result = {"spawnables": [], "overworlds": [], "warps": [], "triggers": []}
    pos = 0

    def ru32() -> int:
        nonlocal pos
        v = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return v

    def ri16() -> int:
        nonlocal pos
        v = struct.unpack_from("<h", data, pos)[0]
        pos += 2
        return v

    def ru16() -> int:
        nonlocal pos
        v = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        return v

    def ri32() -> int:
        nonlocal pos
        v = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        return v

    # ---- Spawnables ----
    count = ru32()
    for _ in range(count):
        script_num = ru16()
        sp_type    = ru16()
        x_raw      = ri16()
        unk2       = ru16()
        y_raw      = ri16()
        z_pos      = ri32()
        unk4       = ru16()
        direction  = ru16()
        unk5       = ru16()
        x_map, x_mat = decompose(x_raw)
        y_map, y_mat = decompose(y_raw)
        type_name = {0: "MISC", 1: "BOARD", 2: "HIDDENITEM"}.get(sp_type, str(sp_type))
        result["spawnables"].append({
            "script": script_num,
            "type":   type_name,
            "dir":    direction,
            "x_map": x_map, "x_matrix": x_mat,
            "y_map": y_map, "y_matrix": y_mat,
            "z":     z_pos,
        })

    # ---- Overworlds ----
    count = ru32()
    for _ in range(count):
        ow_id       = ru16()
        overlay_ent = ru16()
        movement    = ru16()
        ow_type     = ru16()
        flag        = ru16()
        script_num  = ru16()
        orientation = ru16()
        sight_range = ru16()
        unk1        = ru16()
        unk2        = ru16()
        x_range     = ru16()
        y_range     = ru16()
        x_raw       = ri16()
        y_raw       = ri16()
        z_pos       = ri32()
        x_map, x_mat = decompose(x_raw)
        y_map, y_mat = decompose(y_raw)
        type_name = {0: "NORMAL", 1: "TRAINER", 3: "ITEM"}.get(ow_type, str(ow_type))
        is_alias = (script_num == 0xFFFF)
        result["overworlds"].append({
            "ow_id":        ow_id,
            "overlay_entry": overlay_ent,
            "movement":     movement,
            "type":         type_name,
            "flag":         f"0x{flag:04X}",
            "script":       "ALIAS" if is_alias else script_num,
            "orientation":  orientation,
            "sight_range":  sight_range,
            "x_range":      x_range,
            "y_range":      y_range,
            "x_map": x_map, "x_matrix": x_mat,
            "y_map": y_map, "y_matrix": y_mat,
            "z":     z_pos,
        })

    # ---- Warps ----
    count = ru32()
    for _ in range(count):
        x_raw   = ri16()
        y_raw   = ri16()
        header  = ru16()
        anchor  = ru16()
        height  = ru32()
        x_map, x_mat = decompose(x_raw)
        y_map, y_mat = decompose(y_raw)
        result["warps"].append({
            "dest_header": header,
            "anchor":      anchor,
            "height":      height,
            "x_map": x_map, "x_matrix": x_mat,
            "y_map": y_map, "y_matrix": y_mat,
        })

    # ---- Triggers ----
    count = ru32()
    for _ in range(count):
        script_num    = ru16()
        x_raw         = ri16()
        y_raw         = ri16()
        width_x       = ru16()
        height_y      = ru16()
        z_pos         = ru16()
        expected_val  = ru16()
        var_watched   = ru16()
        x_map, x_mat = decompose(x_raw)
        y_map, y_mat = decompose(y_raw)
        result["triggers"].append({
            "script":       script_num,
            "var_watched":  f"0x{var_watched:04X}" if var_watched else "0",
            "expected_val": expected_val,
            "width":        width_x,
            "height":       height_y,
            "z":            z_pos,
            "x_map": x_map, "x_matrix": x_mat,
            "y_map": y_map, "y_matrix": y_mat,
        })

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

    # Choose source directory
    src_dir = EVENTS_RAW_DIR if EVENTS_RAW_DIR.exists() and any(EVENTS_RAW_DIR.iterdir()) \
              else UNPACKED_EVENTS
    if not src_dir.exists():
        print(f"[ERROR] No event files found (checked events/raw/ and unpacked/eventFiles/).")
        return

    print(f"Reading event files from: {src_dir.relative_to(ANALYSIS_ROOT)}")

    event_to_maps    = load_header_event_map(HEADER_CSV)
    header_name_map  = load_header_name_by_num(HEADER_CSV)

    event_files = sorted(f for f in src_dir.iterdir() if f.is_file())
    print(f"Found {len(event_files)} event files.")

    summary_rows:     list[dict] = []
    overworld_rows:   list[dict] = []
    warp_rows:        list[dict] = []
    spawnable_rows:   list[dict] = []
    trigger_rows:     list[dict] = []

    for ef in event_files:
        file_num = ef.stem  # e.g. "0057"
        maps_str = "; ".join(event_to_maps.get(file_num, []))

        try:
            data = ef.read_bytes()
            parsed = parse_event_file(data)
        except Exception as exc:
            print(f"  [WARN] Could not parse {file_num}: {exc}")
            continue

        sp  = parsed["spawnables"]
        ow  = parsed["overworlds"]
        wp  = parsed["warps"]
        tr  = parsed["triggers"]

        summary_rows.append({
            "event_file":       file_num,
            "maps":             maps_str,
            "spawnable_count":  len(sp),
            "overworld_count":  len(ow),
            "warp_count":       len(wp),
            "trigger_count":    len(tr),
            "file_size_bytes":  len(data),
        })

        # Spawnables
        for i, s in enumerate(sp):
            spawnable_rows.append({
                "event_file": file_num,
                "maps":       maps_str,
                "index":      i,
                "type":       s["type"],
                "script":     s["script"],
                "dir":        s["dir"],
                "x_map":      s["x_map"],
                "x_matrix":   s["x_matrix"],
                "y_map":      s["y_map"],
                "y_matrix":   s["y_matrix"],
                "z":          s["z"],
            })

        # Overworlds
        for i, o in enumerate(ow):
            overworld_rows.append({
                "event_file":    file_num,
                "maps":          maps_str,
                "index":         i,
                "ow_id":         o["ow_id"],
                "overlay_entry": o["overlay_entry"],
                "type":          o["type"],
                "movement":      o["movement"],
                "flag":          o["flag"],
                "script":        o["script"],
                "orientation":   o["orientation"],
                "sight_range":   o["sight_range"],
                "x_range":       o["x_range"],
                "y_range":       o["y_range"],
                "x_map":         o["x_map"],
                "x_matrix":      o["x_matrix"],
                "y_map":         o["y_map"],
                "y_matrix":      o["y_matrix"],
                "z":             o["z"],
            })

        # Warps
        for i, w in enumerate(wp):
            dest_header  = w["dest_header"]
            dest_map_name = header_name_map.get(str(dest_header), "")
            warp_rows.append({
                "event_file":    file_num,
                "maps":          maps_str,
                "index":         i,
                "dest_header":   dest_header,
                "dest_map_name": dest_map_name,
                "anchor":        w["anchor"],
                "height":        w["height"],
                "x_map":         w["x_map"],
                "x_matrix":      w["x_matrix"],
                "y_map":         w["y_map"],
                "y_matrix":      w["y_matrix"],
            })

        # Triggers
        for i, t in enumerate(tr):
            trigger_rows.append({
                "event_file":   file_num,
                "maps":         maps_str,
                "index":        i,
                "script":       t["script"],
                "var_watched":  t["var_watched"],
                "expected_val": t["expected_val"],
                "width":        t["width"],
                "height":       t["height"],
                "z":            t["z"],
                "x_map":        t["x_map"],
                "x_matrix":     t["x_matrix"],
                "y_map":        t["y_map"],
                "y_matrix":     t["y_matrix"],
            })

    def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(EVENTS_DIR / "events-summary.csv", summary_rows, [
        "event_file", "maps", "spawnable_count", "overworld_count",
        "warp_count", "trigger_count", "file_size_bytes",
    ])
    print(f"  -> events/events-summary.csv  ({len(summary_rows)} rows)")

    write_csv(EVENTS_DIR / "spawnables.csv", spawnable_rows, [
        "event_file", "maps", "index", "type", "script", "dir",
        "x_map", "x_matrix", "y_map", "y_matrix", "z",
    ])
    print(f"  -> events/spawnables.csv  ({len(spawnable_rows)} rows)")

    write_csv(EVENTS_DIR / "overworlds.csv", overworld_rows, [
        "event_file", "maps", "index", "ow_id", "overlay_entry", "type",
        "movement", "flag", "script", "orientation", "sight_range",
        "x_range", "y_range", "x_map", "x_matrix", "y_map", "y_matrix", "z",
    ])
    print(f"  -> events/overworlds.csv  ({len(overworld_rows)} rows)")

    write_csv(EVENTS_DIR / "warps.csv", warp_rows, [
        "event_file", "maps", "index", "dest_header", "dest_map_name",
        "anchor", "height", "x_map", "x_matrix", "y_map", "y_matrix",
    ])
    print(f"  -> events/warps.csv  ({len(warp_rows)} rows)")

    write_csv(EVENTS_DIR / "triggers.csv", trigger_rows, [
        "event_file", "maps", "index", "script", "var_watched",
        "expected_val", "width", "height", "z",
        "x_map", "x_matrix", "y_map", "y_matrix",
    ])
    print(f"  -> events/triggers.csv  ({len(trigger_rows)} rows)")

    # Summary stats
    total_ow   = sum(r["overworld_count"]  for r in summary_rows)
    total_wp   = sum(r["warp_count"]       for r in summary_rows)
    total_sp   = sum(r["spawnable_count"]  for r in summary_rows)
    total_tr   = sum(r["trigger_count"]    for r in summary_rows)
    mapped     = sum(1 for r in summary_rows if r["maps"])
    print()
    print(f"Totals across {len(summary_rows)} event files:")
    print(f"  Overworlds (NPCs) : {total_ow:,}")
    print(f"  Warps             : {total_wp:,}")
    print(f"  Spawnables        : {total_sp:,}")
    print(f"  Triggers          : {total_tr:,}")
    print(f"  Event files with known map: {mapped}/{len(summary_rows)}")
    print("\nDone.")


if __name__ == "__main__":
    main()

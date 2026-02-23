#!/usr/bin/env python3
"""
serialize_events.py

Reads edited event CSVs and writes binary event files to events/edited/ in the
exact EventFile.cs ToByteArray() format.

Usage:
    python tools/serialize_events.py              # serialize all event files
    python tools/serialize_events.py --event 0057 # serialize only event 0057
    python tools/serialize_events.py --validate   # also round-trip validate

The CSVs are the edit surface. Modify values (e.g. overlay_entry) in the CSV,
then run this script to produce the patched binary for copying to a duplicate ROM.

Unknown fields (unknown1/unknown2 in Overworlds; unknown2/4/5 in Spawnables)
are preserved from the original raw binary when available, otherwise defaulted
to zero. This guarantees a lossless round-trip for all known fields.

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
from collections import defaultdict
from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

EVENTS_CSV_DIR  = ANALYSIS_ROOT / "events"
EVENTS_RAW_DIR  = ANALYSIS_ROOT / "events" / "raw"
UNPACKED_EVENTS = ANALYSIS_ROOT / "unpacked" / "eventFiles"
EVENTS_EDITED   = ANALYSIS_ROOT / "events" / "edited"

MAP_SIZE = 32  # MapFile.mapSize in DSPRE


# ---------------------------------------------------------------------------
# Type-field mappings (string <-> int)
# ---------------------------------------------------------------------------

SPAWNABLE_TYPE = {"MISC": 0, "BOARD": 1, "HIDDENITEM": 2}
OVERWORLD_TYPE = {"NORMAL": 0, "TRAINER": 1, "ITEM": 3}

SCRIPT_ALIAS = 0xFFFF


# ---------------------------------------------------------------------------
# Preserve unknown fields from original raw binary
# ---------------------------------------------------------------------------

def read_raw_unknowns(data: bytes) -> dict:
    """
    Parse the raw binary event file and return preserved unknown fields.

    Returns:
        {
            "spawnable_unks": list of (unk2: int, unk4: int, unk5: int),
            "overworld_unks": list of (unk1: int, unk2: int),
        }
    """
    result = {"spawnable_unks": [], "overworld_unks": []}
    pos = 0

    def ru32():
        nonlocal pos
        v = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return v

    def ri16():
        nonlocal pos
        v = struct.unpack_from("<h", data, pos)[0]
        pos += 2
        return v

    def ru16():
        nonlocal pos
        v = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        return v

    def ri32():
        nonlocal pos
        v = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        return v

    try:
        # Spawnables
        count = ru32()
        for _ in range(count):
            ru16()          # script
            ru16()          # type
            ri16()          # x
            unk2 = ru16()   # unknown2
            ri16()          # y
            ri32()          # z
            unk4 = ru16()   # unknown4
            ru16()          # dir
            unk5 = ru16()   # unknown5
            result["spawnable_unks"].append((unk2, unk4, unk5))

        # Overworlds
        count = ru32()
        for _ in range(count):
            ru16()          # ow_id
            ru16()          # overlay_entry
            ru16()          # movement
            ru16()          # type
            ru16()          # flag
            ru16()          # script
            ru16()          # orientation
            ru16()          # sight_range
            unk1 = ru16()   # unknown1
            unk2 = ru16()   # unknown2
            ru16()          # x_range
            ru16()          # y_range
            ri16()          # x
            ri16()          # y
            ri32()          # z
            result["overworld_unks"].append((unk1, unk2))

    except struct.error:
        pass  # File smaller than expected — unknowns may be incomplete

    return result


# ---------------------------------------------------------------------------
# Binary serializers (exact mirror of EventFile.cs ToByteArray())
# ---------------------------------------------------------------------------

def pack_spawnable(row: dict, unk2: int = 0, unk4: int = 0, unk5: int = 0) -> bytes:
    """Serialize one Spawnable row to 20 bytes."""
    t = str(row["type"])
    sp_type = SPAWNABLE_TYPE[t] if t in SPAWNABLE_TYPE else int(t)
    script  = int(row["script"])
    x_coord = int(row["x_map"]) + MAP_SIZE * int(row["x_matrix"])
    y_coord = int(row["y_map"]) + MAP_SIZE * int(row["y_matrix"])
    z       = int(row["z"])
    direction = int(row["dir"])

    return struct.pack(
        "<HHhHhiHHH",
        script,          # u16 scriptNumber
        sp_type,         # u16 type
        x_coord,         # i16 xCoordinate
        unk2,            # u16 unknown2
        y_coord,         # i16 yCoordinate
        z,               # i32 zPosition
        unk4,            # u16 unknown4
        direction,       # u16 dir
        unk5,            # u16 unknown5
    )  # 2+2+2+2+2+4+2+2+2 = 20 bytes


def pack_overworld(row: dict, unk1: int = 0, unk2: int = 0) -> bytes:
    """Serialize one Overworld row to 32 bytes."""
    ow_id         = int(row["ow_id"])
    overlay_entry = int(row["overlay_entry"])
    movement      = int(row["movement"])
    t = str(row["type"])
    ow_type       = OVERWORLD_TYPE[t] if t in OVERWORLD_TYPE else int(t)
    flag          = int(str(row["flag"]), 16) if str(row["flag"]).startswith("0x") else int(row["flag"])
    script_raw    = row["script"]
    script        = SCRIPT_ALIAS if str(script_raw).strip().upper() == "ALIAS" else int(script_raw)
    orientation   = int(row["orientation"])
    sight_range   = int(row["sight_range"])
    x_range       = int(row["x_range"])
    y_range       = int(row["y_range"])
    x_coord       = int(row["x_map"]) + MAP_SIZE * int(row["x_matrix"])
    y_coord       = int(row["y_map"]) + MAP_SIZE * int(row["y_matrix"])
    z             = int(row["z"])

    return struct.pack(
        "<HHHHHHHHHHHHhhi",
        ow_id,           # u16 owID
        overlay_entry,   # u16 overlayTableEntry
        movement,        # u16 movement
        ow_type,         # u16 type
        flag,            # u16 flag
        script,          # u16 scriptNumber
        orientation,     # u16 orientation
        sight_range,     # u16 sightRange
        unk1,            # u16 unknown1
        unk2,            # u16 unknown2
        x_range,         # u16 xRange
        y_range,         # u16 yRange
        x_coord,         # i16 xCoordinate
        y_coord,         # i16 yCoordinate
        z,               # i32 zPosition (EventFile.cs: int zPosition, writer.Write(int))
    )  # 12×2 + 2 + 2 + 4 = 32 bytes ✓


def pack_warp(row: dict) -> bytes:
    """Serialize one Warp row to 12 bytes."""
    x_coord = int(row["x_map"]) + MAP_SIZE * int(row["x_matrix"])
    y_coord = int(row["y_map"]) + MAP_SIZE * int(row["y_matrix"])
    header  = int(row["dest_header"])
    anchor  = int(row["anchor"])
    height  = int(row["height"])

    # EventFile.cs writes: ushort x, ushort y, ushort header, ushort anchor, uint32 height
    return struct.pack(
        "<HHHHI",
        x_coord & 0xFFFF,  # u16 xCoordinate
        y_coord & 0xFFFF,  # u16 yCoordinate
        header,            # u16 header
        anchor,            # u16 anchor
        height,            # u32 height
    )  # 2+2+2+2+4 = 12 bytes ✓


def pack_trigger(row: dict) -> bytes:
    """Serialize one Trigger row to 16 bytes."""
    script   = int(row["script"])
    x_coord  = int(row["x_map"]) + MAP_SIZE * int(row["x_matrix"])
    y_coord  = int(row["y_map"]) + MAP_SIZE * int(row["y_matrix"])
    width_x  = int(row["width"])
    height_y = int(row["height"])
    z        = int(row["z"])
    expected = int(row["expected_val"])
    var_w_raw = str(row["var_watched"])
    var_w    = int(var_w_raw, 16) if var_w_raw.startswith("0x") else int(var_w_raw)

    # EventFile.cs writes: u16 script, u16 x, u16 y, u16 widthX, u16 heightY,
    #                       u16 zPos, u16 expectedVarValue, u16 variableWatched
    return struct.pack(
        "<HHHHHHHH",
        script,            # u16 scriptNumber
        x_coord & 0xFFFF,  # u16 xCoordinate
        y_coord & 0xFFFF,  # u16 yCoordinate
        width_x,           # u16 widthX
        height_y,          # u16 heightY
        z,                 # u16 zPosition
        expected,          # u16 expectedVarValue
        var_w,             # u16 variableWatched
    )  # 2*8 = 16 bytes ✓


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------

def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def group_by_event(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        grouped[r["event_file"]].append(r)
    return grouped


# ---------------------------------------------------------------------------
# Round-trip validation helper
# ---------------------------------------------------------------------------

def count_entities(data: bytes) -> tuple[int, int, int, int]:
    """Return (spawnable_count, overworld_count, warp_count, trigger_count)."""
    pos = 0

    def ru32():
        nonlocal pos
        v = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        return v

    sp  = ru32(); pos += sp  * 20
    ow  = ru32(); pos += ow  * 32
    wp  = ru32(); pos += wp  * 12
    tr  = ru32(); pos += tr  * 16
    return sp, ow, wp, tr


# ---------------------------------------------------------------------------
# Raw binary locator
# ---------------------------------------------------------------------------

def find_raw(file_num: str) -> Path | None:
    """Locate the original raw binary for a given event file number."""
    for src in (EVENTS_RAW_DIR, UNPACKED_EVENTS):
        candidate = src / file_num
        if candidate.exists():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Core serialization
# ---------------------------------------------------------------------------

def serialize_event_file(
    file_num: str,
    sp_rows:   list[dict],
    ow_rows:   list[dict],
    warp_rows: list[dict],
    trig_rows: list[dict],
) -> bytes:
    """Build and return the binary event file."""

    # Preserve unknown fields from the original raw binary
    raw_path = find_raw(file_num)
    unks: dict = {"spawnable_unks": [], "overworld_unks": []}
    if raw_path:
        unks = read_raw_unknowns(raw_path.read_bytes())

    sp_unks  = unks["spawnable_unks"]
    ow_unks  = unks["overworld_unks"]

    buf = bytearray()

    # Spawnables
    buf += struct.pack("<I", len(sp_rows))
    for i, row in enumerate(sp_rows):
        u2, u4, u5 = sp_unks[i] if i < len(sp_unks) else (0, 0, 0)
        buf += pack_spawnable(row, unk2=u2, unk4=u4, unk5=u5)

    # Overworlds
    buf += struct.pack("<I", len(ow_rows))
    for i, row in enumerate(ow_rows):
        u1, u2 = ow_unks[i] if i < len(ow_unks) else (0, 0)
        buf += pack_overworld(row, unk1=u1, unk2=u2)

    # Warps
    buf += struct.pack("<I", len(warp_rows))
    for row in warp_rows:
        buf += pack_warp(row)

    # Triggers
    buf += struct.pack("<I", len(trig_rows))
    for row in trig_rows:
        buf += pack_trigger(row)

    return bytes(buf)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Serialize event CSVs to binary event files.")
    parser.add_argument("--event", metavar="NNNN",
                        help="Only serialize this event file number (e.g. 0057).")
    parser.add_argument("--validate", action="store_true",
                        help="After writing, re-parse and compare entity counts with the original.")
    args = parser.parse_args()

    # Load all CSVs
    sp_rows   = load_csv(EVENTS_CSV_DIR / "spawnables.csv")
    ow_rows   = load_csv(EVENTS_CSV_DIR / "overworlds.csv")
    warp_rows = load_csv(EVENTS_CSV_DIR / "warps.csv")
    trig_rows = load_csv(EVENTS_CSV_DIR / "triggers.csv")

    sp_by_ev   = group_by_event(sp_rows)
    ow_by_ev   = group_by_event(ow_rows)
    warp_by_ev = group_by_event(warp_rows)
    trig_by_ev = group_by_event(trig_rows)

    # Determine which event files to process
    all_event_nums = sorted(
        set(sp_by_ev) | set(ow_by_ev) | set(warp_by_ev) | set(trig_by_ev)
    )
    if args.event:
        target = args.event.zfill(4)
        if target not in all_event_nums:
            print(f"[ERROR] Event file {target} not found in CSVs.", file=sys.stderr)
            sys.exit(1)
        all_event_nums = [target]

    EVENTS_EDITED.mkdir(parents=True, exist_ok=True)

    total_written = 0
    errors = 0
    warnings = 0

    for file_num in all_event_nums:
        sp   = sorted(sp_by_ev.get(file_num, []),   key=lambda r: int(r["index"]))
        ow   = sorted(ow_by_ev.get(file_num, []),   key=lambda r: int(r["index"]))
        wp   = sorted(warp_by_ev.get(file_num, []), key=lambda r: int(r["index"]))
        tr   = sorted(trig_by_ev.get(file_num, []), key=lambda r: int(r["index"]))

        # --- Pre-serialize validation ---
        ow_ids = [int(r["ow_id"]) for r in ow]
        dup_ids = [x for x in set(ow_ids) if ow_ids.count(x) > 1]
        if dup_ids:
            print(f"  [WARN] {file_num}: duplicate ow_id(s): {dup_ids}", file=sys.stderr)
            warnings += 1

        orig_path = find_raw(file_num)
        if orig_path:
            orig_counts = count_entities(orig_path.read_bytes())
            csv_counts = (len(sp), len(ow), len(wp), len(tr))
            if csv_counts != orig_counts:
                delta = tuple(c - o for c, o in zip(csv_counts, orig_counts))
                labels = ("sp", "ow", "warp", "trig")
                parts = []
                for lbl, d in zip(labels, delta):
                    if d != 0:
                        parts.append(f"{lbl} {'+' if d > 0 else ''}{d}")
                print(f"  [WARN] {file_num}: count changed vs original: {', '.join(parts)}")
                warnings += 1

        try:
            data = serialize_event_file(file_num, sp, ow, wp, tr)
        except Exception as exc:
            print(f"[ERROR] {file_num}: {exc}", file=sys.stderr)
            errors += 1
            continue

        out_path = EVENTS_EDITED / file_num
        out_path.write_bytes(data)
        total_written += 1

        if args.validate:
            written_counts = count_entities(data)
            label = f"{file_num}"
            if orig_path:
                orig_data = orig_path.read_bytes()
                orig_counts  = count_entities(orig_data)
                match = written_counts == orig_counts
                status = "OK  " if match else "DIFF"
                if not match:
                    print(f"  [{status}] {label}: orig={orig_counts} written={written_counts}")
                else:
                    print(f"  [{status}] {label}: {written_counts} entities, {len(data)} bytes")
            else:
                print(f"  [----] {label}: no original for comparison, {written_counts} entities, {len(data)} bytes")

    print(f"\nWrote {total_written} event file(s) to events/edited/")
    if warnings:
        print(f"  ({warnings} warning(s) — see above)")
    if errors:
        print(f"  ({errors} error(s) — see above)", file=sys.stderr)


if __name__ == "__main__":
    main()

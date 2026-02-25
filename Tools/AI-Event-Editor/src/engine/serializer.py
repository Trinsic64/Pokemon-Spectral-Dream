"""Serialize event CSVs to binary event files (DSPRE EventFile format)."""

from __future__ import annotations

import csv
import struct
from pathlib import Path

OVERWORLD_TYPE = {"NORMAL": 0, "TRAINER": 1, "ITEM": 3}
OVERWORLD_TYPE_REV = {v: k for k, v in OVERWORLD_TYPE.items()}
SPAWNABLE_TYPE = {"MISC": 0, "BOARD": 1, "HIDDENITEM": 2}


def _int(val: str, default: int = 0) -> int:
    if not val:
        return default
    val = val.strip()
    if val.startswith("0x") or val.startswith("0X"):
        return int(val, 16)
    return int(val)


def _u16(val: str, field: str) -> int:
    num = _int(val, 0)
    if num < 0 or num > 0xFFFF:
        raise ValueError(f"{field} out of range for u16: {num}")
    return num


def _s16(val: str, field: str) -> int:
    num = _int(val, 0)
    if num < -0x8000 or num > 0x7FFF:
        raise ValueError(f"{field} out of range for s16: {num}")
    return num


def serialize_event_file(
    overworlds: list[dict],
    spawnables: list[dict],
    warps: list[dict],
    triggers: list[dict],
) -> bytes:
    """Serialize entity lists into a binary event file."""
    buf = bytearray()

    # Spawnables (0x14 bytes each)
    buf += struct.pack("<I", len(spawnables))
    for sp in spawnables:
        script = _u16(sp.get("script", "0"), "spawnable.script")
        sp_type_val = str(sp.get("type", "0")).upper()
        if sp_type_val in SPAWNABLE_TYPE:
            sp_type = SPAWNABLE_TYPE[sp_type_val]
        else:
            sp_type = _u16(sp_type_val, "spawnable.type")
        x = _s16(str(_int(sp.get("x_map", "0")) + _int(sp.get("x_matrix", "0")) * 32), "spawnable.x")
        y = _s16(str(_int(sp.get("y_map", "0")) + _int(sp.get("y_matrix", "0")) * 32), "spawnable.y")
        z = _int(sp.get("z", "0"))
        direction = _u16(sp.get("direction", "0"), "spawnable.direction")
        unk2 = _u16(sp.get("unk2", "0"), "spawnable.unk2")
        unk4 = _u16(sp.get("unk4", "0"), "spawnable.unk4")
        unk5 = _u16(sp.get("unk5", "0"), "spawnable.unk5")

        buf += struct.pack("<HH", script, sp_type)
        buf += struct.pack("<hH", x, unk2)
        buf += struct.pack("<h", y)
        buf += struct.pack("<i", z)
        buf += struct.pack("<HH", unk4, direction)
        buf += struct.pack("<H", unk5)

    # Overworlds (0x20 bytes each)
    buf += struct.pack("<I", len(overworlds))
    for ow in overworlds:
        ow_id = _u16(ow.get("ow_id", "0"), "overworld.ow_id")
        overlay = _u16(ow.get("overlay_entry", "0"), "overworld.overlay_entry")
        movement = _u16(ow.get("movement", "0"), "overworld.movement")
        ow_type_str = ow.get("type", "NORMAL")
        if ow_type_str in OVERWORLD_TYPE:
            ow_type = OVERWORLD_TYPE[ow_type_str]
        else:
            ow_type = _u16(ow_type_str, "overworld.type")
        flag = _u16(ow.get("flag", "0"), "overworld.flag")
        script = _u16(ow.get("script", "0"), "overworld.script")
        orient = _u16(ow.get("orientation", "1"), "overworld.orientation")
        sight = _u16(ow.get("sight_range", "0"), "overworld.sight_range")
        unk1 = _u16(ow.get("unknown1", "0"), "overworld.unknown1")
        unk2 = _u16(ow.get("unknown2", "0"), "overworld.unknown2")
        x_range = _u16(ow.get("x_range", "0"), "overworld.x_range")
        y_range = _u16(ow.get("y_range", "0"), "overworld.y_range")
        x = _s16(str(_int(ow.get("x_map", "0")) + _int(ow.get("x_matrix", "0")) * 32), "overworld.x")
        y = _s16(str(_int(ow.get("y_map", "0")) + _int(ow.get("y_matrix", "0")) * 32), "overworld.y")
        z = _int(ow.get("z", "0"))

        buf += struct.pack("<HHHH", ow_id, overlay, movement, ow_type)
        buf += struct.pack("<HH", flag, script)
        buf += struct.pack("<HH", orient, sight)
        buf += struct.pack("<HH", unk1, unk2)
        buf += struct.pack("<HH", x_range, y_range)
        buf += struct.pack("<hhI", x, y, z)

    # Warps (0x0C bytes each)
    buf += struct.pack("<I", len(warps))
    for w in warps:
        x = _u16(w.get("x_map", w.get("x", "0")), "warp.x")
        y = _u16(w.get("y_map", w.get("y", "0")), "warp.y")
        dest = _u16(w.get("dest_header", "0"), "warp.dest_header")
        anchor = _u16(w.get("anchor", "0"), "warp.anchor")
        height = _int(w.get("height", "0"))
        buf += struct.pack("<HHHHI", x, y, dest, anchor, height)

    # Triggers (0x10 bytes each)
    buf += struct.pack("<I", len(triggers))
    for t in triggers:
        script = _u16(t.get("script", "0"), "trigger.script")
        x = _u16(t.get("x_map", t.get("x", "0")), "trigger.x")
        y = _u16(t.get("y_map", t.get("y", "0")), "trigger.y")
        w = _u16(t.get("width", "0"), "trigger.width")
        h = _u16(t.get("height_range", "0"), "trigger.height_range")
        unk = _u16(t.get("unknown", "0"), "trigger.unknown")
        val = _u16(t.get("expected_value", "0"), "trigger.expected_value")
        var = _u16(t.get("variable", "0"), "trigger.variable")
        buf += struct.pack("<HHHHHHHH", script, x, y, w, h, unk, val, var)

    return bytes(buf)


def serialize_from_csvs(
    events_dir: Path,
    event_file: str,
    output_dir: Path,
) -> Path:
    """Load CSVs and serialize one event file to binary."""
    ef = event_file.zfill(4)

    def load_entities(csv_name: str) -> list[dict]:
        csv_path = events_dir / csv_name
        if not csv_path.exists():
            return []
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row for row in reader if row.get("event_file") == ef]

    overworlds = load_entities("overworlds.csv")
    spawnables = load_entities("spawnables.csv")
    warps = load_entities("warps.csv")
    triggers = load_entities("triggers.csv")

    data = serialize_event_file(overworlds, spawnables, warps, triggers)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / ef
    out_path.write_bytes(data)
    return out_path

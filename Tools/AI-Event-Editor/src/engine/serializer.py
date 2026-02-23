"""Serialize event CSVs to binary event files (DSPRE EventFile format)."""

from __future__ import annotations

import csv
import struct
from pathlib import Path

OVERWORLD_TYPE = {"NORMAL": 0, "TRAINER": 1, "ITEM": 3}
OVERWORLD_TYPE_REV = {v: k for k, v in OVERWORLD_TYPE.items()}


def _int(val: str, default: int = 0) -> int:
    if not val:
        return default
    val = val.strip()
    if val.startswith("0x") or val.startswith("0X"):
        return int(val, 16)
    return int(val)


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
        script = _int(sp.get("script", "0"))
        sp_type = _int(sp.get("type", "0"))
        x = _int(sp.get("x_map", "0")) + _int(sp.get("x_matrix", "0")) * 32
        y = _int(sp.get("y_map", "0")) + _int(sp.get("y_matrix", "0")) * 32
        z = _int(sp.get("z", "0"))
        direction = _int(sp.get("direction", "0"))
        unk2 = _int(sp.get("unk2", "0"))
        unk4 = _int(sp.get("unk4", "0"))
        unk5 = _int(sp.get("unk5", "0"))

        buf += struct.pack("<HH", script, sp_type)
        buf += struct.pack("<hH", x, unk2)
        buf += struct.pack("<h", y)
        buf += struct.pack("<i", z)
        buf += struct.pack("<HH", unk4, direction)
        buf += struct.pack("<H", unk5)

    # Overworlds (0x20 bytes each)
    buf += struct.pack("<I", len(overworlds))
    for ow in overworlds:
        ow_id = _int(ow.get("ow_id", "0"))
        overlay = _int(ow.get("overlay_entry", "0"))
        movement = _int(ow.get("movement", "0"))
        ow_type_str = ow.get("type", "NORMAL")
        ow_type = OVERWORLD_TYPE.get(ow_type_str, _int(ow_type_str, 0))
        flag = _int(ow.get("flag", "0"))
        script = _int(ow.get("script", "0"))
        orient = _int(ow.get("orientation", "1"))
        sight = _int(ow.get("sight_range", "0"))
        unk1 = _int(ow.get("unknown1", "0"))
        unk2 = _int(ow.get("unknown2", "0"))
        x_range = _int(ow.get("x_range", "0"))
        y_range = _int(ow.get("y_range", "0"))
        x = _int(ow.get("x_map", "0")) + _int(ow.get("x_matrix", "0")) * 32
        y = _int(ow.get("y_map", "0")) + _int(ow.get("y_matrix", "0")) * 32
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
        x = _int(w.get("x_map", w.get("x", "0")))
        y = _int(w.get("y_map", w.get("y", "0")))
        dest = _int(w.get("dest_header", "0"))
        anchor = _int(w.get("anchor", "0"))
        height = _int(w.get("height", "0"))
        buf += struct.pack("<HHHHI", x, y, dest, anchor, height)

    # Triggers (0x10 bytes each)
    buf += struct.pack("<I", len(triggers))
    for t in triggers:
        script = _int(t.get("script", "0"))
        x = _int(t.get("x_map", t.get("x", "0")))
        y = _int(t.get("y_map", t.get("y", "0")))
        w = _int(t.get("width", "0"))
        h = _int(t.get("height_range", "0"))
        unk = _int(t.get("unknown", "0"))
        val = _int(t.get("expected_value", "0"))
        var = _int(t.get("variable", "0"))
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

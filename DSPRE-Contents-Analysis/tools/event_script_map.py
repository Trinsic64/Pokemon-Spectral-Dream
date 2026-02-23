#!/usr/bin/env python3
"""
event_script_map.py

Generates a CSV mapping every overworld, spawnable, and trigger to its
corresponding script file and script number. This gives a scripting AI a
clear view of which entities trigger which scripts.

Output: events/event-script-map.csv

Columns:
    entity_type, event_file, maps, entity_index, ow_id, overlay_entry,
    ow_type, script_file, script_num, flag

The script_file is resolved via Header-Data-Main.csv (Event File -> HEADER# -> Script File).

Standard-library only.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

HEADER_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"
EVENTS_DIR = ANALYSIS_ROOT / "events"
OUTPUT_CSV = EVENTS_DIR / "event-script-map.csv"


def load_event_to_script_file() -> dict[str, str]:
    """Return {event_file_zero_padded: script_file_number}."""
    mapping: dict[str, str] = {}
    if not HEADER_CSV.exists():
        return mapping
    with HEADER_CSV.open(encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            ev = row.get("Event File", "").strip()
            sf = row.get("Script File", "").strip()
            if ev and sf:
                try:
                    key = str(int(float(ev))).zfill(4)
                except ValueError:
                    key = ev
                mapping[key] = sf
    return mapping


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    ev_to_sf = load_event_to_script_file()

    overworlds  = load_csv(EVENTS_DIR / "overworlds.csv")
    spawnables  = load_csv(EVENTS_DIR / "spawnables.csv")
    triggers    = load_csv(EVENTS_DIR / "triggers.csv")

    rows: list[dict] = []

    for r in overworlds:
        ef = r["event_file"]
        sf = ev_to_sf.get(ef, "")
        scr = r["script"]
        rows.append({
            "entity_type":   "overworld",
            "event_file":    ef,
            "maps":          r.get("maps", ""),
            "entity_index":  r["index"],
            "ow_id":         r.get("ow_id", ""),
            "overlay_entry": r.get("overlay_entry", ""),
            "ow_type":       r.get("type", ""),
            "script_file":   sf,
            "script_num":    scr,
            "flag":          r.get("flag", ""),
        })

    for r in spawnables:
        ef = r["event_file"]
        sf = ev_to_sf.get(ef, "")
        rows.append({
            "entity_type":   "spawnable",
            "event_file":    ef,
            "maps":          r.get("maps", ""),
            "entity_index":  r["index"],
            "ow_id":         "",
            "overlay_entry": "",
            "ow_type":       r.get("type", ""),
            "script_file":   sf,
            "script_num":    r["script"],
            "flag":          "",
        })

    for r in triggers:
        ef = r["event_file"]
        sf = ev_to_sf.get(ef, "")
        rows.append({
            "entity_type":   "trigger",
            "event_file":    ef,
            "maps":          r.get("maps", ""),
            "entity_index":  r["index"],
            "ow_id":         "",
            "overlay_entry": "",
            "ow_type":       "",
            "script_file":   sf,
            "script_num":    r["script"],
            "flag":          r.get("var_watched", ""),
        })

    fieldnames = [
        "entity_type", "event_file", "maps", "entity_index", "ow_id",
        "overlay_entry", "ow_type", "script_file", "script_num", "flag",
    ]

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    ow_count = sum(1 for r in rows if r["entity_type"] == "overworld")
    sp_count = sum(1 for r in rows if r["entity_type"] == "spawnable")
    tr_count = sum(1 for r in rows if r["entity_type"] == "trigger")
    linked   = sum(1 for r in rows if r["script_file"])

    print(f"Wrote {len(rows)} entries to events/event-script-map.csv")
    print(f"  Overworlds: {ow_count}, Spawnables: {sp_count}, Triggers: {tr_count}")
    print(f"  Linked to script file: {linked}/{len(rows)}")


if __name__ == "__main__":
    main()

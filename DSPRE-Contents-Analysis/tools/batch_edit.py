#!/usr/bin/env python3
"""
batch_edit.py

Applies bulk event edits from a JSON manifest file, serializes all affected
event files, and logs all changes to a changelog CSV.

Usage:
    python tools/batch_edit.py manifest.json              # apply edits
    python tools/batch_edit.py manifest.json --dry-run    # show what would change
    python tools/batch_edit.py manifest.json --backup     # create backup first

Manifest format (JSON):
{
    "description": "Batch edit description",
    "edits": [
        {
            "action": "modify_overworld",
            "event_file": "0057",
            "index": 2,
            "changes": {"overlay_entry": "522"}
        },
        {
            "action": "add_overworld",
            "event_file": "0057",
            "data": {
                "ow_id": "10", "overlay_entry": "87", "type": "ITEM",
                "movement": "0", "flag": "0x0A0B", "script": "10",
                "orientation": "1", "sight_range": "0",
                "x_range": "0", "y_range": "0",
                "x_map": "16", "x_matrix": "30",
                "y_map": "16", "y_matrix": "38", "z": "0"
            }
        },
        {
            "action": "remove_overworld",
            "event_file": "0057",
            "index": 5
        },
        {
            "action": "modify_warp",
            "event_file": "0057",
            "index": 0,
            "changes": {"dest_header": "15"}
        }
    ]
}

Supported actions: modify_overworld, add_overworld, remove_overworld,
                   modify_warp, add_warp, remove_warp,
                   modify_spawnable, add_spawnable, remove_spawnable,
                   modify_trigger, add_trigger, remove_trigger

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
EVENTS_DIR = ANALYSIS_ROOT / "events"
CHANGELOG_CSV = EVENTS_DIR / "changelog.csv"

ENTITY_FILES = {
    "overworld":  "overworlds.csv",
    "warp":       "warps.csv",
    "spawnable":  "spawnables.csv",
    "trigger":    "triggers.csv",
}


def load_csv(name: str) -> tuple[list[dict], list[str]]:
    path = EVENTS_DIR / name
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


def save_csv(name: str, rows: list[dict], fieldnames: list[str]) -> None:
    path = EVENTS_DIR / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_changelog(entries: list[dict]) -> None:
    exists = CHANGELOG_CSV.exists()
    fieldnames = ["timestamp", "action", "entity_type", "event_file", "index",
                  "field", "old_value", "new_value", "description"]
    with CHANGELOG_CSV.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerows(entries)


def apply_edit(edit: dict, all_data: dict, changelog: list[dict],
               timestamp: str, dry_run: bool) -> set[str]:
    """Apply one edit. Returns set of affected event_file numbers."""
    action = edit["action"]
    parts = action.split("_", 1)
    if len(parts) != 2:
        print(f"  [ERROR] Unknown action: {action}", file=sys.stderr)
        return set()

    verb, entity = parts[0], parts[1]
    csv_file = ENTITY_FILES.get(entity)
    if not csv_file:
        print(f"  [ERROR] Unknown entity type: {entity}", file=sys.stderr)
        return set()

    rows, fieldnames = all_data[csv_file]
    event_file = edit.get("event_file", "").zfill(4)
    affected = {event_file}

    if verb == "modify":
        idx = int(edit["index"])
        changes = edit.get("changes", {})
        target = [r for r in rows if r["event_file"] == event_file and int(r["index"]) == idx]
        if not target:
            print(f"  [WARN] {entity} not found: event={event_file} index={idx}")
            return set()
        row = target[0]
        for field, new_val in changes.items():
            old_val = row.get(field, "")
            row[field] = str(new_val)
            changelog.append({
                "timestamp": timestamp, "action": action, "entity_type": entity,
                "event_file": event_file, "index": idx,
                "field": field, "old_value": old_val, "new_value": str(new_val),
                "description": edit.get("description", ""),
            })
            print(f"  {action}: event={event_file} idx={idx} {field}: {old_val} -> {new_val}")

    elif verb == "add":
        raw_data = edit.get("data", {})
        existing = [r for r in rows if r["event_file"] == event_file]
        new_index = max((int(r["index"]) for r in existing), default=-1) + 1
        data = {"event_file": event_file, "index": str(new_index), "maps": ""}
        for fn in fieldnames:
            data.setdefault(fn, raw_data.get(fn, ""))
        rows.append(data)
        changelog.append({
            "timestamp": timestamp, "action": action, "entity_type": entity,
            "event_file": event_file, "index": new_index,
            "field": "", "old_value": "", "new_value": json.dumps(data),
            "description": edit.get("description", ""),
        })
        print(f"  {action}: event={event_file} new idx={new_index}")

    elif verb == "remove":
        idx = int(edit["index"])
        before = len(rows)
        removed_rows = [r for r in rows if r["event_file"] == event_file and int(r["index"]) == idx]
        all_data[csv_file] = (
            [r for r in rows if not (r["event_file"] == event_file and int(r["index"]) == idx)],
            fieldnames,
        )
        after = len(all_data[csv_file][0])
        if before == after:
            print(f"  [WARN] {entity} not found for removal: event={event_file} index={idx}")
        else:
            changelog.append({
                "timestamp": timestamp, "action": action, "entity_type": entity,
                "event_file": event_file, "index": idx,
                "field": "", "old_value": json.dumps(removed_rows[0] if removed_rows else {}),
                "new_value": "",
                "description": edit.get("description", ""),
            })
            print(f"  {action}: event={event_file} idx={idx} removed")

    return affected


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch event editor from JSON manifest.")
    parser.add_argument("manifest", help="Path to JSON manifest file.")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying.")
    parser.add_argument("--backup", action="store_true", help="Create backup before editing.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        # Try relative to ANALYSIS_ROOT
        manifest_path = ANALYSIS_ROOT / args.manifest
    if not manifest_path.exists():
        print(f"[ERROR] Manifest not found: {args.manifest}", file=sys.stderr)
        sys.exit(1)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    edits = manifest.get("edits", [])
    desc = manifest.get("description", "")

    print(f"Manifest: {desc or manifest_path.name}")
    print(f"Edits: {len(edits)}")

    if args.backup and not args.dry_run:
        print("Creating backup...")
        subprocess.run([sys.executable, str(ANALYSIS_ROOT / "tools" / "backup_events.py"),
                        "create", "--name", f"pre_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"],
                       check=True)
        print()

    # Load all CSV data
    all_data: dict[str, tuple[list[dict], list[str]]] = {}
    for csv_file in ENTITY_FILES.values():
        all_data[csv_file] = load_csv(csv_file)

    timestamp = datetime.now().isoformat()
    changelog: list[dict] = []
    affected_events: set[str] = set()

    for edit in edits:
        affected = apply_edit(edit, all_data, changelog, timestamp, args.dry_run)
        affected_events.update(affected)

    if not args.dry_run:
        for csv_file, (rows, fieldnames) in all_data.items():
            save_csv(csv_file, rows, fieldnames)
        append_changelog(changelog)
        print(f"\nSaved {len(changelog)} change(s) to {len(ENTITY_FILES)} CSV files.")
        print(f"Changelog appended to events/changelog.csv")
        print(f"\nAffected event files: {sorted(affected_events)}")
        print(f"Run: python tools/serialize_events.py --validate")
        for ef in sorted(affected_events):
            print(f"  python tools/serialize_events.py --event {ef} --validate")
    else:
        print(f"\n[DRY RUN] Would make {len(changelog)} change(s) to {len(affected_events)} event file(s).")


if __name__ == "__main__":
    main()

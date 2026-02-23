#!/usr/bin/env python3
"""
backup_events.py

Snapshots event data (raw binaries and CSVs) before batch edits, and supports
restoring from a previous snapshot.

Usage:
    python tools/backup_events.py create              # create timestamped backup
    python tools/backup_events.py create --name v1    # create named backup
    python tools/backup_events.py list                # list all backups
    python tools/backup_events.py restore <name>      # restore from a backup
    python tools/backup_events.py diff <name>         # show entity count diffs vs backup

Backups are stored in DSPRE-Contents-Analysis/events/backups/<name>/

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
EVENTS_DIR = ANALYSIS_ROOT / "events"
EVENTS_RAW = EVENTS_DIR / "raw"
BACKUPS_DIR = EVENTS_DIR / "backups"

CSV_FILES = ["overworlds.csv", "warps.csv", "spawnables.csv", "triggers.csv",
             "events-summary.csv", "event-script-map.csv"]


def count_entities(data: bytes) -> tuple[int, int, int, int]:
    pos = 0
    def ru32():
        nonlocal pos
        v = struct.unpack_from("<I", data, pos)[0]; pos += 4; return v
    sp = ru32(); pos += sp * 20
    ow = ru32(); pos += ow * 32
    wp = ru32(); pos += wp * 12
    tr = ru32(); pos += tr * 16
    return sp, ow, wp, tr


def cmd_create(name: str | None) -> None:
    if name is None:
        name = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_dir = BACKUPS_DIR / name
    if backup_dir.exists():
        print(f"[ERROR] Backup '{name}' already exists.", file=sys.stderr)
        sys.exit(1)

    backup_dir.mkdir(parents=True)

    # Back up raw binaries
    raw_backup = backup_dir / "raw"
    if EVENTS_RAW.exists():
        shutil.copytree(EVENTS_RAW, raw_backup)
        raw_count = sum(1 for _ in raw_backup.iterdir())
        print(f"  Backed up {raw_count} raw event files.")
    else:
        print("  [WARN] No raw event files found.")

    # Back up CSVs
    csv_count = 0
    for csv_name in CSV_FILES:
        src = EVENTS_DIR / csv_name
        if src.exists():
            shutil.copy2(src, backup_dir / csv_name)
            csv_count += 1
    print(f"  Backed up {csv_count} CSV files.")

    # Write metadata
    meta = backup_dir / "backup_meta.txt"
    meta.write_text(f"name: {name}\ncreated: {datetime.now().isoformat()}\n", encoding="utf-8")

    print(f"\nBackup created: events/backups/{name}/")


def cmd_list() -> None:
    if not BACKUPS_DIR.exists():
        print("No backups found.")
        return

    backups = sorted(d for d in BACKUPS_DIR.iterdir() if d.is_dir())
    if not backups:
        print("No backups found.")
        return

    print(f"{'Name':<30} {'Created':<25} {'Raw files':<12} {'CSVs'}")
    print("-" * 80)
    for b in backups:
        meta = b / "backup_meta.txt"
        created = ""
        if meta.exists():
            for line in meta.read_text(encoding="utf-8").splitlines():
                if line.startswith("created:"):
                    created = line.split(":", 1)[1].strip()[:19]

        raw_dir = b / "raw"
        raw_count = sum(1 for _ in raw_dir.iterdir()) if raw_dir.exists() else 0
        csv_count = sum(1 for f in b.iterdir() if f.suffix == ".csv")
        print(f"{b.name:<30} {created:<25} {raw_count:<12} {csv_count}")


def cmd_restore(name: str) -> None:
    backup_dir = BACKUPS_DIR / name
    if not backup_dir.exists():
        print(f"[ERROR] Backup '{name}' not found.", file=sys.stderr)
        sys.exit(1)

    # Restore raw binaries
    raw_backup = backup_dir / "raw"
    if raw_backup.exists():
        if EVENTS_RAW.exists():
            shutil.rmtree(EVENTS_RAW)
        shutil.copytree(raw_backup, EVENTS_RAW)
        count = sum(1 for _ in EVENTS_RAW.iterdir())
        print(f"  Restored {count} raw event files.")

    # Restore CSVs
    csv_count = 0
    for csv_name in CSV_FILES:
        src = backup_dir / csv_name
        if src.exists():
            shutil.copy2(src, EVENTS_DIR / csv_name)
            csv_count += 1
    print(f"  Restored {csv_count} CSV files.")
    print(f"\nRestored from backup: {name}")


def cmd_diff(name: str) -> None:
    backup_dir = BACKUPS_DIR / name
    if not backup_dir.exists():
        print(f"[ERROR] Backup '{name}' not found.", file=sys.stderr)
        sys.exit(1)

    raw_backup = backup_dir / "raw"
    if not raw_backup.exists() or not EVENTS_RAW.exists():
        print("Cannot diff: raw directories missing.")
        return

    backup_files = {f.name: f for f in raw_backup.iterdir() if f.is_file()}
    current_files = {f.name: f for f in EVENTS_RAW.iterdir() if f.is_file()}

    added = set(current_files) - set(backup_files)
    removed = set(backup_files) - set(current_files)
    common = set(backup_files) & set(current_files)

    diffs = 0
    for fname in sorted(common):
        try:
            old_data = backup_files[fname].read_bytes()
            new_data = current_files[fname].read_bytes()
            if old_data != new_data:
                old_counts = count_entities(old_data)
                new_counts = count_entities(new_data)
                if old_counts != new_counts:
                    print(f"  {fname}: counts {old_counts} -> {new_counts}")
                else:
                    print(f"  {fname}: data changed (same entity counts)")
                diffs += 1
        except Exception:
            pass

    if added:
        print(f"  Added: {len(added)} files")
    if removed:
        print(f"  Removed: {len(removed)} files")
    if diffs == 0 and not added and not removed:
        print("  No differences found.")
    else:
        print(f"\n{diffs} file(s) changed, {len(added)} added, {len(removed)} removed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Event data backup and restore.")
    sub = parser.add_subparsers(dest="command")

    create = sub.add_parser("create", help="Create a backup snapshot.")
    create.add_argument("--name", default=None, help="Backup name (default: timestamp).")

    sub.add_parser("list", help="List all backups.")

    restore = sub.add_parser("restore", help="Restore from a backup.")
    restore.add_argument("name", help="Backup name to restore.")

    diff = sub.add_parser("diff", help="Show differences vs a backup.")
    diff.add_argument("name", help="Backup name to compare against.")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "create":
        cmd_create(args.name)
    elif args.command == "list":
        cmd_list()
    elif args.command == "restore":
        cmd_restore(args.name)
    elif args.command == "diff":
        cmd_diff(args.name)


if __name__ == "__main__":
    main()

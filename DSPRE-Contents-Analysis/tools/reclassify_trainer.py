#!/usr/bin/env python3
"""
reclassify_trainer.py

Changes a trainer's class across all four data sources atomically:
  1. Data/Trainer-Data/Trainer-Data-Main.csv  (TrainerClass + OWID columns)
  2. Data/Trainer-Data/Trainers/T{ID}-*/meta.json  (trainerclass field)
  3. Tools/hg-engine/armips/data/trainers/trainers.s  (trainerclass line)
  4. DSPRE-Contents-Analysis/events/overworlds.csv  (overlay_entry for matching OWID)

Usage:
    python tools/reclassify_trainer.py --trainer-id 1 --new-class TRAINERCLASS_HIKER --new-owid 333
    python tools/reclassify_trainer.py --trainer-id 1 --new-class TRAINERCLASS_HIKER  # OWID only if provided
    python tools/reclassify_trainer.py --dry-run --trainer-id 1 --new-class TRAINERCLASS_HIKER --new-owid 333
    python tools/reclassify_trainer.py list-classes   # show all available trainer classes

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

TRAINER_CSV = REPO_ROOT / "Data" / "Trainer-Data" / "Trainer-Data-Main.csv"
TRAINERS_DIR = REPO_ROOT / "Data" / "Trainer-Data" / "Trainers"
TRAINERS_S = REPO_ROOT / "Tools" / "hg-engine" / "armips" / "data" / "trainers" / "trainers.s"
TRAINERCLASS_H = REPO_ROOT / "Tools" / "hg-engine" / "include" / "constants" / "trainerclass.h"
OVERWORLDS_CSV = ANALYSIS_ROOT / "events" / "overworlds.csv"


def load_trainer_classes() -> dict[str, int]:
    """Parse trainerclass.h into {TRAINERCLASS_NAME: numeric_value}."""
    classes: dict[str, int] = {}
    if not TRAINERCLASS_H.exists():
        return classes
    for line in TRAINERCLASS_H.read_text(encoding="utf-8").splitlines():
        m = re.match(r"#define\s+(TRAINERCLASS_\w+)\s+(\d+)", line)
        if m:
            classes[m.group(1)] = int(m.group(2))
    return classes


def find_trainer_dir(trainer_id: int) -> Path | None:
    """Find the T{ID}-* directory for a trainer."""
    prefix = f"T{trainer_id}-"
    for d in TRAINERS_DIR.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            return d
    return None


def update_trainer_csv(trainer_id: int, new_class: str, new_owid: str | None, dry_run: bool) -> str | None:
    """Update Trainer-Data-Main.csv. Returns old class name or None if not found."""
    rows = list(csv.DictReader(TRAINER_CSV.open(encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else []

    old_class = None
    old_owid = None
    for row in rows:
        if row.get("TrainerID", "").strip() == str(trainer_id):
            old_class = row.get("TrainerClass", "").strip()
            old_owid = row.get("OWID", "").strip()
            row["TrainerClass"] = new_class
            if new_owid is not None:
                row["OWID"] = new_owid
            break

    if old_class is None:
        return None

    if not dry_run:
        with TRAINER_CSV.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    owid_msg = f", OWID {old_owid} -> {new_owid}" if new_owid else ""
    print(f"  [CSV] TrainerClass: {old_class} -> {new_class}{owid_msg}")
    return old_class


def update_meta_json(trainer_id: int, new_class: str, dry_run: bool) -> bool:
    """Update meta.json in the trainer's directory."""
    tdir = find_trainer_dir(trainer_id)
    if not tdir:
        print(f"  [META] Trainer directory not found for ID {trainer_id}")
        return False

    meta_path = tdir / "meta.json"
    if not meta_path.exists():
        print(f"  [META] meta.json not found in {tdir.name}")
        return False

    data = json.loads(meta_path.read_text(encoding="utf-8"))
    old = data.get("trainerclass", "")
    data["trainerclass"] = new_class

    if not dry_run:
        meta_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"  [META] {tdir.name}/meta.json: {old} -> {new_class}")
    return True


def update_trainers_s(trainer_id: int, new_class: str, dry_run: bool) -> bool:
    """Update the trainerclass line in trainers.s for a specific trainer."""
    if not TRAINERS_S.exists():
        print(f"  [ASM] trainers.s not found")
        return False

    text = TRAINERS_S.read_text(encoding="utf-8")
    lines = text.split("\n")

    # Find the trainerdata line for this ID
    in_trainer = False
    changed = False
    for i, line in enumerate(lines):
        m = re.match(r"trainerdata\s+(\d+)\s*,", line)
        if m:
            if int(m.group(1)) == trainer_id:
                in_trainer = True
            else:
                in_trainer = False

        if in_trainer and re.match(r"\s+trainerclass\s+", line):
            old_line = line.rstrip()
            new_line = re.sub(r"(trainerclass\s+)\S+", rf"\1{new_class}", line).rstrip()
            if old_line != new_line:
                lines[i] = new_line
                changed = True
                print(f"  [ASM] Line {i + 1}: {old_line.strip()} -> {new_line.strip()}")
            in_trainer = False

    if changed and not dry_run:
        TRAINERS_S.write_text("\n".join(lines), encoding="utf-8")

    if not changed:
        print(f"  [ASM] No trainerclass line found for trainer {trainer_id}")
    return changed


def update_overworlds_csv(trainer_id: int, old_owid: str, new_owid: str, dry_run: bool) -> int:
    """Update overlay_entry in overworlds.csv for overworlds matching the old OWID.
    Returns number of rows changed."""
    if not OVERWORLDS_CSV.exists():
        return 0

    # We need to match TRAINER-type overworlds by their OWID in the Trainer CSV.
    # The OWID in Trainer-Data-Main.csv corresponds to the overlay_entry in overworlds.csv.
    rows = list(csv.DictReader(OVERWORLDS_CSV.open(encoding="utf-8")))
    fieldnames = list(rows[0].keys()) if rows else []

    changed = 0
    for row in rows:
        if row.get("type", "").strip() == "TRAINER" and row.get("overlay_entry", "").strip() == old_owid:
            row["overlay_entry"] = new_owid
            changed += 1

    if changed > 0 and not dry_run:
        with OVERWORLDS_CSV.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    if changed:
        print(f"  [OW]  Changed {changed} overworld(s): overlay_entry {old_owid} -> {new_owid}")
    return changed


def cmd_reclassify(args: argparse.Namespace) -> None:
    trainer_id = args.trainer_id
    new_class = args.new_class
    new_owid = args.new_owid
    dry_run = args.dry_run

    if dry_run:
        print(f"[DRY RUN] Reclassifying trainer {trainer_id} to {new_class}")
    else:
        print(f"Reclassifying trainer {trainer_id} to {new_class}")

    # Get old OWID before changing CSV
    old_owid = None
    csv_rows = list(csv.DictReader(TRAINER_CSV.open(encoding="utf-8")))
    for row in csv_rows:
        if row.get("TrainerID", "").strip() == str(trainer_id):
            old_owid = row.get("OWID", "").strip()
            break

    if old_owid is None:
        print(f"[ERROR] Trainer ID {trainer_id} not found in Trainer-Data-Main.csv", file=sys.stderr)
        sys.exit(1)

    # 1. Update CSV
    update_trainer_csv(trainer_id, new_class, new_owid, dry_run)

    # 2. Update meta.json
    update_meta_json(trainer_id, new_class, dry_run)

    # 3. Update trainers.s
    update_trainers_s(trainer_id, new_class, dry_run)

    # 4. Update overworlds.csv (only if OWID changed)
    if new_owid and new_owid != old_owid:
        update_overworlds_csv(trainer_id, old_owid, new_owid, dry_run)
    else:
        print(f"  [OW]  OWID unchanged ({old_owid}), skipping overworlds.csv")

    if dry_run:
        print("\n[DRY RUN] No files were modified.")
    else:
        print("\nDone. All files updated.")


def cmd_list_classes() -> None:
    classes = load_trainer_classes()
    print(f"Available trainer classes ({len(classes)}):")
    for name, val in sorted(classes.items(), key=lambda x: x[1]):
        print(f"  {val:3d}  {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reclassify a trainer across all data sources.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list-classes", help="List all available trainer classes.")

    reclass = sub.add_parser("reclassify", help="Change a trainer's class.")
    reclass.add_argument("--trainer-id", type=int, required=True, help="Trainer ID to reclassify.")
    reclass.add_argument("--new-class", required=True, help="New TRAINERCLASS_* constant name.")
    reclass.add_argument("--new-owid", default=None, help="New OWID / overlay_entry for overworld sprite.")
    reclass.add_argument("--dry-run", action="store_true", help="Show what would change without modifying files.")

    # Also support flat args for convenience
    if len(sys.argv) > 1 and sys.argv[1] == "list-classes":
        cmd_list_classes()
        return

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list-classes":
        cmd_list_classes()
    elif args.command == "reclassify":
        cmd_reclassify(args)


if __name__ == "__main__":
    main()

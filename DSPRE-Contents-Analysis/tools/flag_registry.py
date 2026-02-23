#!/usr/bin/env python3
"""
flag_registry.py

Reads Flag-Data-Main.csv, identifies available (unused) flags, and provides
allocation and query functions for AI-driven event editing.

Usage:
    python tools/flag_registry.py status             # show flag pool summary
    python tools/flag_registry.py allocate N          # allocate N flags, print them
    python tools/flag_registry.py allocate N --name PREFIX --type ITEM --category CAT
    python tools/flag_registry.py check 2571          # check if flag 2571 is free
    python tools/flag_registry.py release 2571        # release a previously allocated flag

Allocation writes back to Flag-Data-Main.csv so future calls see the flag as used.

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
FLAG_CSV = REPO_ROOT / "Data" / "Flag-Data" / "Flag-Data-Main.csv"

AVAILABLE_TYPES = {"UNKOWN", ""}
EMPTY_STORY_POOL = "STORY"


def load_flags(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return rows, list(fieldnames)


def save_flags(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_available(row: dict) -> bool:
    """A flag is available if it has type UNKOWN with no name, or type STORY with no name."""
    t = row.get("Type", "").strip()
    name = row.get("Name", "").strip()
    if t == "UNKOWN" and not name:
        return True
    if t == EMPTY_STORY_POOL and not name and not row.get("Description", "").strip():
        return True
    return False


def get_available(rows: list[dict]) -> list[dict]:
    return [r for r in rows if is_available(r)]


def cmd_status(rows: list[dict]) -> None:
    available = get_available(rows)
    by_type: dict[str, list[int]] = {}
    for r in available:
        t = r.get("Type", "").strip() or "UNTYPED"
        dec = int(r["Decimal"])
        by_type.setdefault(t, []).append(dec)

    total_used = len(rows) - len(available)
    print(f"Total flags in CSV: {len(rows)}")
    print(f"Used/assigned flags: {total_used}")
    print(f"Available flags: {len(available)}")
    print()
    for t, decimals in sorted(by_type.items()):
        decimals.sort()
        lo, hi = decimals[0], decimals[-1]
        print(f"  [{t}] {len(decimals)} flags, range {lo}..{hi}")
    print()
    print(f"Next available: {available[0]['Decimal']} (0x{int(available[0]['Decimal']):X})" if available else "No flags available!")


def cmd_allocate(rows: list[dict], fieldnames: list[str], count: int,
                 name_prefix: str, flag_type: str, category: str,
                 description: str, event_file: str, owid: str) -> None:
    available = get_available(rows)
    if len(available) < count:
        print(f"[ERROR] Only {len(available)} flags available, {count} requested.", file=sys.stderr)
        sys.exit(1)

    allocated = available[:count]
    allocated_decimals = []

    for i, target in enumerate(allocated):
        dec = int(target["Decimal"])
        allocated_decimals.append(dec)
        for row in rows:
            if row["Decimal"] == target["Decimal"]:
                suffix = f"_{i:03d}" if count > 1 else ""
                row["Name"] = f"{name_prefix}{suffix}" if name_prefix else ""
                row["Type"] = flag_type if flag_type else "ITEM"
                row["CATEGORY"] = category
                row["Description"] = description
                row["Event File"] = event_file
                row["OWID"] = owid
                break

    save_flags(FLAG_CSV, rows, fieldnames)

    for dec in allocated_decimals:
        print(f"0x{dec:X} ({dec})")
    print(f"\nAllocated {count} flag(s). Flag-Data-Main.csv updated.")


def cmd_check(rows: list[dict], decimal: int) -> None:
    for r in rows:
        if r["Decimal"].strip() == str(decimal):
            avail = is_available(r)
            status = "AVAILABLE" if avail else "IN USE"
            name = r.get("Name", "").strip()
            typ = r.get("Type", "").strip()
            desc = r.get("Description", "").strip()
            print(f"Flag {decimal} (0x{decimal:X}): {status}")
            if name:
                print(f"  Name: {name}")
            if typ:
                print(f"  Type: {typ}")
            if desc:
                print(f"  Description: {desc}")
            return
    print(f"Flag {decimal} not found in CSV.", file=sys.stderr)
    sys.exit(1)


def cmd_release(rows: list[dict], fieldnames: list[str], decimal: int) -> None:
    for row in rows:
        if row["Decimal"].strip() == str(decimal):
            old_name = row.get("Name", "").strip()
            row["Name"] = ""
            row["Type"] = "STORY"
            row["CATEGORY"] = ""
            row["Description"] = ""
            row["Event File"] = ""
            row["OWID"] = ""
            save_flags(FLAG_CSV, rows, fieldnames)
            print(f"Released flag {decimal} (was: {old_name or 'unnamed'}). CSV updated.")
            return
    print(f"Flag {decimal} not found in CSV.", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag registry for AI event editing.")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show available flag pool summary.")

    alloc = sub.add_parser("allocate", help="Allocate N unused flags.")
    alloc.add_argument("count", type=int, help="Number of flags to allocate.")
    alloc.add_argument("--name", default="", help="Name prefix for the allocated flags.")
    alloc.add_argument("--type", default="ITEM", dest="flag_type", help="Flag type (ITEM, STORY, etc).")
    alloc.add_argument("--category", default="", help="Category value.")
    alloc.add_argument("--description", default="", help="Description.")
    alloc.add_argument("--event-file", default="", help="Event file reference.")
    alloc.add_argument("--owid", default="", help="OWID reference.")

    chk = sub.add_parser("check", help="Check if a flag (by decimal) is available.")
    chk.add_argument("decimal", type=int, help="Flag decimal number.")

    rel = sub.add_parser("release", help="Release a flag back to the pool.")
    rel.add_argument("decimal", type=int, help="Flag decimal number to release.")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    rows, fieldnames = load_flags(FLAG_CSV)

    if args.command == "status":
        cmd_status(rows)
    elif args.command == "allocate":
        cmd_allocate(rows, fieldnames, args.count, args.name, args.flag_type,
                     args.category, args.description, args.event_file, args.owid)
    elif args.command == "check":
        cmd_check(rows, args.decimal)
    elif args.command == "release":
        cmd_release(rows, fieldnames, args.decimal)


if __name__ == "__main__":
    main()

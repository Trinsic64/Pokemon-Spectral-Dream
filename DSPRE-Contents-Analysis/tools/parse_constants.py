#!/usr/bin/env python3
"""
parse_constants.py

Parses #define constants from hg-engine C header files and writes them
as CSV lookup tables in ../constants/.

Outputs:
  constants/species.csv        - SPECIES_* defines
  constants/items.csv          - ITEM_* defines
  constants/moves.csv          - MOVE_* defines
  constants/abilities.csv      - ABILITY_* defines
  constants/trainerclasses.csv - TRAINERCLASS_* defines
  constants/maps.csv           - MAP_* or HEADER_* defines

Standard-library only.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HG_CONSTANTS = REPO_ROOT / "Tools" / "hg-engine" / "include" / "constants"
DEST_DIR = Path(__file__).resolve().parents[1] / "constants"

# (output_csv_stem, header_file, prefix_filter)
EXTRACTIONS: list[tuple[str, str, str]] = [
    ("species",        "species.h",       "SPECIES_"),
    ("items",          "item.h",          "ITEM_"),
    ("moves",          "moves.h",         "MOVE_"),
    ("abilities",      "ability.h",       "ABILITY_"),
    ("trainerclasses", "trainerclass.h",  "TRAINERCLASS_"),
    ("maps",           "maps.h",          ""),  # all defines in maps.h
]

DEFINE_RE = re.compile(r"^\s*#define\s+(\w+)\s+(\S+)")


def parse_header(path: Path, prefix: str) -> list[tuple[str, str, str]]:
    """Return list of (name, raw_value, resolved_int_or_empty) tuples."""
    if not path.exists():
        print(f"  [SKIP] Not found: {path}")
        return []

    rows: list[tuple[str, str]] = []
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = DEFINE_RE.match(line)
            if not m:
                continue
            name, value = m.group(1), m.group(2)
            if prefix and not name.startswith(prefix):
                continue
            # Skip guard macros (all caps, no digits, no underscore in value)
            if value in ("1", "0") and "_H" in name:
                continue
            rows.append((name, value))

    # Build a name->int dict for resolving symbolic references
    sym: dict[str, int] = {}
    resolved: list[tuple[str, str, str]] = []
    for name, value in rows:
        int_val = _try_resolve(value, sym)
        if int_val is not None:
            sym[name] = int_val
        resolved.append((name, value, str(int_val) if int_val is not None else ""))

    return resolved


def _try_resolve(value: str, sym: dict[str, int]) -> int | None:
    """Try to convert value to int, optionally resolving known symbols."""
    value = value.strip("()")
    # Handle hex
    try:
        return int(value, 0)
    except ValueError:
        pass
    # Handle simple arithmetic: symbol + N
    m = re.match(r"^(\w+)\s*\+\s*(\d+)$", value)
    if m and m.group(1) in sym:
        return sym[m.group(1)] + int(m.group(2))
    m = re.match(r"^(\w+)\s*\-\s*(\d+)$", value)
    if m and m.group(1) in sym:
        return sym[m.group(1)] - int(m.group(2))
    # Direct symbol reference
    if value in sym:
        return sym[value]
    return None


def write_csv(dest: Path, rows: list[tuple[str, str, str]]) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["name", "raw_value", "numeric_id"])
        writer.writerows(rows)


def main() -> None:
    print(f"hg-engine constants: {HG_CONSTANTS}")
    print(f"Output dir         : {DEST_DIR}")
    print()

    for stem, header_file, prefix in EXTRACTIONS:
        header_path = HG_CONSTANTS / header_file
        rows = parse_header(header_path, prefix)
        if rows:
            out = DEST_DIR / f"{stem}.csv"
            write_csv(out, rows)
            print(f"  {len(rows):5d} rows  ->  constants/{stem}.csv")
        else:
            print(f"  [EMPTY]  constants/{stem}.csv")

    print()
    print("Done.")


if __name__ == "__main__":
    main()

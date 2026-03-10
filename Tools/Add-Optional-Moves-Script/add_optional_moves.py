#!/usr/bin/env python3
"""
Add Optional Moves to Trainer Data (stdlib-only)

Expands Trainer-X-Data.csv files from 9-row format to extended format,
populating Optional Move 1-N cells with ALL legal moves from Learnset-Data.csv.

Legal move rules:
  - tm: always legal
  - egg: always legal
  - level-up: legal iff Pokemon Level >= move Level (empty Level = 1)
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEARNSET = REPO_ROOT / "Data" / "Pokemon-Data" / "Learnset-Data.csv"
DEFAULT_TRAINERS_DIR = REPO_ROOT / "Data" / "Trainer-Data" / "Trainers"
TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR = TOOL_DIR / "backups"

# Base row structure (optional moves added dynamically)
BASE_ROW_LABELS = [
    "Species", "Level", "Ability", "Held Item",
    "Move 1", "Move 2", "Move 3", "Move 4",
]


@dataclass
class LearnsetEntry:
    move: str
    method: str
    level: int  # 1 if empty for level-up


def load_learnset(path: Path) -> Dict[str, List[LearnsetEntry]]:
    """
    Load Learnset-Data.csv into species -> list of (move, method, level).
    Deduplicates moves per species.
    """
    learnset: Dict[str, List[LearnsetEntry]] = {}
    seen_per_species: Dict[str, set] = {}

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            species = (row.get("Pokemon") or "").strip().upper()
            move = (row.get("Move") or "").strip().upper()
            method = (row.get("Method") or "").strip().lower()
            level_s = (row.get("Level") or "").strip()

            if not species or not move:
                continue

            level = 1
            if method == "level-up" and level_s.isdigit():
                level = int(level_s)

            if species not in seen_per_species:
                seen_per_species[species] = set()
                learnset[species] = []

            if move not in seen_per_species[species]:
                seen_per_species[species].add(move)
                learnset[species].append(LearnsetEntry(move=move, method=method, level=level))

    return learnset


def get_legal_moves(
    species: str,
    pokemon_level: int,
    learnset: Dict[str, List[LearnsetEntry]],
) -> List[str]:
    """
    Return legal moves for species at given level.
    tm/egg: always legal. level-up: legal iff pokemon_level >= level.
    Tries base form if species variant (e.g. RATTATA_ALOLAN) not found.
    """
    species = species.strip().upper()
    candidates = [species]
    if "_" in species:
        base = species.split("_", 1)[0]
        if base != species:
            candidates.append(base)

    entries: List[LearnsetEntry] = []
    for cand in candidates:
        if cand in learnset:
            entries = learnset[cand]
            break

    if not entries:
        return []

    legal: List[str] = []
    for e in entries:
        if e.method in ("tm", "egg"):
            legal.append(e.move)
        elif e.method == "level-up" and pokemon_level >= e.level:
            legal.append(e.move)

    return legal


def read_trainer_csv(path: Path) -> Optional[Tuple[List[str], Dict[str, List[str]]]]:
    """
    Read trainer CSV. Returns (header_row, row_label -> list of 6 values).
    Supports both old format (Move x4) and new format (Move 1-4, Optional Move 1-N).
    Returns None if missing or malformed.
    """
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows or len(rows[0]) < 2:
        return None

    header = rows[0]
    data: Dict[str, List[str]] = {}
    move_rows: List[List[str]] = []
    optional_move_rows: List[Tuple[int, List[str]]] = []  # (index, vals)

    for r in rows[1:]:
        if not r:
            continue
        label = (r[0] or "").strip()
        vals = [(c or "").strip() for c in r[1:7]]
        while len(vals) < 6:
            vals.append("")

        label_lower = label.lower()
        if label_lower == "move":
            move_rows.append(vals)
        elif label_lower.startswith("move "):
            # "Move 1", "Move 2", etc.
            try:
                num = int(label.split()[-1])
                if 1 <= num <= 4:
                    while len(move_rows) < num:
                        move_rows.append([""] * 6)
                    if len(move_rows) < num:
                        move_rows.append(vals)
                    else:
                        move_rows[num - 1] = vals
            except (ValueError, IndexError):
                pass
        elif label_lower.startswith("optional move "):
            try:
                num = int(label.split()[-1])
                if num >= 1:
                    optional_move_rows.append((num, vals))
            except (ValueError, IndexError):
                pass
        else:
            data[label_lower] = vals

    # Normalize move rows
    while len(move_rows) < 4:
        move_rows.append([""] * 6)
    move_rows = move_rows[:4]

    # Build canonical data
    data["species"] = data.get("species", [""] * 6)
    data["level"] = data.get("level", [""] * 6)
    data["ability"] = data.get("ability", [""] * 6)
    data["held item"] = data.get("held item", [""] * 6)

    for i, vals in enumerate(move_rows):
        key = f"move{i+1}"
        data[key] = vals

    for num, vals in sorted(optional_move_rows, key=lambda x: x[0]):
        data[f"optional_move_{num}"] = vals

    return (header, data)


def write_trainer_csv(
    path: Path,
    header: List[str],
    data: Dict[str, List[str]],
) -> None:
    """Write trainer CSV with base rows + all Optional Move rows from data."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def vals(key: str) -> List[str]:
        v = data.get(key, [""] * 6)
        return [v[i] if i < len(v) else "" for i in range(6)]

    # Map row labels to data keys (read uses label.lower() e.g. "held item")
    def row_key(label: str) -> str:
        k = label.lower()
        if k == "held item":
            return "held item"
        if k in ("move 1", "move 2", "move 3", "move 4"):
            return f"move{k.split()[-1]}"
        return k.replace(" ", "_")

    rows: List[List[str]] = []
    for label in BASE_ROW_LABELS:
        key = row_key(label)
        rows.append([label] + vals(key))

    # Add all optional move rows present in data (sorted by number)
    optional_keys = sorted(
        (k for k in data if k.startswith("optional_move_") and k.split("_")[-1].isdigit()),
        key=lambda k: int(k.split("_")[-1]),
    )
    for key in optional_keys:
        num = key.split("_")[-1]
        rows.append([f"Optional Move {num}"] + vals(key))

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def process_trainer_file(
    path: Path,
    learnset: Dict[str, List[LearnsetEntry]],
    dry_run: bool,
    backup_dir: Optional[Path],
    warnings: List[str],
) -> bool:
    """
    Process a single Trainer-X-Data.csv. Returns True if updated.
    """
    result = read_trainer_csv(path)
    if result is None:
        warnings.append(f"{path}: could not read or parse")
        return False

    header, data = result

    # Ensure we have the full structure
    for i in range(1, 5):
        key = f"move{i}"
        if key not in data:
            data[key] = [""] * 6

    species_list = data.get("species", [""] * 6)
    level_list = data.get("level", [""] * 6)
    current_moves = [data.get(f"move{i}", [""] * 6) for i in range(1, 5)]

    # Build optional pool per Pokemon (col 0-5)
    optional_pools: List[List[str]] = [[] for _ in range(6)]
    for col in range(6):
        species = (species_list[col] or "").strip().upper()
        if not species or species == "NONE":
            continue

        level_s = (level_list[col] or "").strip()
        if level_s.upper() == "VARIES":
            pokemon_level = 100
        elif level_s.isdigit():
            pokemon_level = int(level_s)
        else:
            continue

        legal = get_legal_moves(species, pokemon_level, learnset)
        if not legal:
            warnings.append(f"{path.name} col {col+1} ({species}): no learnset found")

        existing = {current_moves[r][col].strip().upper() for r in range(4)}
        existing.discard("")
        optional_pools[col] = [m for m in legal if m not in existing]

    max_optional = max(len(p) for p in optional_pools) if optional_pools else 0
    if max_optional == 0:
        return False

    # Clear old optional move keys; we will repopulate 1..max_optional
    keys_to_drop = [k for k in list(data.keys()) if k.startswith("optional_move_")]
    for k in keys_to_drop:
        del data[k]

    updated = False
    for i in range(1, max_optional + 1):
        key = f"optional_move_{i}"
        idx = i - 1
        row_vals = []
        for col in range(6):
            new_val = optional_pools[col][idx] if idx < len(optional_pools[col]) else ""
            old_row = data.get(key, [""] * 6)
            old_val = old_row[col] if col < len(old_row) else ""
            if new_val != old_val:
                updated = True
            row_vals.append(new_val)
        data[key] = row_vals

    if not updated:
        return False

    if dry_run:
        return True

    if backup_dir:
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = backup_dir / f"{path.name}.{stamp}"
        shutil.copy2(path, backup_path)

    write_trainer_csv(path, header, data)
    return True


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add Optional Move 1-N cells to Trainer CSV files with ALL legal moves from Learnset-Data.csv.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--learnset", type=Path, default=DEFAULT_LEARNSET, help="Path to Learnset-Data.csv")
    parser.add_argument("--trainers-dir", type=Path, default=DEFAULT_TRAINERS_DIR, help="Path to Trainers directory")
    parser.add_argument("--backup-dir", type=Path, default=None, help="Backup CSVs before overwrite (default: no backup)")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be done without writing")
    args = parser.parse_args(argv)

    if not args.learnset.exists():
        print(f"Error: learnset not found: {args.learnset}")
        return 1
    if not args.trainers_dir.exists():
        print(f"Error: trainers dir not found: {args.trainers_dir}")
        return 1

    learnset = load_learnset(args.learnset)
    print(f"Loaded learnset: {len(learnset)} species, {sum(len(v) for v in learnset.values())} entries")

    warnings: List[str] = []
    updated_count = 0

    for folder in sorted(args.trainers_dir.iterdir()):
        if not folder.is_dir():
            continue
        if folder.name.startswith("T0-"):
            continue
        csv_path = folder / f"Trainer-{folder.name.split('-')[0][1:]}-Data.csv"
        if not csv_path.exists():
            # Try pattern Trainer-{id}-Data.csv
            for p in folder.glob("Trainer-*-Data.csv"):
                csv_path = p
                break
            else:
                continue
        if process_trainer_file(csv_path, learnset, args.dry_run, args.backup_dir, warnings):
            updated_count += 1
            print(f"  {'Would update' if args.dry_run else 'Updated'}: {csv_path.relative_to(args.trainers_dir)}")

    for w in warnings:
        print(f"  Warning: {w}")

    print(f"\n{'Would update' if args.dry_run else 'Updated'}: {updated_count} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

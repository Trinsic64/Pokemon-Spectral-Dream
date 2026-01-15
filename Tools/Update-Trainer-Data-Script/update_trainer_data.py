#!/usr/bin/env python3
"""
Trainer Data Sync Tool (stdlib-only)

Phase A (safe):
  - Parse Data/Trainer-Data/trainers.s
  - Generate per-trainer folders under Data/Trainer-Data/Trainers/
  - Produce mismatch review output under Data/Trainer-Data/Trainers-Mismatch/

Phase B (after review):
  - apply-to-main: Update Trainer-Data-Main.csv from per-trainer folders (backing up the CSV)
  - build-trainers-s: Rebuild trainers.s from per-trainer folders + meta.json (dry-run supported)
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "Data" / "Trainer-Data"
DEFAULT_TRAINERS_S = DATA_ROOT / "trainers.s"
DEFAULT_MAIN_CSV = DATA_ROOT / "Trainer-Data-Main.csv"
DEFAULT_TRAINERS_DIR = DATA_ROOT / "Trainers"
DEFAULT_MISMATCH_DIR = DATA_ROOT / "Trainers-Mismatch"

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR = TOOL_DIR / "backups"
DEFAULT_REPORTS_DIR = TOOL_DIR / "reports"


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------


@dataclass
class Mon:
    index: int
    ivs: Optional[int] = None
    abilityslot: Optional[int] = None
    level: Optional[int] = None
    species: Optional[str] = None  # without SPECIES_ prefix
    species_token: Optional[str] = None  # full token e.g. SPECIES_RATTATA
    form_index: Optional[int] = None  # monwithform form index
    moves: List[str] = None  # without MOVE_ prefix
    ability: Optional[str] = None  # without ABILITY_ prefix
    additionalflags: Optional[str] = None
    ballseal: Optional[str] = None

    def __post_init__(self) -> None:
        if self.moves is None:
            self.moves = []


@dataclass
class Trainer:
    trainer_id: int
    trainer_name: str
    trainermontype: str = ""
    trainerclass: str = ""
    nummons: int = 0
    items: List[str] = None  # ITEM_* tokens
    aiflags: str = ""
    battletype: str = "SINGLE_BATTLE"
    party_id: int = 0
    mons: List[Mon] = None

    def __post_init__(self) -> None:
        if self.items is None:
            self.items = []
        if self.mons is None:
            self.mons = []


# --------------------------------------------------------------------------------------
# Normalization helpers
# --------------------------------------------------------------------------------------


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def strip_prefix(token: str, prefix: str) -> str:
    token = (token or "").strip()
    return token[len(prefix) :] if token.startswith(prefix) else token


_INVALID_FS = re.compile(r"[^A-Z0-9_]+")


def slug_upper(value: str, keep_underscore: bool = True) -> str:
    value = (value or "").strip().upper()
    if keep_underscore:
        value = value.replace(" ", "_")
        value = re.sub(r"[^A-Z0-9_]+", "_", value)
        value = re.sub(r"_+", "_", value).strip("_")
        return value or "UNKNOWN"
    value = re.sub(r"[^A-Z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "UNKNOWN"


def trainer_folder_name(tr: Trainer) -> str:
    class_short = strip_prefix(tr.trainerclass, "TRAINERCLASS_")
    # Keep underscores in class, but collapse anything else to underscores
    class_part = slug_upper(class_short, keep_underscore=True)
    name_part = slug_upper(tr.trainer_name, keep_underscore=False)
    return f"T{tr.trainer_id}-{class_part}-{name_part}"


CSV_BATTLE_SOFT = "Double Battle Soft"
CSV_BATTLE_HARD = "Double Battle Hard"


def battle_mode_from_csv(value: str) -> str:
    """
    Battle Type column semantics:
      - Double Battle Soft: record-only, still SINGLE_BATTLE in trainers.s
      - Double Battle Hard: must be DOUBLE_BATTLE in trainers.s

    Back-compat:
      - legacy 'Double Battle' is treated as SOFT (record-only) unless it says 'hard'.
    """
    v = (value or "").strip().lower()
    if not v:
        return "single"
    if "hard" in v:
        return "hard"
    if "soft" in v:
        return "soft"
    if "double" in v:
        return "soft"
    return "single"


def normalize_level_csv(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if v.upper() == "VARIES":
        return "VARIES"
    return v if v.isdigit() else v


def trainer_level_value(tr: Trainer) -> str:
    levels = [m.level for m in tr.mons if m.level is not None]
    if not levels:
        return "0"
    if all(l == levels[0] for l in levels):
        return str(levels[0])
    return "VARIES"


# --------------------------------------------------------------------------------------
# trainers.s parsing
# --------------------------------------------------------------------------------------


_RE_TRAINERDATA = re.compile(r'^trainerdata\s+(\d+),\s+"(.*)"\s*$')
_RE_PARTY = re.compile(r"^\s*party\s+(\d+)\s*$")
_RE_KEYVAL = re.compile(r"^\s*([a-zA-Z_]+)\s+(.*?)\s*$")
_RE_MON_COMMENT = re.compile(r"^\s*//\s*mon\s+(\d+)\s*$")


def parse_trainers_s(path: Path) -> Tuple[List[str], Dict[int, Trainer]]:
    """
    Returns:
      - header_lines: everything before the first trainerdata
      - trainers_by_id: parsed trainers including party mons
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_lines: List[str] = []
    trainers: Dict[int, Trainer] = {}

    i = 0
    # Capture header until first trainerdata
    while i < len(lines) and not lines[i].startswith("trainerdata "):
        header_lines.append(lines[i])
        i += 1

    current: Optional[Trainer] = None
    in_party = False
    current_mon: Optional[Mon] = None

    def flush_current() -> None:
        nonlocal current, in_party, current_mon
        if current is None:
            return
        # Ensure nummons matches parsed mons when present
        if current.nummons and current.mons and current.nummons != len(current.mons):
            # Prefer parsed mons length
            current.nummons = len(current.mons)
        elif not current.nummons:
            current.nummons = len(current.mons)
        trainers[current.trainer_id] = current
        current = None
        in_party = False
        current_mon = None

    while i < len(lines):
        line = lines[i].rstrip("\n")

        m = _RE_TRAINERDATA.match(line.strip())
        if m:
            flush_current()
            tid = int(m.group(1))
            name = m.group(2)
            current = Trainer(trainer_id=tid, trainer_name=name, party_id=tid)
            i += 1
            continue

        if current is None:
            i += 1
            continue

        if line.strip() == "endentry":
            in_party = False
            current_mon = None
            i += 1
            continue

        party_m = _RE_PARTY.match(line)
        if party_m:
            in_party = True
            current.party_id = int(party_m.group(1))
            current_mon = None
            i += 1
            continue

        if in_party and line.strip() == "endparty":
            in_party = False
            current_mon = None
            i += 1
            continue

        if in_party:
            mon_m = _RE_MON_COMMENT.match(line)
            if mon_m:
                idx = int(mon_m.group(1))
                current_mon = Mon(index=idx)
                current.mons.append(current_mon)
                i += 1
                continue

            kv = _RE_KEYVAL.match(line)
            if kv and current_mon is not None:
                key = kv.group(1).strip().lower()
                value = kv.group(2).strip()
                if key == "ivs":
                    current_mon.ivs = int(value) if value.isdigit() else None
                elif key == "abilityslot":
                    current_mon.abilityslot = int(value) if value.isdigit() else None
                elif key == "level":
                    current_mon.level = int(value) if value.isdigit() else None
                elif key == "pokemon":
                    # pokemon SPECIES_X
                    token = value.split()[0]
                    current_mon.species_token = token
                    current_mon.species = strip_prefix(token, "SPECIES_")
                    current_mon.form_index = None
                elif key == "monwithform":
                    # monwithform SPECIES_X, N
                    parts = [p.strip() for p in value.split(",", 1)]
                    token = parts[0].split()[0]
                    current_mon.species_token = token
                    current_mon.species = strip_prefix(token, "SPECIES_")
                    if len(parts) > 1 and parts[1].isdigit():
                        current_mon.form_index = int(parts[1])
                elif key == "move":
                    token = value.split()[0]
                    current_mon.moves.append(strip_prefix(token, "MOVE_"))
                elif key == "ability":
                    token = value.split()[0]
                    current_mon.ability = strip_prefix(token, "ABILITY_")
                elif key == "additionalflags":
                    current_mon.additionalflags = value
                elif key == "ballseal":
                    current_mon.ballseal = value
            i += 1
            continue

        # trainerdata block fields
        kv = _RE_KEYVAL.match(line)
        if kv:
            key = kv.group(1).strip().lower()
            value = kv.group(2).strip()
            if key == "trainermontype":
                current.trainermontype = value
            elif key == "trainerclass":
                current.trainerclass = value.split()[0]
            elif key == "nummons":
                current.nummons = int(value) if value.isdigit() else 0
            elif key == "item":
                # up to 4 lines, but allow 0..4
                current.items.append(value.split()[0])
            elif key == "aiflags":
                current.aiflags = value
            elif key == "battletype":
                current.battletype = value.split()[0]

        i += 1

    flush_current()
    return header_lines, trainers


# --------------------------------------------------------------------------------------
# Per-trainer CSV (grid) IO
# --------------------------------------------------------------------------------------


GRID_ROWS = ["Species", "Level", "Ability", "Held Item", "Move", "Move", "Move", "Move"]


def write_trainer_grid_csv(path: Path, trainer_id: int, mons: List[Mon]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [f"Pokemon {i}" for i in range(1, 7)]
    header = [f"Trainer {trainer_id}"] + cols

    # Prepare cells per mon up to 6
    mon_cells: List[dict] = []
    for idx in range(6):
        if idx < len(mons):
            m = mons[idx]
            moves = (m.moves or [])[:4]
            moves = moves + [""] * (4 - len(moves))
            mon_cells.append(
                {
                    "Species": m.species or "",
                    "Level": "" if m.level is None else str(m.level),
                    "Ability": m.ability or "",
                    "Held Item": "NONE",
                    "Move1": moves[0],
                    "Move2": moves[1],
                    "Move3": moves[2],
                    "Move4": moves[3],
                }
            )
        else:
            mon_cells.append(
                {
                    "Species": "NONE",
                    "Level": "",
                    "Ability": "",
                    "Held Item": "",
                    "Move1": "",
                    "Move2": "",
                    "Move3": "",
                    "Move4": "",
                }
            )

    rows: List[List[str]] = []

    def row_values(key: str) -> List[str]:
        if key == "Move":
            raise ValueError("Move row handled separately")
        return [mon_cells[i][key] for i in range(6)]

    rows.append(["Species"] + row_values("Species"))
    rows.append(["Level"] + row_values("Level"))
    rows.append(["Ability"] + row_values("Ability"))
    rows.append(["Held Item"] + row_values("Held Item"))
    rows.append(["Move"] + [mon_cells[i]["Move1"] for i in range(6)])
    rows.append(["Move"] + [mon_cells[i]["Move2"] for i in range(6)])
    rows.append(["Move"] + [mon_cells[i]["Move3"] for i in range(6)])
    rows.append(["Move"] + [mon_cells[i]["Move4"] for i in range(6)])

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            w.writerow(r)


def read_trainer_grid_csv(path: Path) -> Optional[List[Mon]]:
    """
    Returns a list of Mons (up to 6) containing species/level/ability/moves (4).
    If file is missing or malformed, returns None.
    """
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows or len(rows[0]) < 2:
        return None

    # Map row label -> list of 6 values
    data: Dict[str, List[str]] = {}
    move_rows: List[List[str]] = []
    for r in rows[1:]:
        if not r:
            continue
        label = (r[0] or "").strip()
        vals = [(c or "").strip() for c in r[1:7]]
        if label.lower() == "move":
            move_rows.append(vals)
        else:
            data[label.lower()] = vals

    if len(move_rows) < 4:
        # pad missing move rows
        while len(move_rows) < 4:
            move_rows.append([""] * 6)

    mons: List[Mon] = []
    for idx in range(6):
        species = (data.get("species", [""] * 6)[idx] or "").strip()
        if not species or species.upper() == "NONE":
            continue
        level_s = (data.get("level", [""] * 6)[idx] or "").strip()
        level = int(level_s) if level_s.isdigit() else None
        ability = (data.get("ability", [""] * 6)[idx] or "").strip()
        moves = [move_rows[r][idx].strip() for r in range(4)]
        moves = [m for m in moves if m]
        m = Mon(index=idx, species=species.strip().upper(), level=level, ability=ability.strip().upper(), moves=moves)
        mons.append(m)
    return mons


# --------------------------------------------------------------------------------------
# Trainer-Data-Main.csv IO
# --------------------------------------------------------------------------------------


def read_main_csv(path: Path) -> Tuple[List[str], List[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return fieldnames, rows


def write_main_csv(path: Path, fieldnames: List[str], rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------------------------------
# Mismatch detection
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mismatch:
    trainer_id: int
    folder: str
    reasons: List[str]


def compare_to_main(trainers: Dict[int, Trainer], main_rows: List[dict]) -> List[Mismatch]:
    main_by_id: Dict[int, dict] = {}
    for row in main_rows:
        raw = (row.get("TrainerID") or "").strip()
        if raw.isdigit():
            main_by_id[int(raw)] = row

    mismatches: List[Mismatch] = []
    all_ids = sorted(set(trainers.keys()) | set(main_by_id.keys()))

    for tid in all_ids:
        tr = trainers.get(tid)
        row = main_by_id.get(tid)

        # ignore template/placeholder trainer 0 comparisons unless explicitly present in CSV
        if tid == 0:
            continue

        reasons: List[str] = []
        if tr is None:
            reasons.append("missing_in_trainers_s")
        if row is None:
            reasons.append("missing_in_main_csv")

        if tr and row:
            name_csv = (row.get("TrainerName") or "").strip()
            if name_csv and name_csv.lower() != tr.trainer_name.strip().lower():
                reasons.append(f"name_diff(csv={name_csv!r}, s={tr.trainer_name!r})")

            class_csv = (row.get("TrainerClass") or "").strip()
            if class_csv and class_csv != tr.trainerclass:
                reasons.append(f"class_diff(csv={class_csv}, s={tr.trainerclass})")

            # Battle type mismatch rules:
            # - SOFT double battles do NOT require DOUBLE_BATTLE in trainers.s
            # - HARD double battles MUST be DOUBLE_BATTLE in trainers.s
            bt_mode = battle_mode_from_csv(row.get("Battle Type") or "")
            if bt_mode == "hard" and tr.battletype != "DOUBLE_BATTLE":
                reasons.append("battle_type_hard_expected_but_trainers_s_single")
            if tr.battletype == "DOUBLE_BATTLE" and bt_mode != "hard":
                reasons.append("battle_type_trainers_s_double_but_csv_not_hard")

            level_csv = normalize_level_csv(row.get("Level") or "")
            level_s = trainer_level_value(tr)
            if level_csv and level_csv != level_s:
                reasons.append(f"level_diff(csv={level_csv}, s={level_s})")

            # species list
            csv_species: List[str] = []
            for i in range(1, 7):
                v = (row.get(f"Pokemon {i}") or "").strip()
                if v:
                    csv_species.append(v.strip().upper())
            s_species = [(m.species or "").strip().upper() for m in tr.mons if (m.species or "").strip()]
            if csv_species and csv_species != s_species:
                reasons.append("species_list_diff")

        if reasons:
            folder = trainer_folder_name(tr) if tr else f"T{tid}-UNKNOWN-UNKNOWN"
            mismatches.append(Mismatch(trainer_id=tid, folder=folder, reasons=reasons))

    return mismatches


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------


def cmd_generate_dirs(args: argparse.Namespace) -> int:
    header_lines, trainers = parse_trainers_s(args.trainers_s)
    trainers_dir: Path = args.trainers_dir
    trainers_dir.mkdir(parents=True, exist_ok=True)

    # Load main CSV for mismatch compare
    _, main_rows = read_main_csv(args.main_csv)

    # Prepare run dirs
    stamp = now_stamp()
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    mismatch_run_dir = Path(args.mismatch_dir) / f"run_{stamp}"

    # Write per-trainer dirs
    written = 0
    skipped_zero = 0
    for tid, tr in sorted(trainers.items(), key=lambda kv: kv[0]):
        if tid == 0:
            skipped_zero += 1
            continue

        folder = trainer_folder_name(tr)
        out_dir = trainers_dir / folder
        out_dir.mkdir(parents=True, exist_ok=True)

        grid_path = out_dir / f"Trainer-{tid}-Data.csv"
        meta_path = out_dir / "meta.json"

        if grid_path.exists() and not args.dry_run:
            # Backup existing per-trainer CSV to tool backups
            backup_dir = Path(args.backup_dir) / "per_trainer"
            backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(grid_path, backup_dir / f"Trainer-{tid}-Data_{stamp}.csv")

        if not args.dry_run:
            write_trainer_grid_csv(grid_path, tid, tr.mons)
            meta_path.write_text(json.dumps(asdict(tr), indent=2, sort_keys=True), encoding="utf-8")
        written += 1

    mismatches = compare_to_main(trainers, main_rows)

    # Write mismatch reports + copies
    report_csv = reports_dir / f"mismatch_report_{stamp}.csv"
    mismatch_report_csv = mismatch_run_dir / "mismatch_report.csv"
    latest_txt = Path(args.mismatch_dir) / "LATEST.txt"

    if not args.dry_run:
        mismatch_run_dir.mkdir(parents=True, exist_ok=True)
        (mismatch_run_dir / "Trainers").mkdir(parents=True, exist_ok=True)

        with report_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["TrainerID", "Folder", "Reasons"])
            for mm in mismatches:
                w.writerow([mm.trainer_id, mm.folder, ";".join(mm.reasons)])

        shutil.copy2(report_csv, mismatch_report_csv)
        latest_txt.write_text(f"run_{stamp}\n", encoding="utf-8")

        # Copy mismatched trainer folders for review (CSV + meta.json are enough)
        for mm in mismatches:
            src = trainers_dir / mm.folder
            dst = mismatch_run_dir / "Trainers" / mm.folder
            if not src.exists():
                continue
            dst.mkdir(parents=True, exist_ok=True)
            for fn in ("meta.json", f"Trainer-{mm.trainer_id}-Data.csv"):
                p = src / fn
                if p.exists():
                    shutil.copy2(p, dst / fn)

    print(
        "\n".join(
            [
                f"trainers.s: {args.trainers_s}",
                f"main csv:   {args.main_csv}",
                f"trainers parsed: {len(trainers)} (skipped zero: {skipped_zero})",
                f"trainer folders written: {written}" + (" (dry-run)" if args.dry_run else ""),
                f"mismatches: {len(mismatches)}",
                f"mismatch output: {mismatch_run_dir}" + (" (dry-run)" if args.dry_run else ""),
                f"report csv: {report_csv}" + (" (dry-run)" if args.dry_run else ""),
            ]
        )
    )
    return 0


def _load_trainer_meta(folder: Path) -> Optional[Trainer]:
    meta = folder / "meta.json"
    if not meta.exists():
        return None
    raw = json.loads(meta.read_text(encoding="utf-8"))
    tr = Trainer(
        trainer_id=int(raw["trainer_id"]),
        trainer_name=raw.get("trainer_name", ""),
        trainermontype=raw.get("trainermontype", ""),
        trainerclass=raw.get("trainerclass", ""),
        nummons=int(raw.get("nummons", 0) or 0),
        items=list(raw.get("items", []) or []),
        aiflags=raw.get("aiflags", ""),
        battletype=raw.get("battletype", "SINGLE_BATTLE"),
        party_id=int(raw.get("party_id", raw.get("trainer_id", 0))),
        mons=[],
    )
    for mraw in raw.get("mons", []) or []:
        tr.mons.append(
            Mon(
                index=int(mraw.get("index", 0)),
                ivs=mraw.get("ivs"),
                abilityslot=mraw.get("abilityslot"),
                level=mraw.get("level"),
                species=mraw.get("species"),
                species_token=mraw.get("species_token"),
                form_index=mraw.get("form_index"),
                moves=list(mraw.get("moves", []) or []),
                ability=mraw.get("ability"),
                additionalflags=mraw.get("additionalflags"),
                ballseal=mraw.get("ballseal"),
            )
        )
    return tr


def cmd_apply_to_main(args: argparse.Namespace) -> int:
    trainers_dir: Path = args.trainers_dir
    fieldnames, rows = read_main_csv(args.main_csv)

    # index existing by TrainerID
    by_id: Dict[int, dict] = {}
    for r in rows:
        tid = (r.get("TrainerID") or "").strip()
        if tid.isdigit():
            by_id[int(tid)] = r

    # backup
    stamp = now_stamp()
    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"Trainer-Data-Main_{stamp}.csv"
    if not args.dry_run:
        shutil.copy2(args.main_csv, backup_path)

    updated = 0
    added = 0
    for folder in sorted(trainers_dir.iterdir()):
        if not folder.is_dir():
            continue
        if folder.name.startswith("T0-"):
            continue
        tr = _load_trainer_meta(folder)
        if tr is None:
            continue

        # Prefer per-trainer CSV for per-mon editable fields
        grid_path = folder / f"Trainer-{tr.trainer_id}-Data.csv"
        grid_mons = read_trainer_grid_csv(grid_path) or []
        if grid_mons:
            # Overlay species/level/ability/moves into meta mons by position
            for idx, gm in enumerate(grid_mons):
                if idx < len(tr.mons):
                    tr.mons[idx].species = gm.species
                    tr.mons[idx].level = gm.level
                    tr.mons[idx].ability = gm.ability
                    tr.mons[idx].moves = gm.moves

        row = by_id.get(tr.trainer_id)
        if row is None:
            row = {k: "" for k in fieldnames}
            row["Trainer#"] = str(tr.trainer_id)
            row["TrainerID"] = str(tr.trainer_id)
            rows.append(row)
            by_id[tr.trainer_id] = row
            added += 1

        row["TrainerName"] = tr.trainer_name
        row["TrainerClass"] = tr.trainerclass
        # Preserve existing Soft flags for SINGLE_BATTLE trainers, but mark HARD when trainers.s is DOUBLE_BATTLE.
        if tr.battletype == "DOUBLE_BATTLE":
            row["Battle Type"] = CSV_BATTLE_HARD
        else:
            existing_bt = (row.get("Battle Type") or "").strip()
            if battle_mode_from_csv(existing_bt) == "soft":
                row["Battle Type"] = CSV_BATTLE_SOFT
            else:
                row["Battle Type"] = ""

        # species list
        species_list = [(m.species or "").strip().upper() for m in tr.mons][:6]
        for i in range(1, 7):
            row[f"Pokemon {i}"] = species_list[i - 1] if i - 1 < len(species_list) else ""

        row["Level"] = trainer_level_value(tr)
        updated += 1

    # stable ordering by TrainerID if present
    def sort_key(r: dict) -> Tuple[int, int]:
        tid = (r.get("TrainerID") or "").strip()
        return (0, int(tid)) if tid.isdigit() else (1, 10**9)

    rows.sort(key=sort_key)

    if not args.dry_run:
        write_main_csv(args.main_csv, fieldnames, rows)

    print(
        "\n".join(
            [
                f"main csv: {args.main_csv}",
                f"backup:   {backup_path}" + (" (dry-run)" if args.dry_run else ""),
                f"trainers updated: {updated}",
                f"rows added: {added}",
            ]
        )
    )
    return 0


def cmd_build_trainers_s(args: argparse.Namespace) -> int:
    trainers_dir: Path = args.trainers_dir
    header_lines, original_trainers = parse_trainers_s(args.trainers_s)

    # Load per-trainer meta + overlays (prefer folder data over original)
    trainers: Dict[int, Trainer] = {}
    for tid, tr in original_trainers.items():
        trainers[tid] = tr

    for folder in sorted(trainers_dir.iterdir()):
        if not folder.is_dir():
            continue
        tr = _load_trainer_meta(folder)
        if tr is None:
            continue
        # overlay editable fields from grid
        grid_path = folder / f"Trainer-{tr.trainer_id}-Data.csv"
        grid_mons = read_trainer_grid_csv(grid_path) or []
        if grid_mons:
            for idx, gm in enumerate(grid_mons):
                if idx < len(tr.mons):
                    tr.mons[idx].species = gm.species
                    tr.mons[idx].level = gm.level
                    tr.mons[idx].ability = gm.ability
                    tr.mons[idx].moves = gm.moves
        trainers[tr.trainer_id] = tr

    out_lines: List[str] = []
    out_lines.extend(header_lines)
    out_lines.append("")  # ensure newline after header

    def emit_trainer(tr: Trainer) -> None:
        out_lines.append(f'trainerdata {tr.trainer_id}, "{tr.trainer_name}"')
        out_lines.append(f"    trainermontype {tr.trainermontype or 'TRAINER_DATA_TYPE_MOVES | TRAINER_DATA_TYPE_ABILITY | TRAINER_DATA_TYPE_ADDITIONAL_FLAGS'}")
        out_lines.append(f"    trainerclass {tr.trainerclass or 'TRAINERCLASS_YOUNGSTER'}")
        out_lines.append(f"    nummons {len(tr.mons)}")
        items = list(tr.items or [])
        while len(items) < 4:
            items.append("ITEM_NONE")
        for i in range(4):
            out_lines.append(f"    item {items[i]}")
        out_lines.append(f"    aiflags {tr.aiflags or 'F_PRIORITIZE_SUPER_EFFECTIVE | F_EVALUATE_ATTACKS | 0'}")
        out_lines.append(f"    battletype {tr.battletype or 'SINGLE_BATTLE'}")
        out_lines.append("    endentry")
        out_lines.append("")
        out_lines.append(f"    party {tr.party_id}")
        for idx, m in enumerate(tr.mons):
            out_lines.append(f"        // mon {idx}")
            out_lines.append(f"        ivs {m.ivs if m.ivs is not None else 250}")
            out_lines.append(f"        abilityslot {m.abilityslot if m.abilityslot is not None else 0}")
            out_lines.append(f"        level {m.level if m.level is not None else 1}")
            species_token = m.species_token or (f"SPECIES_{(m.species or 'NONE')}")
            if m.form_index is not None:
                out_lines.append(f"        monwithform {species_token}, {m.form_index}")
            else:
                out_lines.append(f"        pokemon {species_token}")
            moves = (m.moves or [])[:4]
            moves = moves + ["TACKLE"] * (4 - len(moves))
            for mv in moves:
                out_lines.append(f"        move MOVE_{mv}")
            ability = m.ability or "NONE"
            out_lines.append(f"        ability ABILITY_{ability}")
            out_lines.append(f"        additionalflags {m.additionalflags or '0'}")
            out_lines.append(f"        ballseal {m.ballseal or '0'}")
            if idx != len(tr.mons) - 1:
                out_lines.append("")
        out_lines.append("    endparty")
        out_lines.append("")

    for tid in sorted(trainers.keys()):
        emit_trainer(trainers[tid])

    output = "\n".join(out_lines).rstrip() + "\n"
    if args.dry_run:
        print(f"(dry-run) would write {len(output.splitlines())} lines to {args.trainers_s}")
        return 0

    backup_path = Path(args.backup_dir) / f"trainers_{now_stamp()}.s"
    Path(args.backup_dir).mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.trainers_s, backup_path)
    args.trainers_s.write_text(output, encoding="utf-8", newline="\n")
    print(f"Wrote trainers.s: {args.trainers_s}")
    print(f"Backup: {backup_path}")
    return 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Trainer data tooling for Pokemon Spectral Dream (stdlib-only).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    common.add_argument("--trainers-s", type=Path, default=DEFAULT_TRAINERS_S)
    common.add_argument("--main-csv", type=Path, default=DEFAULT_MAIN_CSV)
    common.add_argument("--trainers-dir", type=Path, default=DEFAULT_TRAINERS_DIR)
    common.add_argument("--mismatch-dir", type=Path, default=DEFAULT_MISMATCH_DIR)
    common.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    common.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    common.add_argument("--dry-run", action="store_true")

    gen = sub.add_parser("generate-dirs", parents=[common], help="Generate per-trainer folders + mismatch report.")
    gen.set_defaults(func=cmd_generate_dirs)

    apply_main = sub.add_parser("apply-to-main", parents=[common], help="Update Trainer-Data-Main.csv from trainer folders (backs up CSV).")
    apply_main.set_defaults(func=cmd_apply_to_main)

    build_s = sub.add_parser("build-trainers-s", parents=[common], help="Rebuild trainers.s from trainer folders + meta.json (dry-run supported).")
    build_s.set_defaults(func=cmd_build_trainers_s)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())


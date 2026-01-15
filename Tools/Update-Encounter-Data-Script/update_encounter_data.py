#!/usr/bin/env python3
"""
Encounter Data Sync Tool (stdlib-only)

- Parses Data/Encounter-Data/encounters.s into encounter banks.
- Generates per-bank folders for precise editing.
  Data/Encounter-Data/Encounters/E####_<Area>/
- Builds new canonical main CSVs:
  Grass/Surf/Fishing/RockSmash
- Can rebuild encounters.s (dry-run supported).

Legacy Data/Encounter-Data/Encounter-Data-Main.csv is not modified.
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
DATA_ROOT = REPO_ROOT / "Data" / "Encounter-Data"
DEFAULT_ENCOUNTERS_S = DATA_ROOT / "encounters.s"
DEFAULT_BANKS_DIR = DATA_ROOT / "Encounters"

HEADER_DATA_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"

TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR = TOOL_DIR / "backups"
DEFAULT_REPORTS_DIR = TOOL_DIR / "reports"


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SpeciesRef:
    species_token: str  # SPECIES_*
    form_index: Optional[int] = None

    @property
    def species(self) -> str:
        token = (self.species_token or "").strip()
        return token[len("SPECIES_") :] if token.startswith("SPECIES_") else token

    def display(self) -> str:
        s = self.species
        if s == "NONE":
            return "NONE"
        if self.form_index is None:
            return s
        return f"{s}@{self.form_index}"

    @staticmethod
    def parse_display(value: str) -> "SpeciesRef":
        v = (value or "").strip()
        if not v or v.upper() == "NONE":
            return SpeciesRef("SPECIES_NONE", None)
        if "@" in v:
            base, f = v.split("@", 1)
            base = base.strip().upper()
            f = f.strip()
            return SpeciesRef(f"SPECIES_{base}", int(f) if f.isdigit() else None)
        return SpeciesRef(f"SPECIES_{v.strip().upper()}", None)


@dataclass(frozen=True)
class EncounterSlot:
    species: SpeciesRef
    min_level: int
    max_level: int

    def display_species(self) -> str:
        return self.species.display()


@dataclass
class EncounterBank:
    bank_id: int
    area_label: str
    walkrate: int = 0
    surfrate: int = 0
    rocksmashrate: int = 0
    oldrodrate: int = 0
    goodrodrate: int = 0
    superrodrate: int = 0
    walklevels: List[int] = None  # 12
    morning: List[SpeciesRef] = None  # 12
    day: List[SpeciesRef] = None  # 12
    night: List[SpeciesRef] = None  # 12
    hoenn: List[SpeciesRef] = None  # 2
    sinnoh: List[SpeciesRef] = None  # 2
    surf: List[EncounterSlot] = None  # 5
    rocksmash: List[EncounterSlot] = None  # 2
    oldrod: List[EncounterSlot] = None  # 5
    goodrod: List[EncounterSlot] = None  # 5
    superrod: List[EncounterSlot] = None  # 5
    swarm_grass: SpeciesRef = None
    swarm_surf: SpeciesRef = None
    swarm_goodrod: SpeciesRef = None
    swarm_superrod: SpeciesRef = None

    def __post_init__(self) -> None:
        if self.walklevels is None:
            self.walklevels = []
        if self.morning is None:
            self.morning = []
        if self.day is None:
            self.day = []
        if self.night is None:
            self.night = []
        if self.hoenn is None:
            self.hoenn = []
        if self.sinnoh is None:
            self.sinnoh = []
        if self.surf is None:
            self.surf = []
        if self.rocksmash is None:
            self.rocksmash = []
        if self.oldrod is None:
            self.oldrod = []
        if self.goodrod is None:
            self.goodrod = []
        if self.superrod is None:
            self.superrod = []
        if self.swarm_grass is None:
            self.swarm_grass = SpeciesRef("SPECIES_NONE", None)
        if self.swarm_surf is None:
            self.swarm_surf = SpeciesRef("SPECIES_NONE", None)
        if self.swarm_goodrod is None:
            self.swarm_goodrod = SpeciesRef("SPECIES_NONE", None)
        if self.swarm_superrod is None:
            self.swarm_superrod = SpeciesRef("SPECIES_NONE", None)


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def slug_area(value: str) -> str:
    v = (value or "").strip().upper()
    v = v.replace(" ", "_")
    v = re.sub(r"[^A-Z0-9_]+", "_", v)
    v = re.sub(r"_+", "_", v).strip("_")
    return v or "UNKNOWN"


def bank_folder_name(bank: EncounterBank) -> str:
    return f"E{bank.bank_id:04d}_{slug_area(bank.area_label)}"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------------------
# Parse encounters.s
# --------------------------------------------------------------------------------------


_RE_BANK = re.compile(r"^encounterdata\s+(\d+)\s*(?://\s*(.*))?$")
_RE_RATE = re.compile(r"^(walkrate|surfrate|rocksmashrate|oldrodrate|goodrodrate|superrodrate)\s+(\d+)\s*$")
_RE_WALKLEVELS = re.compile(r"^walklevels\s+(.+)$")
_RE_POKEMON = re.compile(r"^(pokemon)\s+(SPECIES_[A-Z0-9_]+)\s*$")
_RE_MONWITHFORM = re.compile(r"^monwithform\s+(SPECIES_[A-Z0-9_]+)\s*,\s*(\d+)\s*$")
_RE_ENCOUNTER = re.compile(r"^encounter\s+(SPECIES_[A-Z0-9_]+)\s*,\s*(\d+)\s*,\s*(\d+)\s*$")


def parse_encounters_s(path: Path) -> Tuple[List[str], Dict[int, EncounterBank], List[str]]:
    """
    Returns:
      - header_lines: everything before first encounterdata
      - banks: bank_id -> EncounterBank
      - warnings: human-readable parse warnings
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    header_lines: List[str] = []
    warnings: List[str] = []

    i = 0
    while i < len(lines) and not lines[i].lstrip().startswith("encounterdata"):
        header_lines.append(lines[i])
        i += 1

    banks: Dict[int, EncounterBank] = {}
    current: Optional[EncounterBank] = None
    section: Optional[str] = None

    def flush() -> None:
        nonlocal current, section
        if current is None:
            return
        banks[current.bank_id] = current
        current = None
        section = None

    while i < len(lines):
        raw = lines[i].strip()
        if not raw:
            i += 1
            continue
        if raw == ".close":
            # This file currently contains `.close` mid-stream; we ignore it for parsing purposes.
            i += 1
            continue

        bm = _RE_BANK.match(raw)
        if bm:
            flush()
            bank_id = int(bm.group(1))
            area = (bm.group(2) or "").strip() or f"BANK_{bank_id}"
            current = EncounterBank(bank_id=bank_id, area_label=area)
            section = None
            i += 1
            continue

        if current is None:
            i += 1
            continue

        # Section comments
        if raw.startswith("//"):
            low = raw.lower()
            if "morning encounter slots" in low:
                section = "morning"
            elif "day encounter slots" in low:
                section = "day"
            elif "night encounter slots" in low:
                section = "night"
            elif "hoenn encounter slots" in low:
                section = "hoenn"
            elif "sinnoh encounter slots" in low:
                section = "sinnoh"
            elif "surf encounters" in low:
                section = "surf"
            elif "rock smash encounters" in low:
                section = "rocksmash"
            elif "old rod encounters" in low:
                section = "oldrod"
            elif "good rod encounters" in low:
                section = "goodrod"
            elif "super rod encounters" in low:
                section = "superrod"
            elif "swarm grass" in low:
                section = "swarm_grass"
            elif "swarm surf" in low:
                section = "swarm_surf"
            elif "swarm good rod" in low:
                section = "swarm_goodrod"
            elif "swarm super rod" in low:
                section = "swarm_superrod"
            i += 1
            continue

        # Rates
        rm = _RE_RATE.match(raw)
        if rm:
            key, value = rm.group(1), int(rm.group(2))
            setattr(current, key, value)
            i += 1
            continue

        # Walk levels
        wl = _RE_WALKLEVELS.match(raw)
        if wl:
            nums = [n.strip() for n in wl.group(1).split(",")]
            levels = [int(n) for n in nums if n.isdigit()]
            current.walklevels = levels
            i += 1
            continue

        # pokemon / monwithform
        pm = _RE_POKEMON.match(raw)
        if pm:
            ref = SpeciesRef(pm.group(2), None)
            if section in ("morning", "day", "night", "hoenn", "sinnoh"):
                getattr(current, section).append(ref)
            elif section in ("swarm_grass", "swarm_surf", "swarm_goodrod", "swarm_superrod"):
                setattr(current, section, ref)
            else:
                warnings.append(f"bank {current.bank_id}: pokemon outside known section: {raw}")
            i += 1
            continue

        mw = _RE_MONWITHFORM.match(raw)
        if mw:
            ref = SpeciesRef(mw.group(1), int(mw.group(2)))
            if section in ("morning", "day", "night", "hoenn", "sinnoh"):
                getattr(current, section).append(ref)
            elif section in ("swarm_grass", "swarm_surf", "swarm_goodrod", "swarm_superrod"):
                setattr(current, section, ref)
            else:
                warnings.append(f"bank {current.bank_id}: monwithform outside known section: {raw}")
            i += 1
            continue

        em = _RE_ENCOUNTER.match(raw)
        if em:
            slot = EncounterSlot(SpeciesRef(em.group(1), None), int(em.group(2)), int(em.group(3)))
            if section in ("surf", "rocksmash", "oldrod", "goodrod", "superrod"):
                getattr(current, section).append(slot)
            else:
                warnings.append(f"bank {current.bank_id}: encounter outside known section: {raw}")
            i += 1
            continue

        i += 1

    flush()
    return header_lines, banks, warnings


# --------------------------------------------------------------------------------------
# Header cross-references (which headers use a bank)
# --------------------------------------------------------------------------------------


def load_headers_by_bank(path: Path) -> Dict[int, List[int]]:
    if not path.exists():
        return {}
    by_bank: Dict[int, List[int]] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            hdr_raw = (row.get("HEADER #") or "").strip()
            bank_raw = (row.get("Wild File") or "").strip()
            if not hdr_raw.isdigit() or not bank_raw.isdigit():
                continue
            hid = int(hdr_raw)
            bank = int(bank_raw)
            by_bank.setdefault(bank, []).append(hid)
    for bank, ids in by_bank.items():
        by_bank[bank] = sorted(set(ids))
    return by_bank


# --------------------------------------------------------------------------------------
# Per-bank file writers
# --------------------------------------------------------------------------------------


def write_bank_json(path: Path, bank: EncounterBank) -> None:
    path.write_text(json.dumps(asdict(bank), indent=2, sort_keys=True), encoding="utf-8")


def write_grass_csv(path: Path, bank: EncounterBank) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Slot", "Level", "Morning", "Day", "Night"])
        for idx in range(12):
            level = bank.walklevels[idx] if idx < len(bank.walklevels) else ""
            morn = bank.morning[idx].display() if idx < len(bank.morning) else "NONE"
            day = bank.day[idx].display() if idx < len(bank.day) else "NONE"
            night = bank.night[idx].display() if idx < len(bank.night) else "NONE"
            w.writerow([idx + 1, level, morn, day, night])


def write_regions_csv(path: Path, bank: EncounterBank) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Region", "Slot", "Species"])
        for idx in range(2):
            w.writerow(["Hoenn", idx + 1, bank.hoenn[idx].display() if idx < len(bank.hoenn) else "NONE"])
        for idx in range(2):
            w.writerow(["Sinnoh", idx + 1, bank.sinnoh[idx].display() if idx < len(bank.sinnoh) else "NONE"])


def write_encounter_slots_csv(path: Path, rows: List[EncounterSlot], kind: str, rate: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Rate", "Slot", "Species", "MinLevel", "MaxLevel"])
        for idx, slot in enumerate(rows):
            w.writerow([kind, rate, idx + 1, slot.display_species(), slot.min_level, slot.max_level])


def write_fishing_csv(path: Path, bank: EncounterBank) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["RodType", "Rate", "Slot", "Species", "MinLevel", "MaxLevel"])
        for kind, rate, rows in (
            ("OldRod", bank.oldrodrate, bank.oldrod),
            ("GoodRod", bank.goodrodrate, bank.goodrod),
            ("SuperRod", bank.superrodrate, bank.superrod),
        ):
            for idx, slot in enumerate(rows):
                w.writerow([kind, rate, idx + 1, slot.display_species(), slot.min_level, slot.max_level])


def write_swarms_csv(path: Path, bank: EncounterBank) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["SwarmType", "Species"])
        w.writerow(["Grass", bank.swarm_grass.display()])
        w.writerow(["Surf", bank.swarm_surf.display()])
        w.writerow(["GoodRod", bank.swarm_goodrod.display()])
        w.writerow(["SuperRod", bank.swarm_superrod.display()])


def bank_validation(bank: EncounterBank) -> List[str]:
    issues: List[str] = []
    if len(bank.walklevels) != 12:
        issues.append(f"walklevels_count={len(bank.walklevels)}")
    for key in ("morning", "day", "night"):
        if len(getattr(bank, key)) != 12:
            issues.append(f"{key}_count={len(getattr(bank, key))}")
    if len(bank.hoenn) != 2:
        issues.append(f"hoenn_count={len(bank.hoenn)}")
    if len(bank.sinnoh) != 2:
        issues.append(f"sinnoh_count={len(bank.sinnoh)}")
    if len(bank.surf) != 5:
        issues.append(f"surf_count={len(bank.surf)}")
    if len(bank.rocksmash) != 2:
        issues.append(f"rocksmash_count={len(bank.rocksmash)}")
    for key in ("oldrod", "goodrod", "superrod"):
        if len(getattr(bank, key)) != 5:
            issues.append(f"{key}_count={len(getattr(bank, key))}")
    return issues


# --------------------------------------------------------------------------------------
# Read per-bank CSVs back (overlay for rebuild)
# --------------------------------------------------------------------------------------


def read_grass_csv(path: Path) -> Tuple[List[int], List[SpeciesRef], List[SpeciesRef], List[SpeciesRef]]:
    walklevels: List[int] = []
    morning: List[SpeciesRef] = []
    day: List[SpeciesRef] = []
    night: List[SpeciesRef] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lvl_raw = (row.get("Level") or "").strip()
            walklevels.append(int(lvl_raw) if lvl_raw.isdigit() else 0)
            morning.append(SpeciesRef.parse_display(row.get("Morning") or "NONE"))
            day.append(SpeciesRef.parse_display(row.get("Day") or "NONE"))
            night.append(SpeciesRef.parse_display(row.get("Night") or "NONE"))
    return walklevels, morning, day, night


def read_regions_csv(path: Path) -> Tuple[List[SpeciesRef], List[SpeciesRef]]:
    hoenn: List[SpeciesRef] = []
    sinnoh: List[SpeciesRef] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            region = (row.get("Region") or "").strip().lower()
            species = SpeciesRef.parse_display(row.get("Species") or "NONE")
            if region == "hoenn":
                hoenn.append(species)
            elif region == "sinnoh":
                sinnoh.append(species)
    return hoenn[:2], sinnoh[:2]


def read_simple_slots_csv(path: Path) -> List[EncounterSlot]:
    slots: List[EncounterSlot] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            species = SpeciesRef.parse_display(row.get("Species") or "NONE")
            min_lv = int((row.get("MinLevel") or "0").strip() or 0)
            max_lv = int((row.get("MaxLevel") or "0").strip() or 0)
            slots.append(EncounterSlot(species, min_lv, max_lv))
    return slots


def read_fishing_csv(path: Path) -> Tuple[List[EncounterSlot], List[EncounterSlot], List[EncounterSlot]]:
    oldrod: List[EncounterSlot] = []
    goodrod: List[EncounterSlot] = []
    superrod: List[EncounterSlot] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rod = (row.get("RodType") or "").strip().lower()
            species = SpeciesRef.parse_display(row.get("Species") or "NONE")
            min_lv = int((row.get("MinLevel") or "0").strip() or 0)
            max_lv = int((row.get("MaxLevel") or "0").strip() or 0)
            slot = EncounterSlot(species, min_lv, max_lv)
            if rod == "oldrod":
                oldrod.append(slot)
            elif rod == "goodrod":
                goodrod.append(slot)
            elif rod == "superrod":
                superrod.append(slot)
    return oldrod, goodrod, superrod


def read_swarms_csv(path: Path) -> Tuple[SpeciesRef, SpeciesRef, SpeciesRef, SpeciesRef]:
    swarm_grass = SpeciesRef("SPECIES_NONE", None)
    swarm_surf = SpeciesRef("SPECIES_NONE", None)
    swarm_good = SpeciesRef("SPECIES_NONE", None)
    swarm_super = SpeciesRef("SPECIES_NONE", None)
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            st = (row.get("SwarmType") or "").strip().lower()
            sp = SpeciesRef.parse_display(row.get("Species") or "NONE")
            if st == "grass":
                swarm_grass = sp
            elif st == "surf":
                swarm_surf = sp
            elif st == "goodrod":
                swarm_good = sp
            elif st == "superrod":
                swarm_super = sp
    return swarm_grass, swarm_surf, swarm_good, swarm_super


# --------------------------------------------------------------------------------------
# Build main CSVs
# --------------------------------------------------------------------------------------


def backup_if_exists(path: Path, backup_dir: Path, stamp: str) -> None:
    if not path.exists():
        return
    ensure_dir(backup_dir)
    shutil.copy2(path, backup_dir / f"{path.stem}_{stamp}{path.suffix}")


def write_grass_main_csv(path: Path, banks: List[EncounterBank], headers_by_bank: Dict[int, List[int]], backup_dir: Path, stamp: str) -> None:
    backup_if_exists(path, backup_dir, stamp)
    level_cols = [f"Level{i}" for i in range(1, 13)]
    slot_cols = [f"Slot{i}" for i in range(1, 13)]
    fieldnames = ["BankId", "Area", "Time", "WalkRate"] + level_cols + slot_cols + ["HeadersUsed"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for bank in banks:
            levels = [(bank.walklevels[i] if i < len(bank.walklevels) else "") for i in range(12)]
            for time_key, species_list in (("Morn", bank.morning), ("Day", bank.day), ("Night", bank.night)):
                row: Dict[str, object] = {
                    "BankId": bank.bank_id,
                    "Area": bank.area_label,
                    "Time": time_key,
                    "WalkRate": bank.walkrate,
                    "HeadersUsed": ";".join(str(h) for h in headers_by_bank.get(bank.bank_id, [])),
                }
                for i in range(12):
                    row[f"Level{i+1}"] = levels[i]
                    row[f"Slot{i+1}"] = species_list[i].display() if i < len(species_list) else "NONE"
                w.writerow(row)


def write_surf_main_csv(path: Path, banks: List[EncounterBank], headers_by_bank: Dict[int, List[int]], backup_dir: Path, stamp: str) -> None:
    backup_if_exists(path, backup_dir, stamp)
    fieldnames = ["BankId", "Area", "SurfRate"]
    for i in range(1, 6):
        fieldnames.extend([f"Slot{i}Species", f"Slot{i}Min", f"Slot{i}Max"])
    fieldnames.append("HeadersUsed")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for bank in banks:
            row: Dict[str, object] = {
                "BankId": bank.bank_id,
                "Area": bank.area_label,
                "SurfRate": bank.surfrate,
                "HeadersUsed": ";".join(str(h) for h in headers_by_bank.get(bank.bank_id, [])),
            }
            for i in range(5):
                slot = bank.surf[i] if i < len(bank.surf) else EncounterSlot(SpeciesRef("SPECIES_NONE", None), 0, 0)
                row[f"Slot{i+1}Species"] = slot.display_species()
                row[f"Slot{i+1}Min"] = slot.min_level
                row[f"Slot{i+1}Max"] = slot.max_level
            w.writerow(row)


def write_rocksmash_main_csv(path: Path, banks: List[EncounterBank], headers_by_bank: Dict[int, List[int]], backup_dir: Path, stamp: str) -> None:
    backup_if_exists(path, backup_dir, stamp)
    fieldnames = ["BankId", "Area", "RockSmashRate"]
    for i in range(1, 3):
        fieldnames.extend([f"Slot{i}Species", f"Slot{i}Min", f"Slot{i}Max"])
    fieldnames.append("HeadersUsed")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for bank in banks:
            row: Dict[str, object] = {
                "BankId": bank.bank_id,
                "Area": bank.area_label,
                "RockSmashRate": bank.rocksmashrate,
                "HeadersUsed": ";".join(str(h) for h in headers_by_bank.get(bank.bank_id, [])),
            }
            for i in range(2):
                slot = bank.rocksmash[i] if i < len(bank.rocksmash) else EncounterSlot(SpeciesRef("SPECIES_NONE", None), 0, 0)
                row[f"Slot{i+1}Species"] = slot.display_species()
                row[f"Slot{i+1}Min"] = slot.min_level
                row[f"Slot{i+1}Max"] = slot.max_level
            w.writerow(row)


def write_fishing_main_csv(path: Path, banks: List[EncounterBank], headers_by_bank: Dict[int, List[int]], backup_dir: Path, stamp: str) -> None:
    backup_if_exists(path, backup_dir, stamp)
    fieldnames = ["BankId", "Area", "RodType", "Rate"]
    for i in range(1, 6):
        fieldnames.extend([f"Slot{i}Species", f"Slot{i}Min", f"Slot{i}Max"])
    fieldnames.append("HeadersUsed")
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for bank in banks:
            for rod_type, rate, slots in (
                ("OldRod", bank.oldrodrate, bank.oldrod),
                ("GoodRod", bank.goodrodrate, bank.goodrod),
                ("SuperRod", bank.superrodrate, bank.superrod),
            ):
                row: Dict[str, object] = {
                    "BankId": bank.bank_id,
                    "Area": bank.area_label,
                    "RodType": rod_type,
                    "Rate": rate,
                    "HeadersUsed": ";".join(str(h) for h in headers_by_bank.get(bank.bank_id, [])),
                }
                for i in range(5):
                    slot = slots[i] if i < len(slots) else EncounterSlot(SpeciesRef("SPECIES_NONE", None), 0, 0)
                    row[f"Slot{i+1}Species"] = slot.display_species()
                    row[f"Slot{i+1}Min"] = slot.min_level
                    row[f"Slot{i+1}Max"] = slot.max_level
                w.writerow(row)


# --------------------------------------------------------------------------------------
# Rebuild encounters.s
# --------------------------------------------------------------------------------------


def emit_species_line(ref: SpeciesRef) -> str:
    if ref.form_index is None:
        return f"pokemon {ref.species_token}"
    return f"monwithform {ref.species_token}, {ref.form_index}"


def emit_encounter_line(slot: EncounterSlot) -> str:
    return f"encounter {slot.species.species_token}, {slot.min_level}, {slot.max_level}"


def build_encounters_s_text(header_lines: List[str], banks: List[EncounterBank]) -> str:
    out: List[str] = []
    out.extend(header_lines)
    out.append("")
    out.append("// Auto-generated from per-bank encounter folders")
    out.append("")
    for bank in banks:
        out.append(f"encounterdata   {bank.bank_id}   // {bank.area_label}")
        out.append("")
        out.append(f"walkrate {bank.walkrate}")
        out.append(f"surfrate {bank.surfrate}")
        out.append(f"rocksmashrate {bank.rocksmashrate}")
        out.append(f"oldrodrate {bank.oldrodrate}")
        out.append(f"goodrodrate {bank.goodrodrate}")
        out.append(f"superrodrate {bank.superrodrate}")
        levels = ", ".join(str(n) for n in (bank.walklevels[:12] + [0] * 12)[:12])
        out.append(f"walklevels {levels}")
        out.append("")
        out.append("// morning encounter slots")
        for ref in (bank.morning[:12] + [SpeciesRef('SPECIES_NONE', None)] * 12)[:12]:
            out.append(emit_species_line(ref))
        out.append("")
        out.append("// day encounter slots")
        for ref in (bank.day[:12] + [SpeciesRef('SPECIES_NONE', None)] * 12)[:12]:
            out.append(emit_species_line(ref))
        out.append("")
        out.append("// night encounter slots")
        for ref in (bank.night[:12] + [SpeciesRef('SPECIES_NONE', None)] * 12)[:12]:
            out.append(emit_species_line(ref))
        out.append("")
        out.append("// hoenn encounter slots")
        for ref in (bank.hoenn[:2] + [SpeciesRef('SPECIES_NONE', None)] * 2)[:2]:
            out.append(emit_species_line(ref))
        out.append("")
        out.append("// sinnoh encounter slots")
        for ref in (bank.sinnoh[:2] + [SpeciesRef('SPECIES_NONE', None)] * 2)[:2]:
            out.append(emit_species_line(ref))
        out.append("")
        out.append("// surf encounters")
        for slot in (bank.surf[:5] + [EncounterSlot(SpeciesRef('SPECIES_NONE', None), 0, 0)] * 5)[:5]:
            out.append(emit_encounter_line(slot))
        out.append("")
        out.append("// rock smash encounters")
        for slot in (bank.rocksmash[:2] + [EncounterSlot(SpeciesRef('SPECIES_NONE', None), 0, 0)] * 2)[:2]:
            out.append(emit_encounter_line(slot))
        out.append("")
        out.append("// old rod encounters")
        for slot in (bank.oldrod[:5] + [EncounterSlot(SpeciesRef('SPECIES_NONE', None), 0, 0)] * 5)[:5]:
            out.append(emit_encounter_line(slot))
        out.append("")
        out.append("// good rod encounters")
        for slot in (bank.goodrod[:5] + [EncounterSlot(SpeciesRef('SPECIES_NONE', None), 0, 0)] * 5)[:5]:
            out.append(emit_encounter_line(slot))
        out.append("")
        out.append("// super rod encounters")
        for slot in (bank.superrod[:5] + [EncounterSlot(SpeciesRef('SPECIES_NONE', None), 0, 0)] * 5)[:5]:
            out.append(emit_encounter_line(slot))
        out.append("")
        out.append("// swarm grass")
        out.append(emit_species_line(bank.swarm_grass))
        out.append("// swarm surf")
        out.append(emit_species_line(bank.swarm_surf))
        out.append("// swarm good rod")
        out.append(emit_species_line(bank.swarm_goodrod))
        out.append("// swarm super rod")
        out.append(emit_species_line(bank.swarm_superrod))
        out.append("")
    out.append(".close")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------


def cmd_generate_dirs(args: argparse.Namespace) -> int:
    header_lines, banks_map, warnings = parse_encounters_s(args.encounters_s)
    headers_by_bank = load_headers_by_bank(args.headers_csv)
    banks_dir: Path = args.banks_dir
    ensure_dir(banks_dir)

    stamp = now_stamp()
    reports_dir: Path = args.reports_dir
    ensure_dir(reports_dir)

    issues_rows: List[Tuple[int, str, str]] = []
    written = 0

    for bank_id in sorted(banks_map.keys()):
        bank = banks_map[bank_id]
        folder = bank_folder_name(bank)
        out_dir = banks_dir / folder
        ensure_dir(out_dir)

        issues = bank_validation(bank)
        if issues:
            issues_rows.append((bank_id, folder, ";".join(issues)))

        if not args.dry_run:
            write_bank_json(out_dir / "bank.json", bank)
            write_grass_csv(out_dir / "Grass.csv", bank)
            write_regions_csv(out_dir / "Regions.csv", bank)
            write_encounter_slots_csv(out_dir / "Surf.csv", bank.surf, "Surf", bank.surfrate)
            write_encounter_slots_csv(out_dir / "RockSmash.csv", bank.rocksmash, "RockSmash", bank.rocksmashrate)
            write_fishing_csv(out_dir / "Fishing.csv", bank)
            write_swarms_csv(out_dir / "Swarms.csv", bank)

            used = headers_by_bank.get(bank.bank_id, [])
            readme = [
                f"# Encounter Bank {bank.bank_id:04d} — {bank.area_label}",
                "",
                "## Rates",
                f"- walkrate: `{bank.walkrate}`",
                f"- surfrate: `{bank.surfrate}`",
                f"- rocksmashrate: `{bank.rocksmashrate}`",
                f"- oldrodrate: `{bank.oldrodrate}`",
                f"- goodrodrate: `{bank.goodrodrate}`",
                f"- superrodrate: `{bank.superrodrate}`",
                "",
                "## Used by headers (Wild File)",
                f"- Headers: `{', '.join(str(h) for h in used) if used else '(none)'}`",
                "",
                "## Files in this folder",
                "- `bank.json` (lossless source-of-truth)",
                "- `Grass.csv`, `Surf.csv`, `Fishing.csv`, `RockSmash.csv`, `Swarms.csv`, `Regions.csv`",
            ]
            (out_dir / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
        written += 1

    if not args.dry_run:
        if warnings:
            (reports_dir / f"parse_warnings_{stamp}.txt").write_text("\n".join(warnings) + "\n", encoding="utf-8")
        if issues_rows:
            with (reports_dir / f"bank_issues_{stamp}.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["BankId", "Folder", "Issues"])
                w.writerows(issues_rows)

    print(
        "\n".join(
            [
                f"encounters.s: {args.encounters_s}",
                f"banks parsed: {len(banks_map)}",
                f"banks dir:    {banks_dir}",
                f"folders written: {written}" + (" (dry-run)" if args.dry_run else ""),
                f"warnings: {len(warnings)}",
                f"banks with issues: {len(issues_rows)}",
            ]
        )
    )
    return 0


def cmd_build_mains(args: argparse.Namespace) -> int:
    banks_dir: Path = args.banks_dir
    headers_by_bank = load_headers_by_bank(args.headers_csv)
    stamp = now_stamp()

    banks: List[EncounterBank] = []
    for entry in banks_dir.iterdir():
        if not entry.is_dir():
            continue
        bank_json = entry / "bank.json"
        if not bank_json.exists():
            continue
        raw = json.loads(bank_json.read_text(encoding="utf-8"))
        # reconstruct EncounterBank with nested types
        bank = EncounterBank(bank_id=int(raw["bank_id"]), area_label=raw.get("area_label", f"BANK_{raw['bank_id']}"))
        for k in ("walkrate", "surfrate", "rocksmashrate", "oldrodrate", "goodrodrate", "superrodrate"):
            setattr(bank, k, int(raw.get(k, 0) or 0))
        bank.walklevels = list(raw.get("walklevels", []) or [])
        bank.morning = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("morning", []) or []]
        bank.day = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("day", []) or []]
        bank.night = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("night", []) or []]
        bank.hoenn = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("hoenn", []) or []]
        bank.sinnoh = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("sinnoh", []) or []]
        bank.surf = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("surf", []) or []]
        bank.rocksmash = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("rocksmash", []) or []]
        bank.oldrod = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("oldrod", []) or []]
        bank.goodrod = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("goodrod", []) or []]
        bank.superrod = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("superrod", []) or []]
        bank.swarm_grass = SpeciesRef(raw.get("swarm_grass", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_grass", {}).get("form_index"))
        bank.swarm_surf = SpeciesRef(raw.get("swarm_surf", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_surf", {}).get("form_index"))
        bank.swarm_goodrod = SpeciesRef(raw.get("swarm_goodrod", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_goodrod", {}).get("form_index"))
        bank.swarm_superrod = SpeciesRef(raw.get("swarm_superrod", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_superrod", {}).get("form_index"))

        # Overlay edited CSVs if present
        grass_csv = entry / "Grass.csv"
        if grass_csv.exists():
            wl, m, d, n = read_grass_csv(grass_csv)
            bank.walklevels = wl
            bank.morning, bank.day, bank.night = m, d, n
        regions_csv = entry / "Regions.csv"
        if regions_csv.exists():
            ho, si = read_regions_csv(regions_csv)
            bank.hoenn, bank.sinnoh = ho, si
        surf_csv = entry / "Surf.csv"
        if surf_csv.exists():
            bank.surf = read_simple_slots_csv(surf_csv)
        rock_csv = entry / "RockSmash.csv"
        if rock_csv.exists():
            bank.rocksmash = read_simple_slots_csv(rock_csv)
        fish_csv = entry / "Fishing.csv"
        if fish_csv.exists():
            bank.oldrod, bank.goodrod, bank.superrod = read_fishing_csv(fish_csv)
        sw_csv = entry / "Swarms.csv"
        if sw_csv.exists():
            bank.swarm_grass, bank.swarm_surf, bank.swarm_goodrod, bank.swarm_superrod = read_swarms_csv(sw_csv)

        banks.append(bank)

    banks.sort(key=lambda b: b.bank_id)
    backup_dir: Path = args.backup_dir
    ensure_dir(backup_dir)

    grass_path = DATA_ROOT / "Grass-Encounter-Data-Main.csv"
    surf_path = DATA_ROOT / "Surf-Encounter-Data-Main.csv"
    fish_path = DATA_ROOT / "Fishing-Encounter-Data-Main.csv"
    rock_path = DATA_ROOT / "RockSmash-Encounter-Data-Main.csv"

    if not args.dry_run:
        write_grass_main_csv(grass_path, banks, headers_by_bank, backup_dir, stamp)
        write_surf_main_csv(surf_path, banks, headers_by_bank, backup_dir, stamp)
        write_fishing_main_csv(fish_path, banks, headers_by_bank, backup_dir, stamp)
        write_rocksmash_main_csv(rock_path, banks, headers_by_bank, backup_dir, stamp)

    print(
        "\n".join(
            [
                f"banks dir: {banks_dir}",
                f"banks loaded: {len(banks)}",
                f"wrote mains: " + ("(dry-run)" if args.dry_run else "OK"),
                f"- {grass_path}",
                f"- {surf_path}",
                f"- {fish_path}",
                f"- {rock_path}",
            ]
        )
    )
    return 0


def cmd_build_encounters_s(args: argparse.Namespace) -> int:
    header_lines, _, _ = parse_encounters_s(args.encounters_s)
    banks_dir: Path = args.banks_dir

    banks: List[EncounterBank] = []
    for entry in banks_dir.iterdir():
        if not entry.is_dir():
            continue
        bank_json = entry / "bank.json"
        if not bank_json.exists():
            continue
        raw = json.loads(bank_json.read_text(encoding="utf-8"))
        bank = EncounterBank(bank_id=int(raw["bank_id"]), area_label=raw.get("area_label", f"BANK_{raw['bank_id']}"))
        for k in ("walkrate", "surfrate", "rocksmashrate", "oldrodrate", "goodrodrate", "superrodrate"):
            setattr(bank, k, int(raw.get(k, 0) or 0))
        bank.walklevels = list(raw.get("walklevels", []) or [])
        bank.morning = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("morning", []) or []]
        bank.day = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("day", []) or []]
        bank.night = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("night", []) or []]
        bank.hoenn = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("hoenn", []) or []]
        bank.sinnoh = [SpeciesRef(r["species_token"], r.get("form_index")) for r in raw.get("sinnoh", []) or []]
        bank.surf = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("surf", []) or []]
        bank.rocksmash = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("rocksmash", []) or []]
        bank.oldrod = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("oldrod", []) or []]
        bank.goodrod = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("goodrod", []) or []]
        bank.superrod = [EncounterSlot(SpeciesRef(s["species"]["species_token"], s["species"].get("form_index")), int(s["min_level"]), int(s["max_level"])) for s in raw.get("superrod", []) or []]
        bank.swarm_grass = SpeciesRef(raw.get("swarm_grass", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_grass", {}).get("form_index"))
        bank.swarm_surf = SpeciesRef(raw.get("swarm_surf", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_surf", {}).get("form_index"))
        bank.swarm_goodrod = SpeciesRef(raw.get("swarm_goodrod", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_goodrod", {}).get("form_index"))
        bank.swarm_superrod = SpeciesRef(raw.get("swarm_superrod", {}).get("species_token", "SPECIES_NONE"), raw.get("swarm_superrod", {}).get("form_index"))

        # Overlay editable CSVs if present
        grass_csv = entry / "Grass.csv"
        if grass_csv.exists():
            wl, m, d, n = read_grass_csv(grass_csv)
            bank.walklevels = wl
            bank.morning, bank.day, bank.night = m, d, n
        regions_csv = entry / "Regions.csv"
        if regions_csv.exists():
            ho, si = read_regions_csv(regions_csv)
            bank.hoenn, bank.sinnoh = ho, si
        surf_csv = entry / "Surf.csv"
        if surf_csv.exists():
            bank.surf = read_simple_slots_csv(surf_csv)
        rock_csv = entry / "RockSmash.csv"
        if rock_csv.exists():
            bank.rocksmash = read_simple_slots_csv(rock_csv)
        fish_csv = entry / "Fishing.csv"
        if fish_csv.exists():
            bank.oldrod, bank.goodrod, bank.superrod = read_fishing_csv(fish_csv)
        sw_csv = entry / "Swarms.csv"
        if sw_csv.exists():
            bank.swarm_grass, bank.swarm_surf, bank.swarm_goodrod, bank.swarm_superrod = read_swarms_csv(sw_csv)

        banks.append(bank)

    banks.sort(key=lambda b: b.bank_id)
    text = build_encounters_s_text(header_lines, banks)

    if args.dry_run:
        print(f"(dry-run) would write {len(text.splitlines())} lines")
        return 0

    stamp = now_stamp()
    backup_dir: Path = args.backup_dir
    ensure_dir(backup_dir)
    backup_path = backup_dir / f"encounters_{stamp}.s"
    shutil.copy2(args.encounters_s, backup_path)

    output_path: Path = args.output or args.encounters_s
    output_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote: {output_path}")
    print(f"Backup: {backup_path}")
    return 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Encounter data tooling for Pokemon Spectral Dream (stdlib-only).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--encounters-s", type=Path, default=DEFAULT_ENCOUNTERS_S)
    common.add_argument("--banks-dir", type=Path, default=DEFAULT_BANKS_DIR)
    common.add_argument("--headers-csv", type=Path, default=HEADER_DATA_CSV)
    common.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    common.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    common.add_argument("--dry-run", action="store_true")

    gen = sub.add_parser("generate-dirs", parents=[common], help="Generate per-bank folders + editable CSVs + bank.json.")
    gen.set_defaults(func=cmd_generate_dirs)

    mains = sub.add_parser("build-mains", parents=[common], help="Build new main encounter CSVs from per-bank folders.")
    mains.set_defaults(func=cmd_build_mains)

    bld = sub.add_parser("build-encounters-s", parents=[common], help="Rebuild encounters.s from per-bank folders (dry-run supported).")
    bld.add_argument("--output", type=Path, default=None, help="Optional output path (defaults to encounters.s).")
    bld.set_defaults(func=cmd_build_encounters_s)

    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())


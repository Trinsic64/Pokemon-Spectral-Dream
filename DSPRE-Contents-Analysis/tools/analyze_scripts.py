#!/usr/bin/env python3
"""
analyze_scripts.py

Parses all .script files in ../scripts/ and generates:
  analysis/script-summary.csv  - per-file summary of commands, IDs referenced
  analysis/script-commands.csv - every command occurrence with context

Cross-references:
  - constants/items.csv    for GiveItem / TakeItem / CheckItem
  - constants/species.csv  for GivePokemon / CheckPokemon
  - constants/moves.csv    for move references
  - Data/Header-Data/Header-Data-Main.csv  to map script# -> map names

Standard-library only.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ANALYSIS_ROOT / "scripts"
CONSTANTS_DIR = ANALYSIS_ROOT / "constants"
ANALYSIS_DIR = ANALYSIS_ROOT / "analysis"
HEADER_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"

# Commands that reference items (arg position 0 = item id)
ITEM_COMMANDS = {"GiveItem", "TakeItem", "CheckItem", "CheckPocket", "GiveItemMultiple"}
# Commands that reference species
POKEMON_COMMANDS = {"GivePokemon", "CheckPokemon", "WildBattle", "Poke2Battle"}
# Commands that reference flags
FLAG_COMMANDS = {"CheckFlag", "SetFlag", "ClearFlag"}
# Commands that reference variables
VAR_COMMANDS = {"SetVar", "CheckVar", "AddVar", "CopyVar"}
# Commands that reference text
MSG_COMMANDS = {"Message", "MessageInstant", "MultiMessage"}


def load_csv_lookup(path: Path, key_col: str, val_col: str) -> dict[str, str]:
    """Load a CSV into a {key: value} dict. Returns empty dict if file missing."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    with path.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            k = row.get(key_col, "").strip()
            v = row.get(val_col, "").strip()
            if k:
                result[k] = v
    return result


def load_header_script_map(header_csv: Path) -> dict[str, list[str]]:
    """Return {script_file_number_str: [map_name, ...]} from Header-Data-Main.csv.

    Keys are zero-padded to 4 digits to match filenames like '0742'.
    """
    mapping: dict[str, list[str]] = defaultdict(list)
    if not header_csv.exists():
        return mapping
    with header_csv.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            script_ref = row.get("Script File", "").strip()
            internal_name = row.get("Internal Name", "").strip()
            if script_ref and internal_name:
                # Normalize to 4-digit zero-padded string
                try:
                    key = str(int(script_ref)).zfill(4)
                except ValueError:
                    key = script_ref
                mapping[key].append(internal_name)
    return mapping


def parse_script_file(path: Path) -> dict:
    """Parse a single .script file and return extracted info."""
    info: dict = {
        "file": path.stem,
        "script_count": 0,
        "function_count": 0,
        "action_count": 0,
        "message_refs": [],
        "item_refs": [],
        "pokemon_refs": [],
        "flag_refs": [],
        "var_refs": [],
        "commands": [],
        "all_commands": defaultdict(int),
    }

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return info

    lines = text.splitlines()
    current_section = None

    for line in lines:
        stripped = line.strip()

        # Track section headers
        if stripped.startswith("Script ") and stripped.endswith(":"):
            info["script_count"] += 1
            current_section = "script"
            continue
        if "FUNCTIONS" in stripped or stripped.startswith("Function "):
            if stripped.endswith(":"):
                info["function_count"] += 1
            current_section = "function"
            continue
        if "ACTIONS" in stripped or stripped.startswith("Action "):
            if stripped.endswith(":"):
                info["action_count"] += 1
            current_section = "action"
            continue

        if not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        # Parse command line: CommandName [args...]
        parts = stripped.split()
        if not parts:
            continue
        cmd = parts[0]
        args = parts[1:]

        info["all_commands"][cmd] += 1
        info["commands"].append((cmd, args, current_section))

        # Extract specific references
        if cmd in MSG_COMMANDS and args:
            for a in args:
                if re.match(r"^\d+$", a):
                    info["message_refs"].append(int(a))

        if cmd in ITEM_COMMANDS and args:
            info["item_refs"].append(args[0])

        if cmd in POKEMON_COMMANDS and args:
            info["pokemon_refs"].append(args[0])

        if cmd in FLAG_COMMANDS and args:
            info["flag_refs"].append(args[0])

        if cmd in VAR_COMMANDS and args:
            info["var_refs"].append(args[0])

    return info


def resolve_name(id_str: str, lookup_by_name: dict[str, str], lookup_by_num: dict[str, str]) -> str:
    """Try to resolve a species/item/move name or numeric ID to a friendly name."""
    # Already symbolic
    if id_str in lookup_by_name:
        return lookup_by_name[id_str]
    # Numeric
    if id_str in lookup_by_num:
        return lookup_by_num[id_str]
    return id_str


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # Load constants
    item_by_name = load_csv_lookup(CONSTANTS_DIR / "items.csv", "name", "numeric_id")
    item_by_num = {v: k for k, v in item_by_name.items() if v}
    species_by_name = load_csv_lookup(CONSTANTS_DIR / "species.csv", "name", "numeric_id")
    species_by_num = {v: k for k, v in species_by_name.items() if v}

    # Load header -> script mapping
    script_to_maps = load_header_script_map(HEADER_CSV)

    script_files = sorted(SCRIPTS_DIR.glob("*.script"))
    print(f"Parsing {len(script_files)} script files...")

    summary_rows: list[dict] = []
    command_rows: list[dict] = []

    for sf in script_files:
        info = parse_script_file(sf)
        file_num = sf.stem  # e.g. "0742"

        maps_using = "; ".join(script_to_maps.get(file_num, []))

        item_names = "; ".join(
            resolve_name(i, {}, item_by_num) if re.match(r"^\d+$", i) else i
            for i in info["item_refs"]
        )
        pokemon_names = "; ".join(
            resolve_name(s, {}, species_by_num) if re.match(r"^\d+$", s) else s
            for s in info["pokemon_refs"]
        )
        top_commands = "; ".join(
            f"{cmd}({cnt})" for cmd, cnt in sorted(info["all_commands"].items(), key=lambda x: -x[1])[:10]
        )

        summary_rows.append({
            "script_file": file_num,
            "maps_using_script": maps_using,
            "script_count": info["script_count"],
            "function_count": info["function_count"],
            "action_count": info["action_count"],
            "message_refs": "; ".join(str(m) for m in sorted(set(info["message_refs"]))),
            "item_refs": item_names,
            "pokemon_refs": pokemon_names,
            "flag_refs": "; ".join(sorted(set(info["flag_refs"]))),
            "var_refs": "; ".join(sorted(set(info["var_refs"]))),
            "top_commands": top_commands,
            "total_commands": sum(info["all_commands"].values()),
        })

        for cmd, args, section in info["commands"]:
            command_rows.append({
                "script_file": file_num,
                "section": section or "",
                "command": cmd,
                "args": " ".join(args),
            })

    # Write summary CSV
    summary_out = ANALYSIS_DIR / "script-summary.csv"
    with summary_out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "script_file", "maps_using_script", "script_count", "function_count",
            "action_count", "message_refs", "item_refs", "pokemon_refs",
            "flag_refs", "var_refs", "top_commands", "total_commands",
        ])
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"  -> analysis/script-summary.csv  ({len(summary_rows)} rows)")

    # Write command detail CSV
    cmd_out = ANALYSIS_DIR / "script-commands.csv"
    with cmd_out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["script_file", "section", "command", "args"])
        writer.writeheader()
        writer.writerows(command_rows)
    print(f"  -> analysis/script-commands.csv  ({len(command_rows)} rows)")

    # Write command frequency summary
    cmd_freq: dict[str, int] = defaultdict(int)
    for row in command_rows:
        cmd_freq[row["command"]] += 1
    freq_out = ANALYSIS_DIR / "command-frequency.csv"
    with freq_out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["command", "total_uses"])
        for cmd, cnt in sorted(cmd_freq.items(), key=lambda x: -x[1]):
            writer.writerow([cmd, cnt])
    print(f"  -> analysis/command-frequency.csv  ({len(cmd_freq)} unique commands)")

    print("\nDone.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
build_script_data.py

Builds Script-Data-Main.csv by collecting all script IDs referenced in
Header-Data-Main.csv (Script File and Level Script File columns), parsing
each script file for commands/refs, resolving item/trainer names from
items.inc and trainers.s, and outputting a comprehensive CSV.

Usage:
    python tools/build_script_data.py              # build Script-Data-Main.csv
    python tools/build_script_data.py --output X   # custom output path

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

HEADER_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"
SCRIPTS_DIR = ANALYSIS_ROOT / "scripts"
SCRCMD_CSV = REPO_ROOT / "Data" / "Script-Data" / "SCRCMD Database - HGSS.csv"
ITEMS_CSV = ANALYSIS_ROOT / "constants" / "items.csv"
ITEMS_INC = REPO_ROOT / "Tools" / "hg-engine" / "asm" / "include" / "items.inc"
TRAINERS_S = REPO_ROOT / "Tools" / "hg-engine" / "armips" / "data" / "trainers" / "trainers.s"
OUTPUT_CSV = REPO_ROOT / "Data" / "Script-Data" / "Script-Data-Main.csv"

ITEM_COMMANDS = {"GiveItem", "TakeItem", "CheckItem", "CheckPocket", "GiveItemMultiple"}
TRAINER_COMMANDS = {"SetTrainerFlag", "ClearTrainerFlag", "CheckTrainerFlag"}
FLAG_COMMANDS = {"CheckFlag", "SetFlag", "ClearFlag"}
MSG_COMMANDS = {"Message", "MessageInstant", "MultiMessage", "MessageAll", "MessageFlex", "MessageNoSkip"}
BATTLE_COMMANDS = {"TrainerBattle", "WildBattle", "Poke2Battle"}
WARP_COMMANDS = {"Warp", "SetWarpPosition"}
BOARD_COMMANDS = {"SetTextBoard", "ShowBoard", "BoardMessage", "SetIconBoard"}
MOVEMENT_COMMANDS = {"Movement", "WalkNorth8", "WalkSouth8", "WalkEast8", "WalkWest8", "WaitMovement"}
UI_COMMANDS = {"YesNoBox", "YesNoTouchScreen", "CreateMultiTouchBox", "MultiTouchStandardText"}


def load_header_script_map(header_csv: Path) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, set[str]]]:
    """Return (script->headers, level_script->headers, script->text_archives).
    Keys are 4-digit zero-padded string.
    """
    script_headers: dict[str, list[str]] = defaultdict(list)
    level_headers: dict[str, list[str]] = defaultdict(list)
    script_to_archives: dict[str, set[str]] = defaultdict(set)

    if not header_csv.exists():
        return dict(script_headers), dict(level_headers), dict(script_to_archives)

    with header_csv.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            internal = row.get("Internal Name", "").strip()
            if not internal:
                continue

            def add(ref: str, col: str, arch_col: str) -> None:
                if not ref:
                    return
                try:
                    key = str(int(float(ref))).zfill(4)
                except ValueError:
                    key = ref
                if col == "script":
                    script_headers[key].append(internal)
                else:
                    level_headers[key].append(internal)
                arch = row.get(arch_col, "").strip()
                if arch:
                    script_to_archives[key].add(arch)

            sf = row.get("Script File", "").strip()
            lf = row.get("Level Script File", "").strip()
            ta = "Text Archive"
            if sf:
                add(sf, "script", ta)
            if lf:
                add(lf, "level", ta)

    return dict(script_headers), dict(level_headers), dict(script_to_archives)


def collect_all_script_ids(script_headers: dict, level_headers: dict) -> set[str]:
    """Return all unique script IDs from both maps."""
    return set(script_headers.keys()) | set(level_headers.keys())


def parse_script_file(path: Path) -> dict:
    """Parse a single .script file and return extracted info."""
    info: dict = {
        "script_count": 0,
        "function_count": 0,
        "action_count": 0,
        "message_refs": [],
        "item_refs": [],
        "trainer_refs": [],
        "flag_refs": [],
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

        parts = stripped.split()
        if not parts:
            continue
        cmd = parts[0]
        args = parts[1:]

        info["all_commands"][cmd] += 1

        if cmd in MSG_COMMANDS and args:
            for a in args:
                if re.match(r"^\d+$", a):
                    info["message_refs"].append(int(a))

        if cmd in ITEM_COMMANDS and args:
            info["item_refs"].append(args[0])

        if cmd in TRAINER_COMMANDS and args:
            for a in args:
                if re.match(r"^\d+$", a):
                    info["trainer_refs"].append(int(a))
                elif re.match(r"^0x[0-9A-Fa-f]+$", a):
                    try:
                        info["trainer_refs"].append(int(a, 16))
                    except ValueError:
                        pass

        if cmd in FLAG_COMMANDS and args:
            info["flag_refs"].append(args[0])

    return info


def classify_script(
    all_commands: dict[str, int],
    message_refs: list[int],
    item_refs: list[str],
    trainer_refs: list[str],
    used_as: str,
) -> tuple[str, str, str, str, str]:
    """Classify script into Category, Sub-Category, Template Type, Variables, Description.
    Returns (category, sub_category, template_type, variables, description).
    """
    cmds = set(all_commands.keys())
    has_msg = bool(cmds & MSG_COMMANDS) or bool(message_refs)
    has_item = bool(cmds & ITEM_COMMANDS) or bool(item_refs)
    has_trainer = bool(cmds & TRAINER_COMMANDS) or bool(trainer_refs)
    has_battle = bool(cmds & BATTLE_COMMANDS)
    has_warp = bool(cmds & WARP_COMMANDS)
    has_board = bool(cmds & BOARD_COMMANDS)
    has_movement = bool(cmds & MOVEMENT_COMMANDS)
    has_ui = bool(cmds & UI_COMMANDS)
    has_fade = "FadeScreen" in cmds
    total = sum(all_commands.values())

    is_level = "Level Script File" in used_as
    is_minimal = total <= 3 and "End" in cmds

    # Priority 1: Battle/Trainer
    if has_battle or (has_trainer and ("SetFlag" in cmds or "CheckFlag" in cmds)):
        sub = "Wild Battle" if "WildBattle" in cmds else "Trainer Battle"
        return (
            "Battle",
            sub,
            "Trainer_Battle" if has_trainer else "Wild_Battle",
            "trainer_id; trainer_flag" if has_trainer else "species; level",
            "Battle script with trainer/wild encounter",
        )

    # Priority 2: Item
    if has_item:
        if "GiveItem" in cmds or "GiveItemMultiple" in cmds:
            return "Item", "Give Item", "Give_Item", "item_id; quantity", "Give item to player"
        if "TakeItem" in cmds:
            return "Item", "Take Item", "Take_Item", "item_id; quantity", "Take item from player"
        if "CheckItem" in cmds or "CheckPocket" in cmds:
            return "Item", "Check Item", "Check_Item", "item_id; var_result", "Check if player has item"
        return "Item", "Item Operation", "Item_Op", "item_id", "Item-related script"

    # Priority 3: Warp
    if has_warp:
        return "Warp", "Warp/Transport", "Warp_Player", "map_id; warp_id; x; y", "Warp player to location"

    # Priority 4: Board/Signpost
    if has_board:
        sub = "Signpost" if "SetIconBoard" in cmds else "Trainer Tips"
        return "UI", sub, "Signpost_Board", "msg_slot; board_type", "Signpost or info board"

    # Priority 5: NPC Dialogue (Message + interaction)
    if has_msg and (has_ui or "WaitButton" in cmds or "FacePlayer" in cmds):
        if has_ui:
            return "NPC", "Multi-Choice", "NPC_YesNo", "msg_slot; var_result", "NPC with Yes/No choice"
        if "JumpIf" in cmds and "CompareVarValue" in cmds:
            return "NPC", "Conditional", "NPC_Conditional", "msg_slot; flag; var", "NPC with conditional branches"
        return "NPC", "Simple Message", "NPC_Simple_Message", "msg_slot", "NPC dialogue, single message"

    # Priority 6: Movement (dominant movement)
    if has_movement and ("WaitMovement" in cmds or "Movement" in cmds):
        if has_msg:
            return "Movement", "Cutscene with Dialogue", "Movement_With_Message", "event_id; msg_slot", "Movement sequence with dialogue"
        return "Movement", "Cutscene", "Movement_Sequence", "event_id; movement_data", "NPC/event movement sequence"

    # Priority 7: Environment/Transition
    if has_fade and ("WaitFadeScreen" in cmds or "WorldMapScreen" in cmds):
        return "Environment", "Screen Effect", "Fade_Transition", "fade_type; duration", "Screen fade transition"

    # Priority 8: Level Script (used as level script, minimal)
    if is_level and is_minimal:
        return "Level", "On Load", "Level_Script", "(varies)", "Level script, runs on map load"

    # Priority 9: Multi-purpose (has multiple distinct categories)
    categories = sum([has_msg, has_item, has_trainer, has_warp, has_board, has_movement, has_fade])
    if categories >= 2:
        parts = []
        if has_msg:
            parts.append("dialogue")
        if has_trainer or has_battle:
            parts.append("battle")
        if has_item:
            parts.append("item")
        if has_warp:
            parts.append("warp")
        if has_movement:
            parts.append("movement")
        return "Multi-purpose", "Composite", "Composite", "; ".join(parts), "Combines multiple script types"

    # Priority 10: NPC (message only, no UI)
    if has_msg:
        return "NPC", "Message Only", "Message_Only", "msg_slot", "Display message, no choice"

    # Priority 11: Minimal
    if is_minimal:
        return "Minimal", "Stub", "Minimal", "", "Minimal script, placeholder or stub"

    # Priority 12: Conditional/Flow (JumpIf + CompareVarValue dominant, no message)
    jump_if = all_commands.get("JumpIf", 0)
    compare = all_commands.get("CompareVarValue", 0)
    if (jump_if + compare) >= total * 0.3 and not has_msg:
        return "Flow", "Conditional", "Conditional_Flow", "flag; var; jump_targets", "Conditional branching, flag/var checks"

    # Priority 13: Event/Cutscene (RemoveOW, SetOWPosition, PlayCry - event triggers)
    if "RemoveOW" in cmds or "SetOWPosition" in cmds:
        return "Event", "Cutscene", "Event_Trigger", "event_id; flag", "Event/cutscene trigger, OW manipulation"

    # Priority 14: Environment (SetFlag, PlayMusic, PlayFanfare - state/audio)
    if "PlayMusic" in cmds or "PlayFanfare" in cmds:
        set_flag = all_commands.get("SetFlag", 0)
        if set_flag > 0 or "PlayMusic" in cmds:
            return "Environment", "Audio/State", "Set_State", "flag; music_id", "Set game state, play music/fanfare"

    # Priority 15: CommonScript (delegates to shared logic)
    if "CommonScript" in cmds and all_commands.get("CommonScript", 0) >= 2:
        return "Flow", "Common Script", "CommonScript_Call", "script_id; args", "Calls shared common script"

    # Default: Uncategorized
    top = sorted(all_commands.items(), key=lambda x: -x[1])[:3]
    desc = "Script with " + ", ".join(c for c, _ in top) if top else "Uncategorized"
    return "Other", "Uncategorized", "Custom", "", desc


def load_items_lookup() -> dict[str, str]:
    """Return {numeric_id: name} for items. Prefer items.csv, fallback to items.inc."""
    result: dict[str, str] = {}
    if ITEMS_CSV.exists():
        with ITEMS_CSV.open(encoding="utf-8", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                num = row.get("numeric_id", "").strip()
                name = row.get("name", "").strip()
                if num and name:
                    result[num] = name
    if result:
        return result

    if ITEMS_INC.exists():
        for line in ITEMS_INC.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"\.equ\s+(ITEM_\w+)\s*,\s*(\d+)", line)
            if m:
                result[m.group(2)] = m.group(1)
    return result


def load_trainers_lookup() -> dict[int, str]:
    """Return {trainer_id: name} from trainers.s."""
    result: dict[int, str] = {}
    if not TRAINERS_S.exists():
        return result
    for line in TRAINERS_S.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"trainerdata\s+(\d+)\s*,\s*\"([^\"]*)\"", line)
        if m:
            result[int(m.group(1))] = m.group(2)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Script-Data-Main.csv from header and script data.")
    parser.add_argument("--output", "-o", type=Path, default=OUTPUT_CSV, help="Output CSV path")
    args = parser.parse_args()

    if not HEADER_CSV.exists():
        print(f"Error: Header CSV not found: {HEADER_CSV}", file=sys.stderr)
        return 1

    script_headers, level_headers, script_to_archives = load_header_script_map(HEADER_CSV)
    all_ids = collect_all_script_ids(script_headers, level_headers)
    all_ids_sorted = sorted(all_ids, key=lambda x: int(x) if x.isdigit() else 99999)

    item_by_num = load_items_lookup()
    trainer_by_id = load_trainers_lookup()

    rows: list[dict] = []

    for script_id in all_ids_sorted:
        used_as_parts: list[str] = []
        if script_id in script_headers:
            used_as_parts.append("Script File")
        if script_id in level_headers:
            used_as_parts.append("Level Script File")
        used_as = "; ".join(used_as_parts)

        headers_script = script_headers.get(script_id, [])
        headers_level = level_headers.get(script_id, [])
        all_headers = list(dict.fromkeys(headers_script + headers_level))
        headers_using = "; ".join(all_headers)

        archives = script_to_archives.get(script_id, set())
        text_archives = "; ".join(sorted(archives, key=lambda x: (x == "", int(x) if x.isdigit() else x)))

        script_path = SCRIPTS_DIR / f"{script_id}.script"
        file_exists = "Y" if script_path.exists() else "N"

        script_count = 0
        function_count = 0
        action_count = 0
        message_refs: list[int] = []
        item_refs: list[str] = []
        trainer_refs: list[str] = []
        flag_refs: list[str] = []
        all_commands: dict[str, int] = defaultdict(int)

        if script_path.exists():
            info = parse_script_file(script_path)
            script_count = info["script_count"]
            function_count = info["function_count"]
            action_count = info["action_count"]
            message_refs = sorted(set(info["message_refs"]))
            for i in info["item_refs"]:
                resolved = item_by_num.get(i, i) if re.match(r"^\d+$", str(i)) else i
                item_refs.append(resolved)
            item_refs = list(dict.fromkeys(item_refs))
            for t in info["trainer_refs"]:
                resolved = trainer_by_id.get(t, str(t))
                trainer_refs.append(resolved)
            trainer_refs = list(dict.fromkeys(trainer_refs))
            flag_refs = sorted(set(info["flag_refs"]))
            all_commands = info["all_commands"]

        top_commands = "; ".join(
            f"{cmd}({cnt})" for cmd, cnt in sorted(all_commands.items(), key=lambda x: -x[1])[:10]
        )
        total_commands = sum(all_commands.values())

        script_num = int(script_id) if script_id.isdigit() else script_id

        category, sub_category, template_type, variables, description = classify_script(
            all_commands, message_refs, item_refs, trainer_refs, used_as
        )

        rows.append({
            "Script #": script_num,
            "Script File": script_id,
            "Used As": used_as,
            "Headers Using": headers_using,
            "Text Archives": text_archives,
            "Script Count": script_count,
            "Function Count": function_count,
            "Action Count": action_count,
            "Message Refs": "; ".join(str(m) for m in message_refs),
            "Item Refs": "; ".join(item_refs),
            "Trainer Refs": "; ".join(trainer_refs),
            "Flag Refs": "; ".join(flag_refs),
            "Top Commands": top_commands,
            "Total Commands": total_commands,
            "File Exists": file_exists,
            "Category": category,
            "Sub-Category": sub_category,
            "Template Type": template_type,
            "Variables": variables,
            "Description": description,
        })

    fieldnames = [
        "Script #", "Script File", "Used As", "Headers Using", "Text Archives",
        "Script Count", "Function Count", "Action Count",
        "Message Refs", "Item Refs", "Trainer Refs", "Flag Refs",
        "Top Commands", "Total Commands", "File Exists",
        "Category", "Sub-Category", "Template Type", "Variables", "Description",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {args.output} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

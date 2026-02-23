#!/usr/bin/env python3
"""
Item Data Compiler (Repo Tool)

Compiles item property and in-game location data from multiple source files
into four categorised CSV sheets under Data/Item-Data/:

  All-Item-Data.csv    — Master listing of every item
  Medicine-Data.csv    — Items in POCKET_MEDICINE (potions, status heals, etc.)
  Berry-Data.csv       — Items in POCKET_BERRIES
  PokeBall-Data.csv    — Items in POCKET_BALLS

Data sources:
  Tools/hg-engine/include/constants/item.h
      Symbolic ITEM_NAME → numeric ID mapping.

  Tools/hg-engine/data/itemdata/itemdata.c
      Per-item C struct with price, pocket, hold-effect, heal flags, etc.

  Tools/hg-engine/src/field/mart.c
      Indexed static mart inventory arrays + badge-gated mart items.

  Data/Header-Data/Header-Data-Main.csv  +
  ROM/Pokemon-Spectral-Dream_DSPRE_contents/expanded/scripts/*.script
      Which headers sell which inventories; which scripts give items directly.

Standard-library only (no pip installs required).
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


# --------------------------------------------------------------------------------------
# Repo-relative defaults
# --------------------------------------------------------------------------------------

DEFAULT_REPO_ROOT   = Path(__file__).resolve().parents[2]
TOOL_DIR            = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR  = TOOL_DIR / "backups"
DEFAULT_REPORTS_DIR = TOOL_DIR / "reports"

DEFAULT_ITEM_H      = DEFAULT_REPO_ROOT / "Tools" / "hg-engine" / "include" / "constants" / "item.h"
DEFAULT_ITEMDATA_C  = DEFAULT_REPO_ROOT / "Tools" / "hg-engine" / "data" / "itemdata" / "itemdata.c"
DEFAULT_MART_C      = DEFAULT_REPO_ROOT / "Tools" / "hg-engine" / "src" / "field" / "mart.c"
DEFAULT_HEADER_CSV  = DEFAULT_REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"
DEFAULT_SCRIPTS_DIR = DEFAULT_REPO_ROOT / "ROM" / "Pokemon-Spectral-Dream_DSPRE_contents" / "expanded" / "scripts"
DEFAULT_OUTPUT_DIR  = DEFAULT_REPO_ROOT / "Data" / "Item-Data"


# --------------------------------------------------------------------------------------
# Pocket constants (mirrors item.h)
# --------------------------------------------------------------------------------------

POCKET_ITEMS        = 0
POCKET_MEDICINE     = 1
POCKET_BALLS        = 2
POCKET_TMHMS        = 3
POCKET_BERRIES      = 4
POCKET_MAIL         = 5
POCKET_BATTLE_ITEMS = 6
POCKET_KEY_ITEMS    = 7

POCKET_LABEL: Dict[int, str] = {
    POCKET_ITEMS:        "Items",
    POCKET_MEDICINE:     "Medicine",
    POCKET_BALLS:        "Poké Balls",
    POCKET_TMHMS:        "TMs/HMs",
    POCKET_BERRIES:      "Berries",
    POCKET_MAIL:         "Mail",
    POCKET_BATTLE_ITEMS: "Battle Items",
    POCKET_KEY_ITEMS:    "Key Items",
}

# CommonScript IDs used in PokéMart NPC scripts
COMMON_MART_REGULAR = 2048   # calls MartScreen   0x8004 in 0003.script Script 50
COMMON_MART_SPECIAL = 2052   # calls SpMartScreen 0x8004 in 0003.script Script 54
COMMON_GIVE_ITEM    = 2033   # gives item whose ID is in 0x8004 / qty in 0x8005


# --------------------------------------------------------------------------------------
# Data models
# --------------------------------------------------------------------------------------

@dataclass
class ItemProperties:
    """All fields extractable from itemdata.c for a single item."""
    item_id:            int    = 0
    item_name:          str    = ""
    pocket:             int    = POCKET_ITEMS
    price:              int    = 0
    sell_price:         int    = 0          # derived as price // 2
    hold_effect:        int    = 0
    hold_effect_param:  int    = 0
    pluck_effect:       int    = 0
    fling_effect:       int    = 0
    fling_power:        int    = 0
    natural_gift_power: int    = 0
    natural_gift_type:  int    = 0
    prevent_toss:       bool   = False
    selectable:         bool   = False
    field_use_func:     int    = 0
    battle_use_func:    int    = 0
    # partyUseParam flags
    slp_heal:           bool   = False
    psn_heal:           bool   = False
    brn_heal:           bool   = False
    frz_heal:           bool   = False
    prz_heal:           bool   = False
    cfs_heal:           bool   = False
    inf_heal:           bool   = False
    guard_spec:         bool   = False
    revive:             bool   = False
    revive_all:         bool   = False
    level_up:           bool   = False
    evolve:             bool   = False
    atk_stages:         int    = 0
    def_stages:         int    = 0
    spatk_stages:       int    = 0
    spdef_stages:       int    = 0
    speed_stages:       int    = 0
    accuracy_stages:    int    = 0
    critrate_stages:    int    = 0
    pp_up:              bool   = False
    pp_max:             bool   = False
    pp_restore:         bool   = False
    pp_restore_all:     bool   = False
    hp_restore:         bool   = False
    hp_ev_up:           bool   = False
    atk_ev_up:          bool   = False
    def_ev_up:          bool   = False
    speed_ev_up:        bool   = False
    spatk_ev_up:        bool   = False
    spdef_ev_up:        bool   = False
    friendship_mod_lo:  bool   = False
    friendship_mod_med: bool   = False
    friendship_mod_hi:  bool   = False
    hp_ev_up_param:     int    = 0
    atk_ev_up_param:    int    = 0
    def_ev_up_param:    int    = 0
    speed_ev_up_param:  int    = 0
    spatk_ev_up_param:  int    = 0
    spdef_ev_up_param:  int    = 0
    hp_restore_param:   int    = 0
    pp_restore_param:   int    = 0
    # location data (filled later)
    shop_locations:     List[str] = field(default_factory=list)
    given_at_locations: List[str] = field(default_factory=list)

    @property
    def pocket_label(self) -> str:
        return POCKET_LABEL.get(self.pocket, f"Unknown({self.pocket})")


# --------------------------------------------------------------------------------------
# Phase 1 — Parse item.h  →  {ITEM_NAME: item_id}
# --------------------------------------------------------------------------------------

_RE_ITEM_DEFINE = re.compile(r"^#define\s+(ITEM_\w+)\s+(\d+)", re.MULTILINE)


def parse_item_constants(item_h: Path) -> Dict[str, int]:
    """Return {ITEM_NAME: numeric_id} from item.h."""
    if not item_h.exists():
        print(f"  [WARN] item.h not found: {item_h}")
        return {}
    text = item_h.read_text(encoding="utf-8", errors="replace")
    result: Dict[str, int] = {}
    for m in _RE_ITEM_DEFINE.finditer(text):
        result[m.group(1)] = int(m.group(2))
    return result


# --------------------------------------------------------------------------------------
# Phase 2 — Parse itemdata.c  →  {item_id: ItemProperties}
# --------------------------------------------------------------------------------------

_RE_ITEM_BLOCK_START = re.compile(r"\[(?P<name>ITEM_\w+)\]\s*=\s*\{")
_RE_ITEM_PRICE       = re.compile(r"ITEM_PRICE\s*\(\s*(?P<val>\d+)\s*\)")
_RE_FIELD_INT        = re.compile(r"\.\s*(?P<key>\w+)\s*=\s*(?P<val>-?\d+)")
_RE_FIELD_BOOL       = re.compile(r"\.\s*(?P<key>\w+)\s*=\s*(?P<val>TRUE|FALSE)")
_RE_FIELD_SYM        = re.compile(r"\.\s*(?P<key>\w+)\s*=\s*(?P<val>[A-Z_][A-Z0-9_]*)")

# fieldPocket symbol → int
_POCKET_SYM: Dict[str, int] = {
    "POCKET_ITEMS":        POCKET_ITEMS,
    "POCKET_MEDICINE":     POCKET_MEDICINE,
    "POCKET_BALLS":        POCKET_BALLS,
    "POCKET_TMHMS":        POCKET_TMHMS,
    "POCKET_BERRIES":      POCKET_BERRIES,
    "POCKET_MAIL":         POCKET_MAIL,
    "POCKET_BATTLE_ITEMS": POCKET_BATTLE_ITEMS,
    "POCKET_KEY_ITEMS":    POCKET_KEY_ITEMS,
    # aliases seen in the codebase
    "ITEMPOCKET_HP_ITEMS":  POCKET_MEDICINE,
    "ITEMPOCKET_POKEBALL":  POCKET_BALLS,
    "ITEMPOCKET_BATTLE":    POCKET_BATTLE_ITEMS,
}

# naturalGiftType (TYPE_XXX constants) → numeric fallback mapping
_TYPE_SYM: Dict[str, int] = {
    "TYPE_NORMAL": 0, "TYPE_FIGHTING": 1, "TYPE_FLYING": 2, "TYPE_POISON": 3,
    "TYPE_GROUND": 4, "TYPE_ROCK": 5, "TYPE_BUG": 6, "TYPE_GHOST": 7,
    "TYPE_STEEL": 8, "TYPE_FIRE": 10, "TYPE_WATER": 11, "TYPE_GRASS": 12,
    "TYPE_ELECTRIC": 13, "TYPE_PSYCHIC": 14, "TYPE_ICE": 15,
    "TYPE_DRAGON": 16, "TYPE_DARK": 17, "TYPE_FAIRY": 18,
}


def _sym_to_int(sym: str, sym_map: Dict[str, int], default: int = 0) -> int:
    return sym_map.get(sym, default)


def _split_item_blocks(text: str) -> List[Tuple[str, str]]:
    """
    Returns list of (item_name, block_body) for each [ITEM_XXX] = { ... } entry.
    Handles nested braces correctly.
    """
    results: List[Tuple[str, str]] = []
    i = 0
    while i < len(text):
        m = _RE_ITEM_BLOCK_START.search(text, i)
        if not m:
            break
        name = m.group("name")
        brace_start = m.end() - 1  # points at the opening '{'
        depth = 0
        j = brace_start
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    results.append((name, text[brace_start : j + 1]))
                    i = j + 1
                    break
            j += 1
        else:
            break
    return results


def parse_itemdata_c(
    itemdata_c: Path,
    item_constants: Dict[str, int],
) -> Dict[int, ItemProperties]:
    """Parse itemdata.c and return {item_id: ItemProperties}."""
    if not itemdata_c.exists():
        print(f"  [WARN] itemdata.c not found: {itemdata_c}")
        return {}

    # Reverse map: id → name (first matching define wins)
    id_to_name: Dict[int, str] = {}
    for nm, nid in item_constants.items():
        if nid not in id_to_name:
            id_to_name[nid] = nm

    text = itemdata_c.read_text(encoding="utf-8", errors="replace")
    blocks = _split_item_blocks(text)

    result: Dict[int, ItemProperties] = {}

    for name, block in blocks:
        item_id = item_constants.get(name)
        if item_id is None:
            # Try stripping version suffixes and re-lookup
            item_id = item_constants.get(name.upper())
        if item_id is None:
            continue

        props = ItemProperties(item_id=item_id, item_name=name)

        # ITEM_PRICE macro
        m_price = _RE_ITEM_PRICE.search(block)
        if m_price:
            props.price = int(m_price.group("val"))
            props.sell_price = props.price // 2

        # Boolean fields
        for m in _RE_FIELD_BOOL.finditer(block):
            k = m.group("key")
            v = m.group("val") == "TRUE"
            _set_bool_field(props, k, v)

        # Integer fields
        for m in _RE_FIELD_INT.finditer(block):
            k = m.group("key")
            v = int(m.group("val"))
            _set_int_field(props, k, v)

        # Symbolic fields (pocket, type, etc.)
        for m in _RE_FIELD_SYM.finditer(block):
            k  = m.group("key")
            sv = m.group("val")
            if k == "fieldPocket":
                props.pocket = _sym_to_int(sv, _POCKET_SYM, POCKET_ITEMS)
            elif k == "naturalGiftType":
                props.natural_gift_type = _sym_to_int(sv, _TYPE_SYM, 0)

        result[item_id] = props

    return result


_BOOL_FIELDS = {
    "prevent_toss", "selectable",
    "slp_heal", "psn_heal", "brn_heal", "frz_heal", "prz_heal",
    "cfs_heal", "inf_heal", "guard_spec", "revive", "revive_all",
    "level_up", "evolve", "pp_up", "pp_max", "pp_restore",
    "pp_restore_all", "hp_restore", "hp_ev_up", "atk_ev_up",
    "def_ev_up", "speed_ev_up", "spatk_ev_up", "spdef_ev_up",
    "friendship_mod_lo", "friendship_mod_med", "friendship_mod_hi",
}

_INT_FIELDS = {
    "holdEffect": "hold_effect",
    "holdEffectParam": "hold_effect_param",
    "pluckEffect": "pluck_effect",
    "flingEffect": "fling_effect",
    "flingPower": "fling_power",
    "naturalGiftPower": "natural_gift_power",
    "naturalGiftType": "natural_gift_type",
    "fieldUseFunc": "field_use_func",
    "battleUseFunc": "battle_use_func",
    "atk_stages": "atk_stages",
    "def_stages": "def_stages",
    "spatk_stages": "spatk_stages",
    "spdef_stages": "spdef_stages",
    "speed_stages": "speed_stages",
    "accuracy_stages": "accuracy_stages",
    "critrate_stages": "critrate_stages",
    "hp_ev_up_param": "hp_ev_up_param",
    "atk_ev_up_param": "atk_ev_up_param",
    "def_ev_up_param": "def_ev_up_param",
    "speed_ev_up_param": "speed_ev_up_param",
    "spatk_ev_up_param": "spatk_ev_up_param",
    "spdef_ev_up_param": "spdef_ev_up_param",
    "hp_restore_param": "hp_restore_param",
    "pp_restore_param": "pp_restore_param",
}


def _set_bool_field(props: ItemProperties, key: str, val: bool) -> None:
    if key in _BOOL_FIELDS and hasattr(props, key):
        setattr(props, key, val)


def _set_int_field(props: ItemProperties, key: str, val: int) -> None:
    py_key = _INT_FIELDS.get(key)
    if py_key and hasattr(props, py_key):
        setattr(props, py_key, val)


# --------------------------------------------------------------------------------------
# Phase 3 — Parse mart.c  →  indexed list of item lists + badge mart
# --------------------------------------------------------------------------------------

_RE_U16_ARRAY  = re.compile(r"u16\s+(?P<name>s\w+)\s*\[\s*\]\s*=\s*\{(?P<body>[^}]*)\}", re.DOTALL)
_RE_BADGE_ENTRY = re.compile(r"\{\s*(?P<item>ITEM_\w+)\s*,\s*(?P<badges>\d+)\s*\}")
_RE_ITEM_SYM   = re.compile(r"ITEM_\w+")


@dataclass
class MartInventory:
    index: int
    c_name: str           # e.g. "sCherrygroveCityMart"
    label: str            # human-readable, derived from c_name
    item_names: List[str] = field(default_factory=list)


@dataclass
class BadgeMartEntry:
    item_name: str
    required_badges: int


def _c_name_to_label(c_name: str) -> str:
    """Convert sCherrygroveCityMart → Cherrygrove City Mart."""
    name = c_name.lstrip("s")
    # Insert spaces before uppercase letters (camelCase → words)
    result = re.sub(r"([A-Z])", r" \1", name).strip()
    return result


def parse_mart_c(
    mart_c: Path,
    item_constants: Dict[str, int],
) -> Tuple[List[MartInventory], List[BadgeMartEntry]]:
    """
    Returns (static_inventories, badge_mart_entries).

    static_inventories is ordered by declaration order (index == position in list).
    """
    if not mart_c.exists():
        print(f"  [WARN] mart.c not found: {mart_c}")
        return [], []

    text = mart_c.read_text(encoding="utf-8", errors="replace")

    # Badge mart — find the full block by scanning for matching braces
    badge_entries: List[BadgeMartEntry] = []
    badge_start_m = re.search(r"const struct BadgeMartItems sBadgeMart\[\]\s*=\s*\{", text)
    if badge_start_m:
        brace_start = badge_start_m.end() - 1
        depth = 0
        j = brace_start
        badge_body = ""
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    badge_body = text[brace_start + 1 : j]
                    break
            j += 1
        for m in _RE_BADGE_ENTRY.finditer(badge_body):
            badge_entries.append(BadgeMartEntry(m.group("item"), int(m.group("badges"))))

    # Static u16 arrays (in declaration order, excluding sBadgeMart and struct MartItem arrays)
    inventories: List[MartInventory] = []
    for m in _RE_U16_ARRAY.finditer(text):
        c_name = m.group("name")
        body   = m.group("body")
        items  = _RE_ITEM_SYM.findall(body)
        items  = [i for i in items if i != "0xFFFF"]
        inv = MartInventory(
            index=len(inventories),
            c_name=c_name,
            label=_c_name_to_label(c_name),
            item_names=items,
        )
        inventories.append(inv)

    return inventories, badge_entries


# --------------------------------------------------------------------------------------
# Phase 4 — Read Header-Data-Main.csv
# --------------------------------------------------------------------------------------

@dataclass
class HeaderEntry:
    header_id:    int
    internal_name: str
    script_file:  Optional[int]


def read_headers(csv_path: Path) -> List[HeaderEntry]:
    """Return all numeric-id headers from Header-Data-Main.csv."""
    if not csv_path.exists():
        print(f"  [WARN] Header CSV not found: {csv_path}")
        return []
    headers: List[HeaderEntry] = []
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_id = (row.get("HEADER #") or "").strip()
            if not raw_id.isdigit():
                continue
            raw_script = (row.get("Script File") or "").strip()
            script_file: Optional[int] = int(raw_script) if raw_script.isdigit() else None
            headers.append(HeaderEntry(
                header_id=int(raw_id),
                internal_name=(row.get("Internal Name") or "").strip(),
                script_file=script_file,
            ))
    return headers


# --------------------------------------------------------------------------------------
# Phase 5 — Parse script files for mart calls and item-give patterns
# --------------------------------------------------------------------------------------

_RE_SETVAR       = re.compile(r"SetVar\s+0x8004\s+(\d+)")
_RE_COMMON_SCRIPT = re.compile(r"CommonScript\s+(\d+)")
_RE_GIVE_ITEM_CMD = re.compile(
    r"GiveItem\s+(ITEM_\w+|\d+)\s+(\d+)",
    re.IGNORECASE,
)


@dataclass
class ScriptAnalysis:
    header:         HeaderEntry
    mart_indices:   List[Tuple[int, str]]   # [(inventory_index, "regular"|"special"), ...]
    given_item_ids: List[int]               # direct GiveItem
    give_common_ids: List[int]              # items via CommonScript 2033 pattern


def analyse_script(
    header:         HeaderEntry,
    scripts_dir:    Path,
    item_constants: Dict[str, int],
) -> Optional[ScriptAnalysis]:
    if header.script_file is None:
        return None
    script_path = scripts_dir / f"{header.script_file:04d}.script"
    if not script_path.exists():
        return None

    text = script_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    analysis = ScriptAnalysis(
        header=header,
        mart_indices=[],
        given_item_ids=[],
        give_common_ids=[],
    )

    # Walk lines sequentially to capture SetVar→CommonScript pairs
    pending_var_8004: Optional[int] = None
    pending_var_8005: Optional[int] = None

    for line in lines:
        stripped = line.strip()
        # Ignore comment lines
        if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
            continue

        # SetVar 0x8004 <value>
        m_sv = _RE_SETVAR.search(stripped)
        if m_sv:
            pending_var_8004 = int(m_sv.group(1))
            continue

        # SetVar 0x8005 <value>  (item quantity for give-item pattern)
        m_sv5 = re.search(r"SetVar\s+0x8005\s+(\d+)", stripped)
        if m_sv5:
            pending_var_8005 = int(m_sv5.group(1))
            continue

        # CommonScript <id>
        m_cs = _RE_COMMON_SCRIPT.search(stripped)
        if m_cs:
            cs_id = int(m_cs.group(1))
            if pending_var_8004 is not None:
                if cs_id == COMMON_MART_REGULAR:
                    analysis.mart_indices.append((pending_var_8004, "regular"))
                    pending_var_8004 = None
                elif cs_id == COMMON_MART_SPECIAL:
                    analysis.mart_indices.append((pending_var_8004, "special"))
                    pending_var_8004 = None
                elif cs_id == COMMON_GIVE_ITEM:
                    analysis.give_common_ids.append(pending_var_8004)
                    pending_var_8004 = None
            # Reset on any other CommonScript
            elif cs_id not in (COMMON_MART_REGULAR, COMMON_MART_SPECIAL, COMMON_GIVE_ITEM):
                pending_var_8004 = None
            continue

        # Direct GiveItem command:  GiveItem ITEM_XXX qty   or   GiveItem 123 qty
        m_gi = _RE_GIVE_ITEM_CMD.search(stripped)
        if m_gi:
            raw_item = m_gi.group(1)
            if raw_item.startswith("ITEM_"):
                iid = item_constants.get(raw_item)
                if iid is not None:
                    analysis.given_item_ids.append(iid)
            else:
                analysis.given_item_ids.append(int(raw_item))
            continue

        # GetItemQuantity ITEM_XXX ... — not a give, but mark as referenced
        m_giq = re.search(r"GetItemQuantity\s+(ITEM_\w+)", stripped)
        if m_giq:
            pass  # referenced but not given; skip

        # Any non-empty, non-control line resets pending state if nothing matched
        if stripped and not stripped.startswith(("Script ", "Function ", "Jump ", "End", "//", "/*", "*")):
            if pending_var_8004 is not None and _RE_SETVAR.search(stripped) is None:
                # Don't reset if it's another SetVar on a different var
                pass

    return analysis


def analyse_all_scripts(
    headers:     List[HeaderEntry],
    scripts_dir: Path,
    item_constants: Dict[str, int],
) -> List[ScriptAnalysis]:
    analyses: List[ScriptAnalysis] = []
    seen_scripts: Dict[int, List[ScriptAnalysis]] = {}
    for hdr in headers:
        if hdr.script_file is None:
            continue
        a = analyse_script(hdr, scripts_dir, item_constants)
        if a and (a.mart_indices or a.given_item_ids or a.give_common_ids):
            analyses.append(a)
            seen_scripts.setdefault(hdr.script_file, []).append(a)
    return analyses


# --------------------------------------------------------------------------------------
# Phase 6 — Resolve mart inventories + build location data per item
# --------------------------------------------------------------------------------------

def resolve_locations(
    analyses:     List[ScriptAnalysis],
    inventories:  List[MartInventory],
    item_constants: Dict[str, int],
    item_props:   Dict[int, ItemProperties],
) -> None:
    """
    Populate shop_locations and given_at_locations on each ItemProperties entry.
    Also creates stub entries for items found in marts but not in itemdata.c.
    """
    # Reverse constant map: id → name
    id_to_name: Dict[int, str] = {}
    for nm, nid in item_constants.items():
        if nid not in id_to_name:
            id_to_name[nid] = nm

    def _ensure_stub(item_id: int) -> ItemProperties:
        if item_id not in item_props:
            stub = ItemProperties(
                item_id=item_id,
                item_name=id_to_name.get(item_id, f"ITEM_{item_id}"),
            )
            item_props[item_id] = stub
        return item_props[item_id]

    def _name_from_const(const_name: str) -> int:
        return item_constants.get(const_name, -1)

    for analysis in analyses:
        header_label = f"{analysis.header.internal_name} (H#{analysis.header.header_id:04d})"

        # Mart screen inventories
        for inv_idx, kind in analysis.mart_indices:
            if inv_idx < len(inventories):
                inv = inventories[inv_idx]
                inv_label = f"{header_label} [{inv.label}]"
                for const_name in inv.item_names:
                    iid = _name_from_const(const_name)
                    if iid < 0:
                        continue
                    props = _ensure_stub(iid)
                    if inv_label not in props.shop_locations:
                        props.shop_locations.append(inv_label)

        # Direct item gives
        for iid in analysis.given_item_ids + analysis.give_common_ids:
            props = _ensure_stub(iid)
            if header_label not in props.given_at_locations:
                props.given_at_locations.append(header_label)


def resolve_badge_mart_locations(
    badge_entries: List[BadgeMartEntry],
    item_constants: Dict[str, int],
    item_props: Dict[int, ItemProperties],
) -> None:
    """Tag badge-gated mart items with their unlock requirement."""
    id_to_name: Dict[int, str] = {v: k for k, v in item_constants.items()}
    for entry in badge_entries:
        iid = item_constants.get(entry.item_name, -1)
        if iid < 0:
            continue
        if iid not in item_props:
            item_props[iid] = ItemProperties(
                item_id=iid,
                item_name=entry.item_name,
            )
        label = f"Badge Mart (unlocks at {entry.required_badges} badge{'s' if entry.required_badges != 1 else ''})"
        props = item_props[iid]
        if label not in props.shop_locations:
            props.shop_locations.append(label)


# --------------------------------------------------------------------------------------
# Phase 7 — CSV schemas and writers
# --------------------------------------------------------------------------------------

def _b(val: bool) -> str:
    return "TRUE" if val else "FALSE"


def _join(lst: List[str]) -> str:
    return " | ".join(lst) if lst else ""


# ---- All-Item-Data ----------------------------------------------------------------

ALL_ITEM_COLUMNS = [
    "Item_ID", "Item_Name", "Pocket", "Price", "Sell_Price",
    "Hold_Effect", "Hold_Effect_Param", "Fling_Power", "Fling_Effect",
    "Natural_Gift_Power", "Natural_Gift_Type",
    "Prevent_Toss", "Selectable",
    "Field_Use_Func", "Battle_Use_Func",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_all_item_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Pocket":              p.pocket_label,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Hold_Effect":         p.hold_effect,
        "Hold_Effect_Param":   p.hold_effect_param,
        "Fling_Power":         p.fling_power,
        "Fling_Effect":        p.fling_effect,
        "Natural_Gift_Power":  p.natural_gift_power,
        "Natural_Gift_Type":   p.natural_gift_type,
        "Prevent_Toss":        _b(p.prevent_toss),
        "Selectable":          _b(p.selectable),
        "Field_Use_Func":      p.field_use_func,
        "Battle_Use_Func":     p.battle_use_func,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- Medicine-Data ----------------------------------------------------------------

MEDICINE_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "HP_Restore", "HP_Restore_Param",
    "SLP_Heal", "PSN_Heal", "BRN_Heal", "FRZ_Heal", "PRZ_Heal",
    "CFS_Heal", "INF_Heal", "Guard_Spec",
    "Revive", "Revive_All", "Level_Up", "Evolve",
    "PP_Restore", "PP_Restore_Param", "PP_Restore_All", "PP_Up", "PP_Max",
    "ATK_Stages", "DEF_Stages", "SpATK_Stages", "SpDEF_Stages",
    "Speed_Stages", "Accuracy_Stages", "CritRate_Stages",
    "HP_EV_Up", "HP_EV_Param",
    "ATK_EV_Up", "ATK_EV_Param",
    "DEF_EV_Up", "DEF_EV_Param",
    "Speed_EV_Up", "Speed_EV_Param",
    "SpATK_EV_Up", "SpATK_EV_Param",
    "SpDEF_EV_Up", "SpDEF_EV_Param",
    "Friendship_Lo", "Friendship_Med", "Friendship_Hi",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_medicine_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":         p.item_id,
        "Item_Name":       p.item_name,
        "Price":           p.price,
        "Sell_Price":      p.sell_price,
        "HP_Restore":      _b(p.hp_restore),
        "HP_Restore_Param": p.hp_restore_param,
        "SLP_Heal":        _b(p.slp_heal),
        "PSN_Heal":        _b(p.psn_heal),
        "BRN_Heal":        _b(p.brn_heal),
        "FRZ_Heal":        _b(p.frz_heal),
        "PRZ_Heal":        _b(p.prz_heal),
        "CFS_Heal":        _b(p.cfs_heal),
        "INF_Heal":        _b(p.inf_heal),
        "Guard_Spec":      _b(p.guard_spec),
        "Revive":          _b(p.revive),
        "Revive_All":      _b(p.revive_all),
        "Level_Up":        _b(p.level_up),
        "Evolve":          _b(p.evolve),
        "PP_Restore":      _b(p.pp_restore),
        "PP_Restore_Param": p.pp_restore_param,
        "PP_Restore_All":  _b(p.pp_restore_all),
        "PP_Up":           _b(p.pp_up),
        "PP_Max":          _b(p.pp_max),
        "ATK_Stages":      p.atk_stages,
        "DEF_Stages":      p.def_stages,
        "SpATK_Stages":    p.spatk_stages,
        "SpDEF_Stages":    p.spdef_stages,
        "Speed_Stages":    p.speed_stages,
        "Accuracy_Stages": p.accuracy_stages,
        "CritRate_Stages": p.critrate_stages,
        "HP_EV_Up":        _b(p.hp_ev_up),
        "HP_EV_Param":     p.hp_ev_up_param,
        "ATK_EV_Up":       _b(p.atk_ev_up),
        "ATK_EV_Param":    p.atk_ev_up_param,
        "DEF_EV_Up":       _b(p.def_ev_up),
        "DEF_EV_Param":    p.def_ev_up_param,
        "Speed_EV_Up":     _b(p.speed_ev_up),
        "Speed_EV_Param":  p.speed_ev_up_param,
        "SpATK_EV_Up":     _b(p.spatk_ev_up),
        "SpATK_EV_Param":  p.spatk_ev_up_param,
        "SpDEF_EV_Up":     _b(p.spdef_ev_up),
        "SpDEF_EV_Param":  p.spdef_ev_up_param,
        "Friendship_Lo":   _b(p.friendship_mod_lo),
        "Friendship_Med":  _b(p.friendship_mod_med),
        "Friendship_Hi":   _b(p.friendship_mod_hi),
        "Shop_Locations":  _join(p.shop_locations),
        "Given_At_Locations": _join(p.given_at_locations),
    }


# ---- Berry-Data -------------------------------------------------------------------

BERRY_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Hold_Effect", "Hold_Effect_Param",
    "Natural_Gift_Power", "Natural_Gift_Type",
    "Pluck_Effect",
    "SLP_Heal", "PSN_Heal", "BRN_Heal", "FRZ_Heal", "PRZ_Heal",
    "HP_Restore", "HP_Restore_Param",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_berry_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Hold_Effect":         p.hold_effect,
        "Hold_Effect_Param":   p.hold_effect_param,
        "Natural_Gift_Power":  p.natural_gift_power,
        "Natural_Gift_Type":   p.natural_gift_type,
        "Pluck_Effect":        p.pluck_effect,
        "SLP_Heal":            _b(p.slp_heal),
        "PSN_Heal":            _b(p.psn_heal),
        "BRN_Heal":            _b(p.brn_heal),
        "FRZ_Heal":            _b(p.frz_heal),
        "PRZ_Heal":            _b(p.prz_heal),
        "HP_Restore":          _b(p.hp_restore),
        "HP_Restore_Param":    p.hp_restore_param,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- PokeBall-Data ----------------------------------------------------------------

POKEBALL_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Hold_Effect", "Hold_Effect_Param",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_pokeball_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Hold_Effect":         p.hold_effect,
        "Hold_Effect_Param":   p.hold_effect_param,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- TM-Data / HM-Data ------------------------------------------------------------

TM_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Field_Use_Func", "Battle_Use_Func",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_tm_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Field_Use_Func":      p.field_use_func,
        "Battle_Use_Func":     p.battle_use_func,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- Key-Item-Data ----------------------------------------------------------------

KEY_ITEM_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Field_Use_Func", "Prevent_Toss",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_key_item_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Field_Use_Func":      p.field_use_func,
        "Prevent_Toss":        _b(p.prevent_toss),
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- Mail-Data --------------------------------------------------------------------

MAIL_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Hold_Effect", "Hold_Effect_Param",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_mail_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Hold_Effect":         p.hold_effect,
        "Hold_Effect_Param":   p.hold_effect_param,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- Battle-Item-Data -------------------------------------------------------------

BATTLE_ITEM_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Hold_Effect", "Hold_Effect_Param",
    "ATK_Stages", "DEF_Stages", "SpATK_Stages", "SpDEF_Stages",
    "Speed_Stages", "Accuracy_Stages", "CritRate_Stages",
    "Guard_Spec",
    "Field_Use_Func", "Battle_Use_Func",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_battle_item_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Hold_Effect":         p.hold_effect,
        "Hold_Effect_Param":   p.hold_effect_param,
        "ATK_Stages":          p.atk_stages,
        "DEF_Stages":          p.def_stages,
        "SpATK_Stages":        p.spatk_stages,
        "SpDEF_Stages":        p.spdef_stages,
        "Speed_Stages":        p.speed_stages,
        "Accuracy_Stages":     p.accuracy_stages,
        "CritRate_Stages":     p.critrate_stages,
        "Guard_Spec":          _b(p.guard_spec),
        "Field_Use_Func":      p.field_use_func,
        "Battle_Use_Func":     p.battle_use_func,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


# ---- General-Item-Data ------------------------------------------------------------

GENERAL_ITEM_COLUMNS = [
    "Item_ID", "Item_Name", "Price", "Sell_Price",
    "Hold_Effect", "Hold_Effect_Param",
    "Fling_Power", "Fling_Effect",
    "Prevent_Toss", "Selectable",
    "Field_Use_Func", "Battle_Use_Func",
    "Shop_Locations", "Given_At_Locations",
]

def _props_to_general_item_row(p: ItemProperties) -> dict:
    return {
        "Item_ID":             p.item_id,
        "Item_Name":           p.item_name,
        "Price":               p.price,
        "Sell_Price":          p.sell_price,
        "Hold_Effect":         p.hold_effect,
        "Hold_Effect_Param":   p.hold_effect_param,
        "Fling_Power":         p.fling_power,
        "Fling_Effect":        p.fling_effect,
        "Prevent_Toss":        _b(p.prevent_toss),
        "Selectable":          _b(p.selectable),
        "Field_Use_Func":      p.field_use_func,
        "Battle_Use_Func":     p.battle_use_func,
        "Shop_Locations":      _join(p.shop_locations),
        "Given_At_Locations":  _join(p.given_at_locations),
    }


def write_csv(path: Path, fieldnames: List[str], rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


@dataclass
class CsvCounts:
    all_items:    int = 0
    medicine:     int = 0
    berries:      int = 0
    balls:        int = 0
    tms:          int = 0
    hms:          int = 0
    key_items:    int = 0
    mail:         int = 0
    battle_items: int = 0
    general:      int = 0


def write_all_csvs(
    item_props:  Dict[int, ItemProperties],
    output_dir:  Path,
) -> CsvCounts:
    """Write all CSV files. Returns a CsvCounts dataclass."""

    sorted_props = sorted(item_props.values(), key=lambda p: p.item_id)
    counts = CsvCounts()

    # All items (master)
    all_rows = [_props_to_all_item_row(p) for p in sorted_props if p.item_id > 0]
    write_csv(output_dir / "All-Item-Data.csv", ALL_ITEM_COLUMNS, all_rows)
    counts.all_items = len(all_rows)

    # Medicine (POCKET_MEDICINE)
    med_rows = [
        _props_to_medicine_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_MEDICINE
    ]
    write_csv(output_dir / "Medicine-Data.csv", MEDICINE_COLUMNS, med_rows)
    counts.medicine = len(med_rows)

    # Berries (POCKET_BERRIES)
    berry_rows = [
        _props_to_berry_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_BERRIES
    ]
    write_csv(output_dir / "Berry-Data.csv", BERRY_COLUMNS, berry_rows)
    counts.berries = len(berry_rows)

    # Poké Balls (POCKET_BALLS)
    ball_rows = [
        _props_to_pokeball_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_BALLS
    ]
    write_csv(output_dir / "PokeBall-Data.csv", POKEBALL_COLUMNS, ball_rows)
    counts.balls = len(ball_rows)

    # TMs — POCKET_TMHMS, item name starts with ITEM_TM
    tm_rows = [
        _props_to_tm_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_TMHMS and p.item_name.startswith("ITEM_TM")
    ]
    write_csv(output_dir / "TM-Data.csv", TM_COLUMNS, tm_rows)
    counts.tms = len(tm_rows)

    # HMs — POCKET_TMHMS, item name starts with ITEM_HM
    hm_rows = [
        _props_to_tm_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_TMHMS and p.item_name.startswith("ITEM_HM")
    ]
    write_csv(output_dir / "HM-Data.csv", TM_COLUMNS, hm_rows)
    counts.hms = len(hm_rows)

    # Key Items (POCKET_KEY_ITEMS)
    key_rows = [
        _props_to_key_item_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_KEY_ITEMS
    ]
    write_csv(output_dir / "Key-Item-Data.csv", KEY_ITEM_COLUMNS, key_rows)
    counts.key_items = len(key_rows)

    # Mail (POCKET_MAIL)
    mail_rows = [
        _props_to_mail_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_MAIL
    ]
    write_csv(output_dir / "Mail-Data.csv", MAIL_COLUMNS, mail_rows)
    counts.mail = len(mail_rows)

    # Battle Items (POCKET_BATTLE_ITEMS)
    battle_rows = [
        _props_to_battle_item_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_BATTLE_ITEMS
    ]
    write_csv(output_dir / "Battle-Item-Data.csv", BATTLE_ITEM_COLUMNS, battle_rows)
    counts.battle_items = len(battle_rows)

    # General Items (POCKET_ITEMS — misc items not fitting other categories)
    general_rows = [
        _props_to_general_item_row(p)
        for p in sorted_props
        if p.item_id > 0 and p.pocket == POCKET_ITEMS
    ]
    write_csv(output_dir / "General-Item-Data.csv", GENERAL_ITEM_COLUMNS, general_rows)
    counts.general = len(general_rows)

    return counts


# --------------------------------------------------------------------------------------
# Phase 8 — Backup + reports
# --------------------------------------------------------------------------------------

_ALL_CSV_NAMES = (
    "All-Item-Data.csv",
    "Medicine-Data.csv",
    "Berry-Data.csv",
    "PokeBall-Data.csv",
    "TM-Data.csv",
    "HM-Data.csv",
    "Key-Item-Data.csv",
    "Mail-Data.csv",
    "Battle-Item-Data.csv",
    "General-Item-Data.csv",
)


def backup_existing_csvs(output_dir: Path, backup_dir: Path, timestamp: str) -> List[str]:
    backed_up: List[str] = []
    for csv_name in _ALL_CSV_NAMES:
        src = output_dir / csv_name
        if src.exists() and src.stat().st_size > 0:
            backup_dir.mkdir(parents=True, exist_ok=True)
            dst = backup_dir / f"{src.stem}_{timestamp}.csv"
            shutil.copy2(src, dst)
            backed_up.append(str(dst))
    return backed_up


def write_reports(
    reports_dir:     Path,
    timestamp:       str,
    item_props:      Dict[int, ItemProperties],
    inventories:     List[MartInventory],
    badge_entries:   List[BadgeMartEntry],
    analyses:        List[ScriptAnalysis],
    counts:          CsvCounts,
    backed_up:       List[str],
    item_constants:  Dict[str, int],
    dry_run:         bool,
) -> List[str]:
    """Write report files and return summary lines for stdout."""

    # Pocket breakdown
    by_pocket: Dict[str, int] = {}
    for p in item_props.values():
        label = p.pocket_label
        by_pocket[label] = by_pocket.get(label, 0) + 1

    # Items with shop locations
    items_with_shops  = sum(1 for p in item_props.values() if p.shop_locations)
    items_with_gifts  = sum(1 for p in item_props.values() if p.given_at_locations)
    items_no_location = sum(
        1 for p in item_props.values()
        if not p.shop_locations and not p.given_at_locations
    )

    summary_lines = [
        "=" * 60,
        "Item Data Compiler — Run Summary",
        "=" * 60,
        f"  Items parsed from itemdata.c : {len(item_props)}",
        f"  Static mart inventories      : {len(inventories)}",
        f"  Badge-mart entries           : {len(badge_entries)}",
        f"  Script files analysed        : {len(analyses)}",
        "",
        "  CSV output:",
        f"    All-Item-Data.csv          : {counts.all_items} rows",
        f"    Medicine-Data.csv          : {counts.medicine} rows",
        f"    Berry-Data.csv             : {counts.berries} rows",
        f"    PokeBall-Data.csv          : {counts.balls} rows",
        f"    TM-Data.csv                : {counts.tms} rows",
        f"    HM-Data.csv                : {counts.hms} rows",
        f"    Key-Item-Data.csv          : {counts.key_items} rows",
        f"    Mail-Data.csv              : {counts.mail} rows",
        f"    Battle-Item-Data.csv       : {counts.battle_items} rows",
        f"    General-Item-Data.csv      : {counts.general} rows",
        "",
        "  Pocket breakdown:",
    ]
    for lbl, cnt in sorted(by_pocket.items(), key=lambda x: x[1], reverse=True):
        summary_lines.append(f"    {lbl:<24}: {cnt}")
    summary_lines += [
        "",
        f"  Items with shop locations    : {items_with_shops}",
        f"  Items received as gifts      : {items_with_gifts}",
        f"  Items with no location data  : {items_no_location}",
        "",
    ]
    if backed_up:
        summary_lines.append("  Backups created:")
        for b in backed_up:
            summary_lines.append(f"    {b}")
    else:
        summary_lines.append("  No backups needed (no pre-existing data).")
    if dry_run:
        summary_lines.append("\n  [DRY-RUN] No files written.")

    if not dry_run:
        reports_dir.mkdir(parents=True, exist_ok=True)
        summary_path = reports_dir / f"item_summary_{timestamp}.txt"
        summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

        # mart_index_map.csv — inventory index → label → items
        mart_map_path = reports_dir / f"mart_index_map_{timestamp}.csv"
        with mart_map_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Index", "C_Name", "Label", "Items"])
            for inv in inventories:
                w.writerow([inv.index, inv.c_name, inv.label, " | ".join(inv.item_names)])

        # badge_mart.csv
        badge_path = reports_dir / f"badge_mart_{timestamp}.csv"
        with badge_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Item_Name", "Required_Badges"])
            for entry in badge_entries:
                w.writerow([entry.item_name, entry.required_badges])

        # script_analysis.csv
        analysis_path = reports_dir / f"script_analysis_{timestamp}.csv"
        with analysis_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Header_ID", "Internal_Name", "Script_File",
                         "Mart_Indices", "Given_Item_IDs", "CommonScript_Give_IDs"])
            for a in analyses:
                w.writerow([
                    a.header.header_id,
                    a.header.internal_name,
                    a.header.script_file,
                    " | ".join(f"{idx}({kind})" for idx, kind in a.mart_indices),
                    " | ".join(str(i) for i in a.given_item_ids),
                    " | ".join(str(i) for i in a.give_common_ids),
                ])

        # items_no_location.csv
        no_loc_path = reports_dir / f"items_no_location_{timestamp}.csv"
        with no_loc_path.open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["Item_ID", "Item_Name", "Pocket"])
            for p in sorted(item_props.values(), key=lambda x: x.item_id):
                if not p.shop_locations and not p.given_at_locations and p.item_id > 0:
                    w.writerow([p.item_id, p.item_name, p.pocket_label])

    return summary_lines


# --------------------------------------------------------------------------------------
# Main orchestration
# --------------------------------------------------------------------------------------

def run_update(
    item_h:      Path,
    itemdata_c:  Path,
    mart_c:      Path,
    header_csv:  Path,
    scripts_dir: Path,
    output_dir:  Path,
    backup_dir:  Path,
    reports_dir: Path,
    dry_run:     bool,
    verbose:     bool,
) -> int:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    print("Phase 1 — Parsing item.h …")
    item_constants = parse_item_constants(item_h)
    print(f"          {len(item_constants)} item constants loaded.")

    print("Phase 2 — Parsing itemdata.c …")
    item_props = parse_itemdata_c(itemdata_c, item_constants)
    print(f"          {len(item_props)} item entries parsed.")

    print("Phase 3 — Parsing mart.c …")
    inventories, badge_entries = parse_mart_c(mart_c, item_constants)
    print(f"          {len(inventories)} static mart inventories, {len(badge_entries)} badge-mart entries.")

    print("Phase 4 — Reading Header-Data-Main.csv …")
    headers = read_headers(header_csv)
    print(f"          {len(headers)} headers loaded.")

    print("Phase 5 — Analysing script files …")
    analyses = analyse_all_scripts(headers, scripts_dir, item_constants)
    print(f"          {len(analyses)} scripts with mart/give events found.")

    print("Phase 6 — Resolving location data …")
    resolve_locations(analyses, inventories, item_constants, item_props)
    resolve_badge_mart_locations(badge_entries, item_constants, item_props)
    tagged = sum(1 for p in item_props.values() if p.shop_locations or p.given_at_locations)
    print(f"          {tagged} items tagged with location data.")

    if dry_run:
        print("\n[DRY-RUN] Skipping CSV writes and backups.")
        counts = CsvCounts(
            all_items=len([p for p in item_props.values() if p.item_id > 0]),
            medicine=sum(1 for p in item_props.values() if p.pocket == POCKET_MEDICINE),
            berries=sum(1 for p in item_props.values() if p.pocket == POCKET_BERRIES),
            balls=sum(1 for p in item_props.values() if p.pocket == POCKET_BALLS),
            tms=sum(1 for p in item_props.values() if p.pocket == POCKET_TMHMS and p.item_name.startswith("ITEM_TM")),
            hms=sum(1 for p in item_props.values() if p.pocket == POCKET_TMHMS and p.item_name.startswith("ITEM_HM")),
            key_items=sum(1 for p in item_props.values() if p.pocket == POCKET_KEY_ITEMS),
            mail=sum(1 for p in item_props.values() if p.pocket == POCKET_MAIL),
            battle_items=sum(1 for p in item_props.values() if p.pocket == POCKET_BATTLE_ITEMS),
            general=sum(1 for p in item_props.values() if p.pocket == POCKET_ITEMS),
        )
        backed_up: List[str] = []
    else:
        print("Phase 7 — Backing up existing CSVs …")
        backed_up = backup_existing_csvs(output_dir, backup_dir, timestamp)
        print(f"          {len(backed_up)} file(s) backed up.")

        print("Phase 8 — Writing CSVs …")
        counts = write_all_csvs(item_props, output_dir)
        print(f"          Done — All:{counts.all_items}, Medicine:{counts.medicine}, "
              f"Berries:{counts.berries}, Balls:{counts.balls}, "
              f"TMs:{counts.tms}, HMs:{counts.hms}, Keys:{counts.key_items}, "
              f"Mail:{counts.mail}, Battle:{counts.battle_items}, General:{counts.general}")

    print("\nPhase 9 — Writing reports …")
    summary_lines = write_reports(
        reports_dir, timestamp, item_props, inventories, badge_entries,
        analyses, counts, backed_up, item_constants, dry_run,
    )

    print()
    print("\n".join(summary_lines))

    return 0


def run_validate(
    item_h:      Path,
    itemdata_c:  Path,
    mart_c:      Path,
    header_csv:  Path,
    scripts_dir: Path,
) -> int:
    """Validate source files exist and are parseable; print findings."""
    errors = 0

    def _check(path: Path, label: str) -> bool:
        nonlocal errors
        if not path.exists():
            print(f"  [MISSING] {label}: {path}")
            errors += 1
            return False
        print(f"  [OK]      {label}: {path}")
        return True

    print("Validating source files:")
    _check(item_h,      "item.h")
    _check(itemdata_c,  "itemdata.c")
    _check(mart_c,      "mart.c")
    _check(header_csv,  "Header-Data-Main.csv")

    if scripts_dir.exists():
        script_count = len(list(scripts_dir.glob("*.script")))
        print(f"  [OK]      scripts dir: {scripts_dir}  ({script_count} .script files)")
    else:
        print(f"  [MISSING] scripts dir: {scripts_dir}")
        errors += 1

    if errors == 0:
        print("\nAll source files present. Run 'update' to generate CSVs.")
        return 0
    else:
        print(f"\n{errors} source file(s) missing. Check paths above.")
        return 1


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Item data compiler for Pokémon Spectral Dream (stdlib-only).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root",   type=Path, default=DEFAULT_REPO_ROOT,
                        help="Path to the repository root.")
    common.add_argument("--item-h",      type=Path, default=None,
                        help="Path to item.h (overrides --repo-root default).")
    common.add_argument("--itemdata-c",  type=Path, default=None,
                        help="Path to itemdata.c (overrides --repo-root default).")
    common.add_argument("--mart-c",      type=Path, default=None,
                        help="Path to mart.c (overrides --repo-root default).")
    common.add_argument("--header-csv",  type=Path, default=None,
                        help="Path to Header-Data-Main.csv.")
    common.add_argument("--scripts-dir", type=Path, default=None,
                        help="Path to expanded/scripts/ directory.")
    common.add_argument("--output-dir",  type=Path, default=None,
                        help="Where to write the four item CSV files.")
    common.add_argument("--backup-dir",  type=Path, default=DEFAULT_BACKUP_DIR)
    common.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    common.add_argument("--dry-run",     action="store_true",
                        help="Parse all sources but do not write any files.")
    common.add_argument("--verbose",     action="store_true")

    upd = sub.add_parser("update", parents=[common],
                          help="Parse sources and write/update the four CSV files.")
    upd.set_defaults(_cmd="update")

    val = sub.add_parser("validate", parents=[common],
                          help="Check that all source files are present and readable.")
    val.set_defaults(_cmd="validate")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv_list = list(argv) if argv is not None else None
    if argv_list is not None and argv_list and argv_list[0] not in {"update", "validate", "-h", "--help"}:
        argv_list = ["update"] + argv_list

    args = build_parser().parse_args(argv_list)
    cmd  = getattr(args, "_cmd", None) or "update"

    repo_root: Path = args.repo_root

    item_h      = args.item_h      or (repo_root / "Tools" / "hg-engine" / "include" / "constants" / "item.h")
    itemdata_c  = args.itemdata_c  or (repo_root / "Tools" / "hg-engine" / "data" / "itemdata" / "itemdata.c")
    mart_c      = args.mart_c      or (repo_root / "Tools" / "hg-engine" / "src" / "field" / "mart.c")
    header_csv  = args.header_csv  or (repo_root / "Data" / "Header-Data" / "Header-Data-Main.csv")
    scripts_dir = args.scripts_dir or (repo_root / "ROM" / "Pokemon-Spectral-Dream_DSPRE_contents" / "expanded" / "scripts")
    output_dir  = args.output_dir  or (repo_root / "Data" / "Item-Data")

    if cmd == "validate":
        return run_validate(item_h, itemdata_c, mart_c, header_csv, scripts_dir)

    return run_update(
        item_h=item_h,
        itemdata_c=itemdata_c,
        mart_c=mart_c,
        header_csv=header_csv,
        scripts_dir=scripts_dir,
        output_dir=output_dir,
        backup_dir=Path(args.backup_dir),
        reports_dir=Path(args.reports_dir),
        dry_run=args.dry_run,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())

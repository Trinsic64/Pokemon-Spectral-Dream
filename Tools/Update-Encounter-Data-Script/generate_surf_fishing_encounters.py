#!/usr/bin/env python3
"""
Generate Surf + Fishing encounter CSVs for all banks (0–255).

This writes per-bank files:
  Data/Encounter-Data/Encounters/E####_<Area>/Surf.csv
  Data/Encounter-Data/Encounters/E####_<Area>/Fishing.csv

It is intentionally conservative:
- No regional forms (no @ form markers)
- Avoid starters and pseudo-legendary lines by not including them in pools
- Levels are derived from each bank's grass baseline where available, else a bank_id-based fallback.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "Data" / "Encounter-Data"
BANKS_DIR = DATA_ROOT / "Encounters"
LEGACY_MAIN = DATA_ROOT / "Encounter-Data-Main.csv"  # legacy (read-only)
DEFAULT_EVODATA = REPO_ROOT / "Tools" / "hg-engine-OUTDATED" / "armips" / "data" / "evodata.s"
WATER_BIOME_CSV = DATA_ROOT / "Water-Biome-Pokemon.csv"


@dataclass(frozen=True)
class LegacyBankHint:
    water: str = ""
    typing: str = ""


@dataclass(frozen=True)
class EvoEdge:
    method: str  # EVO_*
    param: int
    target: str  # SPECIES_* token


_RE_EVODATA_MON = re.compile(r"^evodata\s+(SPECIES_[A-Z0-9_]+)\s*$")
_RE_EVODATA_EDGE = re.compile(r"^\s*evolution\s+(EVO_[A-Z0-9_]+)\s*,\s*([^,]+)\s*,\s*(SPECIES_[A-Z0-9_]+)\s*$")


def _strip_species_token(token: str) -> str:
    t = (token or "").strip().upper()
    return t[len("SPECIES_") :] if t.startswith("SPECIES_") else t


def _parse_int_param(raw: str) -> int:
    """
    evodata.s parameters are sometimes numbers (levels) and sometimes constants like ITEM_WATER_STONE.
    We only need numeric params for level evolutions; everything else can be treated as 0.
    """
    v = (raw or "").strip()
    return int(v) if v.isdigit() else 0


def _load_evo_map(path: Path) -> Dict[str, List[EvoEdge]]:
    """
    Parse hg-engine evodata.s and return base-species-name -> list of evolution edges.
    Keys/targets are stored as *base names* (e.g. POLIWAG), not SPECIES_* tokens.
    """
    if not path.exists():
        return {}

    evo_map: Dict[str, List[EvoEdge]] = {}
    current: Optional[str] = None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        raw = line.strip()
        if not raw:
            continue
        m = _RE_EVODATA_MON.match(raw)
        if m:
            current = _strip_species_token(m.group(1))
            evo_map.setdefault(current, [])
            continue
        if raw.startswith("terminateevodata"):
            current = None
            continue
        if current is None:
            continue
        e = _RE_EVODATA_EDGE.match(raw)
        if not e:
            continue
        method = e.group(1).strip().upper()
        param = _parse_int_param(e.group(2))
        target = _strip_species_token(e.group(3))
        if target == "NONE":
            continue
        evo_map[current].append(EvoEdge(method=method, param=param, target=target))
    return evo_map


def _evolve_via_level(
    species: str,
    level_for_evo: int,
    evo_map: Dict[str, List[EvoEdge]],
    allowed: Optional[set[str]] = None,
    ev_level_map: Optional[Dict[str, int]] = None,
) -> str:
    """
    Promote by level-based evolutions only. We use `level_for_evo` (usually encounter max level)
    so that if the generated range reaches an evolution level, we represent the evolved stage.
    Uses EvLevel from Water-Biome-Pokemon.csv when available; otherwise falls back to evodata.s.
    """
    s = (species or "").strip().upper()
    lvl = int(level_for_evo or 0)
    ev_levels = ev_level_map or {}
    guard = 0
    while guard < 8:
        guard += 1
        edges = evo_map.get(s, [])
        # Consider any EVO_LEVEL* as level-gated; use EvLevel from CSV when available.
        level_edges = [ed for ed in edges if ed.method.startswith("EVO_LEVEL")]
        candidates = []
        for ed in level_edges:
            required = ev_levels.get(s) if s in ev_levels else ed.param
            if required and lvl >= required:
                candidates.append((ed, required))
        candidates = [ed for ed, _ in candidates]
        if allowed is not None:
            candidates = [ed for ed in candidates if ed.target in allowed]
        if not candidates:
            return s
        chosen = sorted(candidates, key=lambda ed: (ev_levels.get(s, ed.param) or ed.param, ed.target))[-1]
        if chosen.target == s:
            return s
        s = chosen.target
    return s


@dataclass(frozen=True)
class WaterMon:
    species: str  # base name, e.g. POLIWAG
    type1: str
    type2: str
    bst: int
    wild_min: int  # generally encountered min level (user-curated)
    wild_max: int  # generally encountered max level (user-curated)


def _read_water_biome_csv(path: Path) -> List[WaterMon]:
    """
    Reads Data/Encounter-Data/Water-Biome-Pokemon.csv (user-curated).
    Note: this file is tab-separated.

    We intentionally ignore obvious alternate forms (no forms), per your guidance.
    """
    if not path.exists():
        return []

    mons: List[WaterMon] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            tok = (row.get("SpeciesId") or "").strip().upper()
            if not tok.startswith("SPECIES_"):
                continue
            base = _strip_species_token(tok)
            if not base or base == "NONE":
                continue

            # Ignore explicit form/gender variants
            if base.endswith(("_FEMALE", "_MALE", "_DROOPY", "_STRETCHY")):
                continue
            if base.startswith("TATSUGIRI_") or base.startswith("BASCULEGION_"):
                continue

            t1 = (row.get("Type1") or "").strip().upper()
            t2 = (row.get("Type2") or "").strip().upper()
            bst_raw = (row.get("BST") or "").strip()
            bst = int(bst_raw) if bst_raw.isdigit() else 0
            mi_raw = (row.get("EvMin") or row.get("WildMin") or "").strip()
            ma_raw = (row.get("EvMax") or row.get("WildMax") or "").strip()
            wild_min = int(mi_raw) if mi_raw.isdigit() else 0
            wild_max = int(ma_raw) if ma_raw.isdigit() else 0
            mons.append(WaterMon(species=base, type1=t1, type2=t2, bst=bst, wild_min=wild_min, wild_max=wild_max))

    # De-dupe by species (keep highest BST)
    by: Dict[str, WaterMon] = {}
    for m in mons:
        prev = by.get(m.species)
        if prev is None or m.bst > prev.bst:
            by[m.species] = m
    return list(by.values())


def _sync_water_biome_ranges_inplace(water_biome_path: Path, evodata_path: Path) -> None:
    """
    Ensure Water-Biome-Pokemon.csv contains EvMin/EvMax columns and populate missing values
    using a conservative heuristic derived from hg-engine's evodata.s and BST.
    """
    if not water_biome_path.exists():
        raise FileNotFoundError(str(water_biome_path))

    evo_map = _load_evo_map(evodata_path)
    # reverse level requirements: target -> minimum EVO_LEVEL param among sources
    rev_level_req: Dict[str, int] = {}
    for src, edges in evo_map.items():
        for ed in edges:
            if not ed.method.startswith("EVO_LEVEL") or ed.param <= 0:
                continue
            rev_level_req[ed.target] = min(rev_level_req.get(ed.target, 999), ed.param)

    def forward_level(sp: str) -> int:
        edges = evo_map.get(sp, [])
        lvls = [ed.param for ed in edges if ed.method.startswith("EVO_LEVEL") and ed.param > 0]
        return min(lvls) if lvls else 0

    # Read raw rows (tab-separated) and rewrite with EvMin/EvMax.
    raw_rows: List[Dict[str, str]] = []
    with water_biome_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        fieldnames_in = list(reader.fieldnames or [])
        for row in reader:
            raw_rows.append({k: (row.get(k) or "") for k in fieldnames_in})

    # Build output fieldnames: keep original stats columns; drop old EvLevel/EvMethod and legacy range cols if present.
    drop = {"EvLevel", "EvMethod", "WildMin", "WildMax", "EvMin", "EvMax"}
    base_fields = [fn for fn in fieldnames_in if fn and fn not in drop]
    fieldnames_out = base_fields + ["EvMin", "EvMax"]

    for row in raw_rows:
        tok = (row.get("SpeciesId") or "").strip().upper()
        if not tok.startswith("SPECIES_"):
            continue
        sp = _strip_species_token(tok)
        bst_raw = (row.get("BST") or "").strip()
        bst = int(bst_raw) if bst_raw.isdigit() else 0

        mi_raw = (row.get("EvMin") or row.get("WildMin") or "").strip()
        ma_raw = (row.get("EvMax") or row.get("WildMax") or "").strip()
        wild_min = int(mi_raw) if mi_raw.isdigit() else 0
        wild_max = int(ma_raw) if ma_raw.isdigit() else 0

        nxt = forward_level(sp)
        pre = rev_level_req.get(sp, 0)

        if wild_min <= 0 or wild_max <= 0:
            # Defaults
            if sp in ("POLIWRATH", "POLITOED"):
                wild_min, wild_max = 50, 70
            elif sp == "MAGIKARP":
                wild_min, wild_max = 2, 20
            elif nxt > 0:
                wild_min = max(2, nxt - 27)
                wild_max = min(70, nxt + 3)
            elif pre > 0:
                wild_min = pre
                wild_max = 70 if bst >= 450 else min(70, wild_min + 25)
            else:
                if bst >= 500:
                    wild_min, wild_max = 42, 60
                elif bst >= 470:
                    wild_min, wild_max = 35, 60
                elif bst >= 440:
                    wild_min, wild_max = 30, 55
                else:
                    wild_min, wild_max = 2, 35

        # Enforce legality: evolved forms by level can't appear below their evolution level.
        if pre > 0 and wild_min < pre:
            wild_min = pre
        if wild_min < 2:
            wild_min = 2
        if wild_max < wild_min:
            wild_max = wild_min
        if wild_max > 70:
            wild_max = 70

        row["EvMin"] = str(int(wild_min))
        row["EvMax"] = str(int(wild_max))

    with water_biome_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames_out, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for row in raw_rows:
            out_row = {fn: (row.get(fn) or "") for fn in fieldnames_out}
            w.writerow(out_row)


def _split_by_bst(mons: List[WaterMon]) -> Dict[str, List[str]]:
    """
    Split species into common/uncommon/rare by BST quantiles.
    Ensures MAGIKARP stays in common for fishing.
    """
    if not mons:
        return {"common": [], "uncommon": [], "rare": []}
    ordered = sorted(mons, key=lambda m: (m.bst, m.species))
    n = len(ordered)
    c_end = max(1, int(n * 0.45))
    u_end = max(c_end + 1, int(n * 0.80)) if n >= 3 else n

    common = [m.species for m in ordered[:c_end]]
    uncommon = [m.species for m in ordered[c_end:u_end]]
    rare = [m.species for m in ordered[u_end:]]

    if "MAGIKARP" not in common:
        common = ["MAGIKARP"] + [s for s in common if s != "MAGIKARP"]
    uncommon = [s for s in uncommon if s != "MAGIKARP"]
    rare = [s for s in rare if s != "MAGIKARP"]
    return {"common": common, "uncommon": uncommon, "rare": rare}


def _filter_types(mons: List[WaterMon], include_any: Sequence[str]) -> List[WaterMon]:
    want = {t.strip().upper() for t in include_any if t}
    if not want:
        return mons
    out: List[WaterMon] = []
    for m in mons:
        if m.type1 in want or m.type2 in want:
            out.append(m)
    return out


_ITEMISH_METHODS = {
    "EVO_STONE",
    "EVO_STONE_MALE",
    "EVO_STONE_FEMALE",
    "EVO_ITEM_DAY",
    "EVO_ITEM_NIGHT",
    "EVO_TRADE_ITEM",
    "EVO_TRADE",
    "EVO_TRADE_SPECIFIC_MON",
}


def _maybe_promote_special_evo(
    species: str,
    bank_base: int,
    slot_index_1based: int,
    rng: random.Random,
    evo_map: Dict[str, List[EvoEdge]],
    allowed: Optional[set[str]] = None,
    ev_level_map: Optional[Dict[str, int]] = None,
) -> str:
    """
    For non-level evolutions (stones/trades/items), only allow them as rare encounters.
    - Only slot 5 (rarest) is eligible.
    - Uses EvLevel from Water-Biome-Pokemon.csv (typically 50) to gate minimum bank level.
    """
    s = (species or "").strip().upper()
    if slot_index_1based != 5:
        return s

    edges = evo_map.get(s, [])
    special = [ed for ed in edges if ed.method in _ITEMISH_METHODS and ed.target and ed.target != "NONE"]
    if allowed is not None:
        special = [ed for ed in special if ed.target in allowed]
    if not special:
        return s

    base = int(bank_base or 0)
    min_base = (ev_level_map or {}).get(s, 50)
    if base < min_base:
        return s

    # Bias toward higher-level banks.
    p = 0.55 if base >= 50 else 0.15
    if rng.random() > p:
        return s

    # Deterministic-ish: shuffle, then pick one.
    rng.shuffle(special)
    return special[0].target


def _apply_evolution_rules(
    species: Sequence[str],
    level_pairs: Sequence[Tuple[int, int]],
    bank_base: int,
    rng: random.Random,
    evo_map: Dict[str, List[EvoEdge]],
    allowed: Optional[set[str]] = None,
    ev_level_map: Optional[Dict[str, int]] = None,
) -> List[str]:
    originals: List[str] = [(s or "").strip().upper() for s in (species[:5] + ["MAGIKARP"] * 5)[:5]]
    pairs: List[Tuple[int, int]] = list((level_pairs[:5] + [(2, 2)] * 5)[:5])

    # First, stage up via level rules using encounter max level.
    staged: List[str] = []
    for idx, original in enumerate(originals):
        _mi, ma = pairs[idx]
        staged.append(
            _evolve_via_level(original, ma, evo_map, allowed=allowed, ev_level_map=ev_level_map)
        )

    # If we're in a 50+ bank and Poliwhirl exists in this table, push it into the rarest slot.
    # This ensures Poliwrath/Politoed can exist as rare late-game encounters.
    base = int(bank_base or 0)
    if base >= 50 and "POLIWHIRL" in staged and staged[4] != "POLIWHIRL":
        swap_i = next((i for i, s in enumerate(staged) if s == "POLIWHIRL"), None)
        if swap_i is not None:
            staged[swap_i], staged[4] = staged[4], staged[swap_i]
            originals[swap_i], originals[4] = originals[4], originals[swap_i]
            pairs[swap_i], pairs[4] = pairs[4], pairs[swap_i]

    # Apply rarity gating and special-evo promotion.
    out: List[str] = []
    for idx, s in enumerate(staged):
        original = originals[idx]
        slot = idx + 1

        # Power-spike level evolutions should remain rare.
        if original == "MAGIKARP" and s == "GYARADOS":
            if slot != 5:
                s = "MAGIKARP"
            else:
                p = 0.45 if base >= 50 else 0.10
                if rng.random() > p:
                    s = "MAGIKARP"

        s = _maybe_promote_special_evo(
            s, base, slot, rng, evo_map, allowed=allowed, ev_level_map=ev_level_map
        )
        out.append(s)

    return out[:5]

def _stable_seed(bank_id: int, area_label: str) -> int:
    payload = f"{bank_id}:{area_label}".encode("utf-8", errors="replace")
    return int(zlib.adler32(payload))


def _read_legacy_hints(path: Path) -> Dict[int, LegacyBankHint]:
    """
    Best-effort parse of legacy Encounter-Data-Main.csv to get high-level hints.
    The file has 3 rows per bank (Morn/Day/Night) with bank id encoded in the integer part of '#'.
    """
    if not path.exists():
        return {}

    hints: Dict[int, LegacyBankHint] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_num = (row.get("#") or "").strip()
            if not raw_num:
                continue
            try:
                bank_id = int(float(raw_num))
            except ValueError:
                continue
            if bank_id in hints:
                continue  # first row per bank is enough

            water = (row.get("Water?") or "").strip()
            typing = (row.get("Typing") or "").strip()
            hints[bank_id] = LegacyBankHint(water=water, typing=typing)
    return hints


def _read_bank_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_grass_csv(path: Path) -> Tuple[List[int], List[str], bool]:
    """
    Returns (levels, species_set, has_real_data)
    """
    if not path.exists():
        return ([], [], False)
    levels: List[int] = []
    species: List[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lvl_raw = (row.get("Level") or "").strip()
            try:
                lvl = int(lvl_raw)
            except ValueError:
                lvl = 0
            if lvl:
                levels.append(lvl)
            for key in ("Morning", "Day", "Night"):
                s = (row.get(key) or "").strip()
                if s:
                    base = s.split("@", 1)[0].strip().upper()
                    if base and base != "NONE":
                        species.append(base)
    has_real = any(s != "NONE" for s in species) and any(l > 1 for l in levels)
    # Deduplicate while preserving order
    seen = set()
    uniq_species = []
    for s in species:
        if s not in seen:
            seen.add(s)
            uniq_species.append(s)
    return (levels, uniq_species, has_real)


def _mode_int(values: Sequence[int]) -> Optional[int]:
    if not values:
        return None
    counts: Dict[int, int] = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def _clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def _baseline_level(bank_id: int, grass_levels: Sequence[int], has_real_grass: bool) -> int:
    if has_real_grass:
        m = _mode_int([v for v in grass_levels if v > 0])
        if m is not None and m >= 2:
            return m
    # fallback for placeholder/unused banks: smooth progression with bank id
    return _clamp(2 + (bank_id // 4), 2, 70)


def _classify_env(bank_id: int, area_label: str, hint: LegacyBankHint) -> str:
    label = (area_label or "").strip().upper()
    water = (hint.water or "").strip().upper()
    typing = (hint.typing or "").strip().upper()

    if "ICE" in typing or "ICE" in label or "FROZEN" in label or "SNOW" in label or "COLD" in label:
        return "icy"
    if "OCEAN" in water:
        return "marine"
    if "CAVE" in water:
        return "cavewater"
    if water == "LAKE":
        return "fresh"

    if "ISLAND" in label or "NAVEl".upper() in label or "OCEAN" in label:
        return "marine"
    if any(k in label for k in ("CAVE", "PASSAGE", "VICTORY", "RELIC", "TUNNEL", "DEPTHS")):
        return "cavewater"
    return "generic"


def _filter_pool_by_bank_base(
    pool: Dict[str, List[str]], bank_base: int, high_level_only: set[str]
) -> Dict[str, List[str]]:
    """Exclude stone/item/trade evos (EvLevel 50+) from pools when bank_base < 50."""
    if bank_base >= 50 or not high_level_only:
        return pool
    exclude = high_level_only
    out = {}
    for tier, species in pool.items():
        filtered = [s for s in species if s not in exclude]
        out[tier] = filtered if filtered else species  # fallback to unfiltered if empty
    return out


def _pick_unique(rng: random.Random, pool: Sequence[str], k: int, avoid: Iterable[str] = ()) -> List[str]:
    avoid_set = set(a.upper() for a in avoid)
    choices = [p.upper() for p in pool if p and p.upper() not in avoid_set]
    if not choices:
        return ["MAGIKARP"] * k
    # If pool too small, allow repeats after exhausting uniques
    out: List[str] = []
    used: set[str] = set()
    for _ in range(k):
        avail = [c for c in choices if c not in used]
        if not avail:
            pick = rng.choice(choices)
        else:
            pick = rng.choice(avail)
            used.add(pick)
        out.append(pick)
    return out


def _build_pools(water_biome_path: Path) -> Dict[str, Dict[str, List[str]]]:
    mons = _read_water_biome_csv(water_biome_path)
    if not mons:
        # Fallback minimal pool (shouldn't happen if the curated list exists)
        return {"generic": {"common": ["MAGIKARP"], "uncommon": ["POLIWAG"], "rare": ["MILOTIC"]}}

    generic = _split_by_bst(mons)
    icy = _split_by_bst(_filter_types(mons, ["ICE"]))
    fresh = _split_by_bst(_filter_types(mons, ["GROUND"]))
    cavewater = _split_by_bst(_filter_types(mons, ["GHOST", "DARK", "ROCK"]))
    marine = _split_by_bst(_filter_types(mons, ["FLYING", "POISON"]))

    def norm(p: Dict[str, List[str]]) -> Dict[str, List[str]]:
        return {
            "common": p.get("common") or generic["common"],
            "uncommon": p.get("uncommon") or generic["uncommon"],
            "rare": p.get("rare") or generic["rare"],
        }

    return {
        "marine": norm(marine),
        "fresh": norm(fresh),
        "cavewater": norm(cavewater),
        "icy": norm(icy),
        "generic": norm(generic),
    }


def _level_pair(min_level: int, max_level: int) -> Tuple[int, int]:
    mi = max(2, int(min_level))
    ma = max(mi, int(max_level))
    return (mi, ma)


def _levels_for_kind(base: int, kind: str) -> List[Tuple[int, int]]:
    """
    Returns 5 (min,max) pairs for the requested encounter kind.
    """
    b0 = max(2, int(base))
    # Rods should stay meaningfully lower-level even late-game.
    if kind == "OldRod":
        b = min(b0, 20)
    elif kind == "GoodRod":
        b = min(b0, 40)
    elif kind == "SuperRod":
        b = min(b0 + 3, 70)
    else:
        b = b0
    if kind == "Surf":
        raw = [(b - 1, b + 1), (b, b + 2), (b, b + 2), (b + 1, b + 3), (b + 1, b + 4)]
    elif kind == "OldRod":
        raw = [(b - 6, b - 4), (b - 6, b - 3), (b - 5, b - 3), (b - 4, b - 2), (b - 4, b - 1)]
    elif kind == "GoodRod":
        raw = [(b - 4, b - 2), (b - 4, b - 1), (b - 3, b), (b - 2, b), (b - 1, b + 1)]
    elif kind == "SuperRod":
        raw = [(b, b + 3), (b + 1, b + 4), (b + 2, b + 5), (b + 2, b + 6), (b + 3, b + 7)]
    else:
        raw = [(b, b + 2)] * 5
    return [_level_pair(mi, ma) for (mi, ma) in raw]


def _write_surf_csv(path: Path, rate: int, species: Sequence[str], level_pairs: Sequence[Tuple[int, int]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Type", "Rate", "Slot", "Species", "MinLevel", "MaxLevel"])
        for i in range(5):
            sp = (species[i] if i < len(species) else "MAGIKARP").upper()
            mi, ma = level_pairs[i] if i < len(level_pairs) else (2, 2)
            w.writerow(["Surf", int(rate), i + 1, sp, mi, ma])


def _write_fishing_csv(
    path: Path,
    rates: Dict[str, int],
    species_by_rod: Dict[str, Sequence[str]],
    levels_by_rod: Dict[str, Sequence[Tuple[int, int]]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["RodType", "Rate", "Slot", "Species", "MinLevel", "MaxLevel"])
        for rod in ("OldRod", "GoodRod", "SuperRod"):
            rate = int(rates.get(rod, 0) or 0)
            species = species_by_rod.get(rod, [])
            level_pairs = levels_by_rod.get(rod, [])
            for i in range(5):
                sp = (species[i] if i < len(species) else "MAGIKARP").upper()
                mi, ma = level_pairs[i] if i < len(level_pairs) else (2, 2)
                w.writerow([rod, rate, i + 1, sp, mi, ma])


SLOT_PCTS_5 = [60, 30, 5, 4, 1]  # Slot 1..5 encounter chances (Surf + all rods)


def _tier_plan(base: int, kind: str) -> List[List[str]]:
    """
    Decide which BST-tier pools to use per slot. As `base` rises, stronger mons shift forward.
    """
    b = int(base or 0)
    if kind == "Surf":
        if b < 20:
            return [["common"], ["common"], ["uncommon", "common"], ["uncommon"], ["rare", "uncommon"]]
        if b < 40:
            return [["common", "uncommon"], ["uncommon", "common"], ["uncommon", "rare"], ["rare", "uncommon"], ["rare"]]
        return [["uncommon", "rare"], ["uncommon", "rare"], ["rare", "uncommon"], ["rare"], ["rare"]]

    if kind == "OldRod":
        return [["magikarp"], ["magikarp"], ["common"], ["common"], ["uncommon", "common"]]

    if kind == "GoodRod":
        if b < 20:
            return [["common"], ["common"], ["uncommon", "common"], ["uncommon"], ["rare", "uncommon"]]
        if b < 40:
            return [["common", "uncommon"], ["common", "uncommon"], ["uncommon"], ["uncommon", "rare"], ["rare"]]
        return [["uncommon"], ["uncommon", "rare"], ["rare", "uncommon"], ["rare"], ["rare"]]

    if kind == "SuperRod":
        if b < 20:
            return [["uncommon", "common"], ["uncommon"], ["rare", "uncommon"], ["rare", "uncommon"], ["rare", "uncommon"]]
        if b < 40:
            return [["uncommon"], ["uncommon", "rare"], ["rare", "uncommon"], ["rare", "uncommon"], ["rare", "uncommon"]]
        return [["rare", "uncommon"], ["rare", "uncommon"], ["rare", "uncommon"], ["rare", "uncommon"], ["rare", "uncommon"]]

    return [["common"], ["common"], ["uncommon"], ["uncommon"], ["rare"]]


def _select_species_for_levels(
    rng: random.Random,
    pool: Dict[str, List[str]],
    kind: str,
    base: int,
    desired_levels: Sequence[Tuple[int, int]],
    legal_ranges: Dict[str, Tuple[int, int]],
    avoid: Iterable[str] = (),
) -> Tuple[List[str], List[Tuple[int, int]]]:
    """
    Pick 5 species + clamp each slot's (min,max) into that species' legal range.
    """
    plan = _tier_plan(base, kind)
    used = {a.strip().upper() for a in avoid if a}
    out_species: List[str] = []
    out_levels: List[Tuple[int, int]] = []

    for i in range(5):
        tiers = plan[i] if i < len(plan) else ["common"]
        tier_lists: List[List[str]] = []
        for tier in tiers:
            if tier == "magikarp":
                tier_lists.append(["MAGIKARP"])
            else:
                tier_lists.append([s.upper() for s in (pool.get(tier, []) or [])])

        # Fallback if everything is empty in this env
        if not any(tier_lists):
            tier_lists = [["MAGIKARP"]]
        for lst in tier_lists:
            rng.shuffle(lst)
        mi0, ma0 = desired_levels[i] if i < len(desired_levels) else (2, 2)

        picked_sp: Optional[str] = None
        picked_lv: Optional[Tuple[int, int]] = None

        def try_pick_from(lst: List[str], allow_used: bool) -> None:
            nonlocal picked_sp, picked_lv
            for sp in lst:
                if (not allow_used) and sp in used:
                    continue
                lo, hi = legal_ranges.get(sp, (2, 70))
                mi = max(int(mi0), int(lo))
                ma = min(int(ma0), int(hi))
                if mi > ma:
                    continue
                picked_sp = sp
                picked_lv = (mi, ma)
                return

        # Pass 1: prefer unused species; Pass 2: allow repeats if needed.
        for allow_used in (False, True):
            if picked_sp is not None:
                break
            for lst in tier_lists:
                try_pick_from(lst, allow_used=allow_used)
                if picked_sp is not None:
                    break

        if picked_sp is None or picked_lv is None:
            sp = "MAGIKARP"
            lo, hi = legal_ranges.get(sp, (2, 20))
            mi = max(int(mi0), int(lo))
            ma = min(int(ma0), int(hi))
            if mi > ma:
                mi, ma = int(lo), int(hi)
            picked_sp, picked_lv = sp, (mi, ma)

        out_species.append(picked_sp)
        out_levels.append(picked_lv)
        used.add(picked_sp)

    return out_species[:5], out_levels[:5]


def _iter_bank_dirs(banks_dir: Path) -> Iterable[Path]:
    for entry in sorted(banks_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not re.match(r"^E\d{4}_", entry.name):
            continue
        yield entry


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Generate Surf + Fishing encounters for all banks (0–255).")
    ap.add_argument("--banks-dir", type=Path, default=BANKS_DIR)
    ap.add_argument("--legacy-main", type=Path, default=LEGACY_MAIN)
    ap.add_argument("--evodata", type=Path, default=DEFAULT_EVODATA)
    ap.add_argument("--water-biome", type=Path, default=WATER_BIOME_CSV)
    ap.add_argument(
        "--sync-water-biome-ranges",
        action="store_true",
        help="Rewrite Water-Biome-Pokemon.csv to include EvMin/EvMax ranges (fills missing values).",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only-bank", type=int, default=None, help="If set, only generate for this BankId.")
    args = ap.parse_args(argv)

    if args.sync_water_biome_ranges:
        _sync_water_biome_ranges_inplace(args.water_biome, args.evodata)
        print(f"Synced EvMin/EvMax in: {args.water_biome}")
        return 0

    water_mons = _read_water_biome_csv(args.water_biome)
    meta: Dict[str, WaterMon] = {m.species: m for m in water_mons}
    allowed_species = set(meta.keys())
    pools = _build_pools(args.water_biome)
    hints = _read_legacy_hints(args.legacy_main)

    evo_map = _load_evo_map(args.evodata)
    # Minimum legal level for evolved forms that evolve by level.
    rev_level_req: Dict[str, int] = {}
    for src, edges in evo_map.items():
        for ed in edges:
            if ed.method.startswith("EVO_LEVEL") and ed.param > 0:
                rev_level_req[ed.target] = min(rev_level_req.get(ed.target, 999), ed.param)

    legal_ranges: Dict[str, Tuple[int, int]] = {}
    for sp, m in meta.items():
        lo = int(m.wild_min or 2)
        hi = int(m.wild_max or 70)
        lo = max(2, lo, int(rev_level_req.get(sp, 0) or 0))
        hi = min(70, hi)
        if hi < lo:
            hi = lo
        legal_ranges[sp] = (lo, hi)

    written = 0
    for bank_dir in _iter_bank_dirs(args.banks_dir):
        bank_json = _read_bank_json(bank_dir / "bank.json")
        bank_id = int(bank_json.get("bank_id", -1))
        area_label = str(bank_json.get("area_label", bank_dir.name)).strip()
        if bank_id < 0:
            continue
        if args.only_bank is not None and bank_id != int(args.only_bank):
            continue

        grass_levels, _, has_real_grass = _read_grass_csv(bank_dir / "Grass.csv")
        base = _baseline_level(bank_id, grass_levels, has_real_grass)
        env = _classify_env(bank_id, area_label, hints.get(bank_id, LegacyBankHint()))

        rng = random.Random(_stable_seed(bank_id, area_label))
        pool = pools.get(env, pools["generic"])

        surf_rate = int(bank_json.get("surfrate", 15) or 15)
        rates = {
            "OldRod": int(bank_json.get("oldrodrate", 25) or 25),
            "GoodRod": int(bank_json.get("goodrodrate", 50) or 50),
            "SuperRod": int(bank_json.get("superrodrate", 75) or 75),
        }

        # Pick legal species and clamp level ranges into each species' EvMin/EvMax.
        surf_species, surf_levels = _select_species_for_levels(
            rng, pool, "Surf", base, _levels_for_kind(base, "Surf"), legal_ranges
        )
        old_species, old_levels = _select_species_for_levels(
            rng, pool, "OldRod", base, _levels_for_kind(base, "OldRod"), legal_ranges
        )
        good_species, good_levels = _select_species_for_levels(
            rng, pool, "GoodRod", base, _levels_for_kind(base, "GoodRod"), legal_ranges
        )
        super_species, super_levels = _select_species_for_levels(
            rng, pool, "SuperRod", base, _levels_for_kind(base, "SuperRod"), legal_ranges
        )
        fish_species = {"OldRod": old_species, "GoodRod": good_species, "SuperRod": super_species}
        fish_levels = {"OldRod": old_levels, "GoodRod": good_levels, "SuperRod": super_levels}

        if args.dry_run:
            print(
                f"[dry-run] bank {bank_id:03d} {area_label} env={env} base={base} "
                f"surf={surf_species} superrod={fish_species['SuperRod']}"
            )
            continue

        _write_surf_csv(bank_dir / "Surf.csv", surf_rate, surf_species, surf_levels)
        _write_fishing_csv(bank_dir / "Fishing.csv", rates, fish_species, fish_levels)
        written += 1

    if args.dry_run:
        return 0
    print(f"Wrote Surf+Fishing for {written} bank folders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


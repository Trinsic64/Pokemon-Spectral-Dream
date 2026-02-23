#!/usr/bin/env python3
"""
build_index.py

Generates human- and AI-readable INDEX.md files:
  ../INDEX.md                 - top-level overview of all DSPRE contents
  ../scripts/INDEX.md         - per-script: ID, map name(s), command count
  ../textArchives/INDEX.md    - per-archive: ID, map name(s), entry count, preview
  ../constants/INDEX.md       - overview of all constant tables
  ../analysis/cross-reference.md - notable findings from analysis

Standard-library only.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ANALYSIS_ROOT / "analysis"
CONSTANTS_DIR = ANALYSIS_ROOT / "constants"
SCRIPTS_DIR = ANALYSIS_ROOT / "scripts"
TEXT_DIR = ANALYSIS_ROOT / "textArchives"

TODAY = date.today().isoformat()


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  -> {path.relative_to(ANALYSIS_ROOT)}")


def build_top_level_index(
    script_summary: list[dict],
    text_summary: list[dict],
) -> str:
    script_count = len(list(SCRIPTS_DIR.glob("*.script")))
    text_count = len(list(TEXT_DIR.glob("*.txt")))
    total_text_entries = sum(int(r.get("entry_count", 0) or 0) for r in text_summary)
    total_script_cmds = sum(int(r.get("total_commands", 0) or 0) for r in script_summary)

    return f"""# DSPRE Contents Analysis — Index

Generated: {TODAY}

This directory contains a copy of all files extracted from the game ROM by DSPRE
(DS Pokemon ROM Editor), plus analysis scripts and generated lookup tables to help
AI agents and developers understand the game's data without requiring DSPRE.

---

## What This Directory Contains

| Folder | Contents | File Count |
|--------|----------|------------|
| `scripts/` | Game event scripts (one per map, decompiled from NARCs) | {script_count} `.script` files |
| `textArchives/` | All in-game dialogue and UI text strings | {text_count} `.txt` files |
| `data/` | Binary asset NARCs, DS graphics/model files, overlays | ~260 files |
| `constants/` | CSV lookup tables for species, item, move, ability IDs | 5 `.csv` files |
| `analysis/` | Generated summaries and cross-reference reports | CSV + MD files |
| `tools/` | Python scripts that generated this analysis | `.py` files |

---

## Authority: What DSPRE Covers vs. hg-engine

**DSPRE** handles only map scripts and text. It does NOT define game data such as
trainer parties, wild encounters, Pokemon stats, or item effects. Those are all
defined in `Tools/hg-engine/` and built from source:

| Data Type | Authoritative Source |
|-----------|----------------------|
| Map scripts | `scripts/*.script` (this directory) |
| Dialogue / text | `textArchives/*.txt` (this directory) |
| Map headers (link scripts ↔ maps) | `Data/Header-Data/Header-Data-Main.csv` |
| Pokemon species IDs | `Tools/hg-engine/include/constants/species.h` |
| Item IDs | `Tools/hg-engine/include/constants/item.h` |
| Move IDs | `Tools/hg-engine/include/constants/moves.h` |
| Ability IDs | `Tools/hg-engine/include/constants/ability.h` |
| Trainer data | `Tools/hg-engine/armips/data/trainers/trainers.s` |
| Wild encounters | `Tools/hg-engine/armips/data/encounters.s` |
| Pokemon base stats | `Tools/hg-engine/armips/data/mondata.s` |

---

## Quick Stats

- **Script files**: {script_count} files, {total_script_cmds:,} total commands
- **Text archives**: {text_count} files, {total_text_entries:,} total text entries
- **How scripts link to maps**: See `Data/Header-Data/Header-Data-Main.csv` column `Script File`
- **How text archives link to maps**: See column `Text Archive` in the same CSV

---

## Navigation

- Browse scripts by map: [`scripts/INDEX.md`](scripts/INDEX.md)
- Browse text archives by map: [`textArchives/INDEX.md`](textArchives/INDEX.md)
- Look up species/item/move IDs: [`constants/INDEX.md`](constants/INDEX.md)
- Cross-reference findings: [`analysis/cross-reference.md`](analysis/cross-reference.md)
- Raw analysis data: [`analysis/script-summary.csv`](analysis/script-summary.csv),
  [`analysis/text-archive-summary.csv`](analysis/text-archive-summary.csv)

---

## Script File Format

Scripts are decompiled from ROM NARCs by DSPRE. Each `.script` file may contain:
- **Scripts** (event handlers triggered by NPCs, items on ground, map entry, etc.)
- **Functions** (subroutines called by scripts)
- **Actions** (movement sequences for NPCs)

Example snippet:
```
Script 1:
    LockAll
    FacePlayer
    Message 0          // text entry 0 from the matching text archive
    WaitButton
    CloseMessage
    ReleaseAll
End
```

Key commands to know:
| Command | Meaning |
|---------|---------|
| `Message N` | Display text entry N from this map's text archive |
| `GiveItem ITEM_X` | Give player an item (use constants/items.csv to decode) |
| `GivePokemon SPECIES_X` | Give player a Pokemon |
| `CheckFlag 0xNNNN` | Check a story/event flag |
| `SetFlag 0xNNNN` | Set a story/event flag |
| `SetVar 0xNNNN val` | Set a game variable |
| `CommonScript N` | Call a globally-shared script |

---

## How to Use This Analysis

1. **Find a map's script**: Look up the map's `Internal Name` in
   `Data/Header-Data/Header-Data-Main.csv`, read `Script File` column.
   Open `scripts/NNNN.script`.

2. **Decode an item/species ID**: Check `constants/items.csv` or `constants/species.csv`.

3. **Understand what a script does**: Read the `.script` file + the matching
   `textArchives/NNNN.txt` (same number as `Text Archive` column in Header CSV).

4. **Find all scripts using a specific item**: Search `analysis/script-commands.csv`
   where `command=GiveItem` and `args` contains the item name or ID.
"""


def build_scripts_index(script_summary: list[dict]) -> str:
    lines = [
        "# Scripts Index",
        "",
        f"Generated: {TODAY}",
        "",
        f"Total script files: {len(script_summary)}",
        "",
        "Each script file corresponds to one or more maps. The `Script File` column in",
        "`Data/Header-Data/Header-Data-Main.csv` links map headers to script numbers.",
        "",
        "| Script # | Maps Using This Script | Scripts | Functions | Actions | Total Commands | Items Referenced | Pokemon Referenced |",
        "|----------|----------------------|---------|-----------|---------|---------------|-----------------|-------------------|",
    ]

    for row in script_summary:
        maps = row.get("maps_using_script", "") or "—"
        # Truncate long map lists
        if len(maps) > 80:
            maps = maps[:77] + "..."
        items = row.get("item_refs", "") or "—"
        if len(items) > 50:
            items = items[:47] + "..."
        pokemon = row.get("pokemon_refs", "") or "—"
        if len(pokemon) > 50:
            pokemon = pokemon[:47] + "..."

        lines.append(
            f"| {row['script_file']} "
            f"| {maps} "
            f"| {row.get('script_count', 0)} "
            f"| {row.get('function_count', 0)} "
            f"| {row.get('action_count', 0)} "
            f"| {row.get('total_commands', 0)} "
            f"| {items} "
            f"| {pokemon} |"
        )

    return "\n".join(lines) + "\n"


def build_text_index(text_summary: list[dict]) -> str:
    lines = [
        "# Text Archives Index",
        "",
        f"Generated: {TODAY}",
        "",
        f"Total text archive files: {len(text_summary)}",
        "",
        "Each text archive holds numbered string entries. Scripts reference them via",
        "`Message N` commands. The `Text Archive` column in",
        "`Data/Header-Data/Header-Data-Main.csv` links map headers to archive numbers.",
        "",
        "| Archive # | Maps Using This Archive | Entries | Has Control Codes | First Entry Preview |",
        "|-----------|------------------------|---------|-------------------|---------------------|",
    ]

    for row in text_summary:
        maps = row.get("maps_using_archive", "") or "—"
        if len(maps) > 60:
            maps = maps[:57] + "..."
        preview = row.get("first_entry_preview", "") or "—"
        # Escape pipe characters in preview
        preview = preview.replace("|", "\\|").replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:57] + "..."

        lines.append(
            f"| {row['archive_file']} "
            f"| {maps} "
            f"| {row.get('entry_count', 0)} "
            f"| {row.get('has_control_codes', '—')} "
            f"| {preview} |"
        )

    return "\n".join(lines) + "\n"


def build_constants_index() -> str:
    csv_files = sorted(CONSTANTS_DIR.glob("*.csv"))
    table_lines = [
        "| File | Description | Row Count |",
        "|------|-------------|-----------|",
    ]
    for cf in csv_files:
        rows = read_csv(cf)
        desc_map = {
            "species": "Pokemon species ID → SPECIES_* constant name",
            "items": "Item ID → ITEM_* constant name",
            "moves": "Move ID → MOVE_* constant name",
            "abilities": "Ability ID → ABILITY_* constant name",
            "trainerclasses": "Trainer class ID → TRAINERCLASS_* name",
            "maps": "Map/header ID constants",
        }
        desc = desc_map.get(cf.stem, cf.stem)
        table_lines.append(f"| `{cf.name}` | {desc} | {len(rows)} |")

    return f"""# Constants Index

Generated: {TODAY}

Lookup tables extracted from `Tools/hg-engine/include/constants/` C headers.
Each CSV has three columns: `name`, `raw_value`, `numeric_id`.

## Files

{chr(10).join(table_lines)}

## Usage

To look up what item ID `17` is:
- Open `items.csv`, find the row where `numeric_id = 17` → name is `ITEM_POTION`

To decode `SPECIES_BULBASAUR` to a number:
- Open `species.csv`, find `name = SPECIES_BULBASAUR` → `numeric_id = 1`

## Source Headers

All constants are parsed from `Tools/hg-engine/include/constants/`. If a constant
is missing or incorrect here, the header file is authoritative.
"""


def build_data_index() -> str:
    data_dir = ANALYSIS_ROOT / "data"
    overlay_dir = data_dir / "overlay"
    pbr_dir = data_dir / "pbr"

    def ext_counts(d: Path) -> dict[str, int]:
        counts: dict[str, int] = {}
        if not d.exists():
            return counts
        for f in d.iterdir():
            if f.is_file():
                ext = f.suffix or "(no ext)"
                counts[ext] = counts.get(ext, 0) + 1
        return counts

    root_counts = ext_counts(data_dir)
    overlay_counts = ext_counts(overlay_dir)
    pbr_counts = ext_counts(pbr_dir)

    def fmt_counts(c: dict) -> str:
        return ", ".join(f"`{ext}` × {cnt}" for ext, cnt in sorted(c.items()))

    return f"""# Data Directory Index

Generated: {TODAY}

This directory contains binary asset files copied from the ROM's `data/` sections.
Most files here are **not human-readable** without specialized Nintendo DS tools.

---

## Subdirectories

### `data/` (root — map/area assets)

File types: {fmt_counts(root_counts)}

| Extension | Format | Description |
|-----------|--------|-------------|
| `.narc` | NARC | Nintendo ARChive — packed container of related files (graphics, sound, etc.) |
| `.NCGR` / `.ncgr` | NCGR | Nintendo Character Graphic Resource — tile/sprite pixel data |
| `.NCLR` / `.nclr` | NCLR | Nintendo CoLor Resource — palette data |
| `.NCER` | NCER | Nintendo CEll Resource — sprite cell layout |
| `.NANR` | NANR | Nintendo ANimation Resource — animation sequences |
| `.NSCR` | NSCR | Nintendo SCreen Resource — background tilemap |
| `.nsbmd` | NSBMD | Nintendo DS Binary Model Data — 3D model |
| `.nsbtx` | NSBTX | Nintendo DS Binary Texture — 3D texture atlas |
| `.nsbca` | NSBCA | Nintendo DS Binary Character Animation — 3D animation |
| `.bin` | Binary | Raw binary data (misc) |
| `.dat` | Binary | Raw data file |
| `.atr` | Binary | Attribute file |
| `.txt` | Text | Area lighting configuration (human-readable) |

### `overlay/` — ROM Overlays

File types: {fmt_counts(overlay_counts)}

ROM overlays are compiled ARM code sections that are loaded into RAM at runtime.
They cannot be read as plain text — disassembly tools (e.g. ndsdis, ghidra-nds) are
required to analyze their contents.

The key overlays in this ROM are modified by `Tools/hg-engine/` which patches
them during the build process.

### `pbr/` — Pokemon Battle Revolution References

File types: {fmt_counts(pbr_counts)}

Contains `.inc` include files listing NARC and SDAT asset paths used for
Pokemon Battle Revolution battle animations and sounds.

---

## Note on NARC Files

NARC files are containers — each holds a numbered list of sub-files. To extract
sub-files from a NARC you need a tool such as:
- DSPRE (DS Pokemon ROM Editor)
- knarc / Tinke
- NitroPacker

The `.narc` files in this directory are **binary** — they cannot be read or
edited as plain text.
"""


def build_cross_reference(script_summary: list[dict], text_summary: list[dict]) -> str:
    # Find most-used items in scripts
    item_freq: dict[str, int] = {}
    pokemon_freq: dict[str, int] = {}
    scripts_with_items = 0
    scripts_with_pokemon = 0

    for row in script_summary:
        items_str = row.get("item_refs", "")
        if items_str:
            scripts_with_items += 1
            for item in items_str.split(";"):
                item = item.strip()
                if item:
                    item_freq[item] = item_freq.get(item, 0) + 1

        poke_str = row.get("pokemon_refs", "")
        if poke_str:
            scripts_with_pokemon += 1
            for poke in poke_str.split(";"):
                poke = poke.strip()
                if poke:
                    pokemon_freq[poke] = pokemon_freq.get(poke, 0) + 1

    top_items = sorted(item_freq.items(), key=lambda x: -x[1])[:20]
    top_pokemon = sorted(pokemon_freq.items(), key=lambda x: -x[1])[:20]

    # Scripts that reference both items AND pokemon
    rich_scripts = [
        r for r in script_summary
        if r.get("item_refs") and r.get("pokemon_refs")
    ]

    # Largest text archives
    top_text = sorted(
        text_summary,
        key=lambda r: int(r.get("entry_count", 0) or 0),
        reverse=True,
    )[:15]

    lines = [
        "# Cross-Reference Report",
        "",
        f"Generated: {TODAY}",
        "",
        "---",
        "",
        "## Item References in Scripts",
        "",
        f"Scripts referencing items: **{scripts_with_items}**",
        "",
        "### Most Frequently Referenced Items",
        "",
        "| Item | Scripts Referencing It |",
        "|------|------------------------|",
    ]
    for item, cnt in top_items:
        lines.append(f"| `{item}` | {cnt} |")

    lines += [
        "",
        "---",
        "",
        "## Pokemon References in Scripts",
        "",
        f"Scripts referencing Pokemon: **{scripts_with_pokemon}**",
        "",
        "### Most Frequently Referenced Pokemon",
        "",
        "| Pokemon | Scripts Referencing It |",
        "|---------|------------------------|",
    ]
    for poke, cnt in top_pokemon:
        lines.append(f"| `{poke}` | {cnt} |")

    lines += [
        "",
        "---",
        "",
        "## Scripts with Both Items and Pokemon",
        "",
        f"Count: {len(rich_scripts)}",
        "",
        "| Script | Maps | Items | Pokemon |",
        "|--------|------|-------|---------|",
    ]
    for r in rich_scripts[:30]:
        maps = (r.get("maps_using_script", "") or "—")[:40]
        items = (r.get("item_refs", "") or "—")[:40]
        pokes = (r.get("pokemon_refs", "") or "—")[:40]
        lines.append(f"| {r['script_file']} | {maps} | {items} | {pokes} |")

    lines += [
        "",
        "---",
        "",
        "## Largest Text Archives",
        "",
        "| Archive | Maps | Entry Count | First Entry Preview |",
        "|---------|------|-------------|---------------------|",
    ]
    for r in top_text:
        maps = (r.get("maps_using_archive", "") or "—")[:40]
        preview = (r.get("first_entry_preview", "") or "—").replace("|", "\\|")[:50]
        lines.append(f"| {r['archive_file']} | {maps} | {r.get('entry_count', 0)} | {preview} |")

    return "\n".join(lines) + "\n"


def main() -> None:
    print("Building index files...")

    script_summary = read_csv(ANALYSIS_DIR / "script-summary.csv")
    text_summary = read_csv(ANALYSIS_DIR / "text-archive-summary.csv")

    write_md(ANALYSIS_ROOT / "INDEX.md", build_top_level_index(script_summary, text_summary))
    write_md(SCRIPTS_DIR / "INDEX.md", build_scripts_index(script_summary))
    write_md(TEXT_DIR / "INDEX.md", build_text_index(text_summary))
    write_md(CONSTANTS_DIR / "INDEX.md", build_constants_index())
    write_md(ANALYSIS_ROOT / "data" / "INDEX.md", build_data_index())
    write_md(ANALYSIS_DIR / "cross-reference.md", build_cross_reference(script_summary, text_summary))

    print("\nDone.")


if __name__ == "__main__":
    main()

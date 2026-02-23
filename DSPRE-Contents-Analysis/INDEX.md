# DSPRE Contents Analysis — Index

Generated: 2026-02-23

This directory contains a copy of all files extracted from the game ROM by DSPRE
(DS Pokemon ROM Editor), plus analysis scripts and generated lookup tables to help
AI agents and developers understand the game's data without requiring DSPRE.

---

## What This Directory Contains

| Folder | Contents | File Count |
|--------|----------|------------|
| `scripts/` | Game event scripts (one per map, decompiled from NARCs) | 965 `.script` files |
| `textArchives/` | All in-game dialogue and UI text strings | 890 `.txt` files |
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

- **Script files**: 965 files, 89,748 total commands
- **Text archives**: 890 files, 70,581 total text entries
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

# Unpacked Directory Index

Generated: 2026-02-23

This directory contains binary files extracted from ROM NARCs by DSPRE when the
ROM project was last opened. Total: **33,275 files** across 31 subdirectories.

These are raw binary files — not human-readable as text. Each subdirectory
corresponds to one NARC archive from the ROM.

## Subdirectories

| Subdirectory | File Count | Description |
|--------------|------------|-------------|
| `areaData/` | 128 | Area type/terrain assignment binary files |
| `buildingConfigFiles/` | 128 | Building placement config binary files |
| `buildingTextures/` | 128 | Building texture pack binary files |
| `dynamicHeaders/` | 546 | Map header binary files (parsed by update_header_data.py) |
| `eggMoves/` | 1 | Pokemon egg move binary data |
| `encounters/` | 256 | Wild encounter binary files (one per bank) |
| `eventFiles/` | 491 | Map event binary files — NPCs, warps, floor items, triggers |
| `evolutions/` | 1,393 | Pokemon evolution data binary files |
| `exteriorBuildingModels/` | 427 | Exterior 3D building model binary files |
| `headbutt/` | 540 | Headbutt tree encounter binary files |
| `interiorBuildingModels/` | 301 | Interior 3D building model binary files |
| `itemData/` | 2,558 | Item property binary files (price, hold effect, etc.) |
| `itemIcons/` | 5,122 | Item icon graphic binary files |
| `learnsets/` | 1 | Pokemon learnset binary data |
| `maps/` | 2,452 | Map geometry/collision binary files |
| `mapTextures/` | 128 | Map texture pack binary files |
| `matrices/` | 299 | Area matrix layout binary files |
| `monIcons/` | 1,400 | Pokemon party icon graphic binary files |
| `moveData/` | 924 | Move property binary files (power, accuracy, effect) |
| `otherPokemonBattleSprites/` | 261 | Misc Pokemon battle sprite binary files |
| `OWSprites/` | 1,553 | Overworld character sprite binary files |
| `personalPokeData/` | 1,393 | Pokemon base stat / personal data binary files |
| `pokemonBattleSprites/` | 8,358 | Pokemon battle sprite binary files |
| `safariZone/` | 12 | Safari Zone encounter binary files |
| `scripts/` | 965 | Script binary files (binary form of expanded/scripts/) |
| `synthOverlay/` | 16 | Synthesised overlay binary files |
| `textArchives/` | 890 | Text archive binary files (binary form of expanded/textArchives/) |
| `tradeData/` | 13 | In-game trade data binary files |
| `trainerGraphics/` | 645 | Trainer graphic binary files |
| `trainerParty/` | 973 | Trainer party data binary files |
| `trainerProperties/` | 973 | Trainer property data binary files |

## Notes

- `eventFiles/` has been parsed into human-readable CSVs in `events/`
- `encounters/`, `trainerProperties/`, `trainerParty/` are authoritative in
  `Tools/hg-engine/` — DSPRE binary files are supplementary reference only
- `personalPokeData/`, `moveData/` are authoritative in `Tools/hg-engine/armips/data/`
- `dynamicHeaders/` is parsed by `Tools/Update-Header-Data-Script/update_header_data.py`

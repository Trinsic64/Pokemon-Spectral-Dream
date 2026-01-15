# Encounter Data Sync Tool

This tool keeps encounter data easy to browse/edit while staying round-trip compatible with the build file:

- **HG-Engine source file**: `Data/Encounter-Data/encounters.s`
- **Per-bank folders**: `Data/Encounter-Data/Encounters/E####_<Area>/`
- **Main encounter CSVs (new canonical)**:
  - `Data/Encounter-Data/Grass-Encounter-Data-Main.csv` (3 rows per bank: Morn/Day/Night)
  - `Data/Encounter-Data/Surf-Encounter-Data-Main.csv`
  - `Data/Encounter-Data/Fishing-Encounter-Data-Main.csv`
  - `Data/Encounter-Data/RockSmash-Encounter-Data-Main.csv`

The legacy file `Data/Encounter-Data/Encounter-Data-Main.csv` is **not modified**.

## Quick start

From repo root:

```bash
python Tools/Update-Encounter-Data-Script/update_encounter_data.py generate-dirs
python Tools/Update-Encounter-Data-Script/update_encounter_data.py build-mains
```

Dry-run rebuild of `encounters.s`:

```bash
python Tools/Update-Encounter-Data-Script/update_encounter_data.py build-encounters-s --dry-run
```

## Folder contents per bank

Each `E####_<Area>/` folder contains:

- `bank.json` (lossless parsed data; used for round-tripping)
- `Grass.csv` (12 slots + walklevels for Morn/Day/Night)
- `Surf.csv` (5 slots with min/max levels)
- `Fishing.csv` (Old/Good/Super rod, 5 each)
- `RockSmash.csv` (2 slots)
- `Swarms.csv` (grass/surf/good/super)
- `Regions.csv` (Hoenn/Sinnoh slots)
- `README.md` (summary + “used by headers” cross-reference)

## Header cross-reference

The tool looks up which headers use each encounter bank by scanning:

- `Data/Header-Data/Header-Data-Main.csv` column `Wild File`


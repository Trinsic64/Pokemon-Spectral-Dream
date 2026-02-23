# Constants Index

Generated: 2026-02-23

Lookup tables extracted from `Tools/hg-engine/include/constants/` C headers.
Each CSV has three columns: `name`, `raw_value`, `numeric_id`.

## Files

| File | Description | Row Count |
|------|-------------|-----------|
| `abilities.csv` | Ability ID → ABILITY_* constant name | 311 |
| `items.csv` | Item ID → ITEM_* constant name | 2558 |
| `maps.csv` | Map/header ID constants | 540 |
| `moves.csv` | Move ID → MOVE_* constant name | 956 |
| `species.csv` | Pokemon species ID → SPECIES_* constant name | 1401 |
| `trainerclasses.csv` | Trainer class ID → TRAINERCLASS_* name | 137 |

## Usage

To look up what item ID `17` is:
- Open `items.csv`, find the row where `numeric_id = 17` → name is `ITEM_POTION`

To decode `SPECIES_BULBASAUR` to a number:
- Open `species.csv`, find `name = SPECIES_BULBASAUR` → `numeric_id = 1`

## Source Headers

All constants are parsed from `Tools/hg-engine/include/constants/`. If a constant
is missing or incorrect here, the header file is authoritative.

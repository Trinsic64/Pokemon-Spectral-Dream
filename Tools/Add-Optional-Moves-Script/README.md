# Add Optional Moves Script

Expands Trainer-X-Data.csv files from the 9-row format to the 21-row format, populating Optional Move 1-12 cells with legal moves from Learnset-Data.csv.

## Legal Move Rules

Moves are considered legal based on the learn method and Pokemon level:

| Method | Rule | Example |
|-------|------|---------|
| **tm** | Always legal (learned via TM/HM items) | TOXIC, ICE_BEAM |
| **egg** | Always legal (learned via breeding) | SCREECH, COUNTER |
| **level-up** | Legal iff Pokemon Level >= move Level | RATTATA Lv.2: TACKLE (Lv.1) legal, QUICK_ATTACK (Lv.4) illegal |

Empty Level for level-up moves is treated as Level 1.

## Usage

```bash
# Dry-run (report what would be updated without writing)
python add_optional_moves.py --dry-run

# Run with backup before overwrite
python add_optional_moves.py --backup-dir backups

# Run with custom paths
python add_optional_moves.py --learnset Data/Pokemon-Data/Learnset-Data.csv --trainers-dir Data/Trainer-Data/Trainers
```

## Options

- `--learnset` — Path to Learnset-Data.csv (default: Data/Pokemon-Data/Learnset-Data.csv)
- `--trainers-dir` — Path to Trainers directory (default: Data/Trainer-Data/Trainers)
- `--backup-dir` — Backup CSVs before overwrite (default: no backup)
- `--dry-run` — Report changes without writing files

## Output Format

The script expands each Trainer CSV to include all legal optional moves:

- Species, Level, Ability, Held Item
- Move 1, Move 2, Move 3, Move 4
- Optional Move 1 through Optional Move N (as many as needed for all legal moves)

Optional moves are ALL legal alternatives not already in Move 1-4. You can copy any optional move into a Move slot when editing teams.

## Notes

- Skips T0-TEMPLATE folder
- Species not found in learnset: Optional moves left empty, warning printed
- VARIES level: treated as Level 100 to maximize legal options
- Species variants (e.g. RATTATA_ALOLAN): falls back to base form (RATTATA) if variant not in learnset

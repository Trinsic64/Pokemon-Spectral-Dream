# Trainer Data Sync Tool

This tool manages the project’s trainer data in three layers:

- **HG-Engine source file**: `Data/Trainer-Data/trainers.s`
- **Developer-facing index sheet**: `Data/Trainer-Data/Trainer-Data-Main.csv`
- **Per-trainer folders**: `Data/Trainer-Data/Trainers/T<ID>-<Class>-<Name>/`

The goal is to make trainers easy to browse/edit for new developers, while keeping the build files (`trainers.s`) accurate and rebuildable.

## Quick start

From repo root:

```bash
python Tools/Update-Trainer-Data-Script/update_trainer_data.py generate-dirs
```

Dry-run:

```bash
python Tools/Update-Trainer-Data-Script/update_trainer_data.py generate-dirs --dry-run
```

## Outputs

- Mismatch review output:
  - `Data/Trainer-Data/Trainers-Mismatch/run_YYYYMMDD-HHMMSS/`
  - `Data/Trainer-Data/Trainers-Mismatch/LATEST.txt`
- Tool backups:
  - `Tools/Update-Trainer-Data-Script/backups/Trainer-Data-Main_YYYYMMDD-HHMMSS.csv`
- Tool reports:
  - `Tools/Update-Trainer-Data-Script/reports/mismatch_report_YYYYMMDD-HHMMSS.csv`

## Per-trainer folder contents

Each trainer folder contains:

- `Trainer-<id>-Data.csv` (grid format for editing per-Pokémon details)
- `meta.json` (lossless parsed/exported data from `trainers.s`, used for round-tripping)

**Important:** `Trainer-<id>-Data.csv` uses constant-like tokens without prefixes:
- Species: `RATTATA` (from `SPECIES_RATTATA`)
- Moves: `TAIL_WHIP` (from `MOVE_TAIL_WHIP`)
- Ability: `RUN_AWAY` (from `ABILITY_RUN_AWAY`)

Forms (e.g. `monwithform SPECIES_SCIZOR, 1`) are preserved in `meta.json`.

## Battle Type semantics (new system)

`Trainer-Data-Main.csv`’s **Battle Type** column can be one of:

- **`Double Battle Soft`**: record-only; trainer stays `SINGLE_BATTLE` in `trainers.s`. Used when *two overworld trainers* can jointly trigger a double battle if they both lock-on (handled manually in DSPRE / by the developer).
- **`Double Battle Hard`**: must be `DOUBLE_BATTLE` in `trainers.s` (one trainer entry, 2–6 Pokémon).

Back-compat: legacy values containing `Double Battle` (without “hard”) are treated as **Soft** by the tool.


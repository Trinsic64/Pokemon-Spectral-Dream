# Pokemon Spectral Dream

Pokemon Spectral Dream is a Nintendo DS ROM-hack project with a repo focused on **source data**, **documentation**, and **developer tooling** that helps keep the project consistent and rebuildable.

This repository contains **project data and tools**, but **does not include** any Nintendo DS ROM files or extracted ROM contents.

## Legal / distribution note

- ROMs and extracted ROM contents (for example, DSPRE unpack folders) are **not distributed** in this repo.
- Instead, the repo provides **patch artifacts** and **project data** so you can work using your **own legally obtained ROM**.

If you are a contributor: do **not** commit ROM binaries (`.nds`) or extracted ROM contents into this repository.

## Quick start (BYO ROM)

1) Put your ROM at `ROM/Pokemon-Spectral-Dream.nds` (it is ignored by git).
2) Apply the patch in `ROM/` to your ROM (see `ROM/README.md`).
3) Run tools from repo root, for example:

```bash
python Tools/Update-Encounter-Data-Script/update_encounter_data.py --help
python Tools/Update-Trainer-Data-Script/update_trainer_data.py --help
python Tools/Update-Header-Data-Script/update_header_data.py --help
```

See `ROM/README.md` for details.

## Repository layout

- **`Data/`**: the project’s human-editable and source-controlled data (CSV/JSON/scripts/docs).  
  This is where most collaboration happens.
- **`Maps/`**: map project files used by Pokémon DS Map Studio (see “Maps” below).
- **`ROM/`**: patch artifacts and *local-only* ROM inputs (ignored by git).  
  See `ROM/README.md`.
- **`Tools/`**: repo tooling used to generate/sync/round-trip project data (Python scripts with docs).

## Tools (what they do)

Most tools are intentionally **standard-library only** Python scripts to keep setup simple.

- **Encounter data tool** (`Tools/Update-Encounter-Data-Script/`)
  - Works with `Data/Encounter-Data/encounters.s`
  - Generates per-bank folders under `Data/Encounter-Data/Encounters/`
  - Can rebuild main encounter CSVs and round-trip back to `encounters.s`
  - Docs: `Tools/Update-Encounter-Data-Script/docs/README.md`
- **Trainer data tool** (`Tools/Update-Trainer-Data-Script/`)
  - Works with `Data/Trainer-Data/trainers.s` and `Data/Trainer-Data/Trainer-Data-Main.csv`
  - Generates per-trainer folders under `Data/Trainer-Data/Trainers/`
  - Can rebuild `trainers.s` from the per-trainer folders
  - Docs: `Tools/Update-Trainer-Data-Script/docs/README.md`
- **Header data tool** (`Tools/Update-Header-Data-Script/`)
  - Updates `Data/Header-Data/Header-Data-Main.csv` and per-header notes
  - Requires a *local* DSPRE extraction at `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` (ignored by git)
  - Docs: `Tools/Update-Header-Data-Script/docs/README.md`

## Maps

The map assets in `Maps/` are only compatible with **AdAstra’s fork** of **Pokémon DS Map Studio** (maps re-saved with that fork may be incompatible with vanilla).

- Tool release: `https://github.com/AdAstra-LD/Pokemon-DS-Map-Studio/releases/tag/v2.2.1`

See `Maps/README.md` for the same note.

# Roguelike (Baseline) — Round-trip & Build Workflow

This project keeps **source-controlled data** in `Data/`, while the **actual ROM content** lives in:
- `ROM/Pokemon-Spectral-Dream.nds` (local-only)
- `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` (local-only DSPRE extraction)

## 1) Sync headers (always first after extracting)

From repo root:

```bash
python Tools/Update-Header-Data-Script/update_header_data.py update
python Tools/Update-Header-Data-Script/update_header_data.py validate
```

This updates:
- `Data/Header-Data/Header-Data-Main.csv`
- `Data/Header-Data/Headers/*/README.md` and `INDEX.md`

## 2) Script/Text round-trip (DSPRE)

### Source-controlled exports
- Scripts: `Data/Script-Data/Scripts/*.script`
- Text archives: `Data/Text-Data/*.txt`

### Roguelike baseline script files touched (must be imported back to ROM)
- `Data/Script-Data/Scripts/0843.script` (starter bootstrap adds Roguelike flags/var + Pokédex + starter kit)
- Gyms (set `ROGUE_STORY_STAGE` and optional cleared flags on badge awards):
  - `0886.script` (Gym 1)
  - `0877.script` (Gym 2)
  - `0786.script` (Gym 3)
  - `0760.script` (Gym 4)
  - `0943.script` (Gym 5)
  - `0778.script` (Gym 6)
  - `0859.script` (Gym 7)
  - `0922.script` (Gym 8 + E4 unlocked)
- Completion hooks:
  - `0825.script` (Hall of Fame)
  - `0107.script` (endgame screen trigger on a specific map script)

### DSPRE import/export policy
- **Export** scripts/text from the ROM into the `Data/` folders above.
- Make edits in `Data/`.
- **Import** the edited script/text back into the ROM (either directly into `Pokemon-Spectral-Dream.nds`, or into the extraction + re-pack per your DSPRE workflow).

## 3) Trainers & encounters round-trip (repo tools → hg-engine build inputs)

### Trainers
- Generate per-trainer folders (and mismatch report):

```bash
python Tools/Update-Trainer-Data-Script/update_trainer_data.py generate-dirs
```

- Rebuild build-file used by hg-engine:

```bash
python Tools/Update-Trainer-Data-Script/update_trainer_data.py build-trainers-s
```

Outputs into `Data/Trainer-Data/trainers.s`.

### Encounters

```bash
python Tools/Update-Encounter-Data-Script/update_encounter_data.py generate-dirs
python Tools/Update-Encounter-Data-Script/update_encounter_data.py build-mains
python Tools/Update-Encounter-Data-Script/update_encounter_data.py build-encounters-s
```

Outputs into `Data/Encounter-Data/encounters.s`.

## 4) Build a distributable ROM (hg-engine)

This repo contains a working clone at `Tools/hg-engine/`.

High-level flow:
1. Copy your base ROM into the hg-engine folder as `rom.nds`
2. Ensure `Data/Trainer-Data/trainers.s` and `Data/Encounter-Data/encounters.s` are up-to-date
3. Build with `make` (recommended under WSL/MSYS2 per hg-engine requirements)

Result is typically an output ROM (see `Tools/hg-engine/Makefile` variables `ROMNAME`/`BUILDROM`).

## 5) Patch artifacts

Once you have a rebuilt/updated `.nds`, create a patch (xdelta) against the correct base ROM and place the patch under `ROM/` (do not commit ROM binaries).


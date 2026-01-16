# Header Data Sync Tool

This tool keeps the project’s header metadata **up-to-date** and **easy for new developers to query**.

- **Header CSV**: `Data/Header-Data/Header-Data-Main.csv`
- **Source of truth (local-only)**: `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` (generated from your own ROM; not in git)
- **Per-header notes**: `Data/Header-Data/Headers/####_InternalName/`

## Setup (one-time)

1) Place your ROM at `ROM/Pokemon-Spectral-Dream.nds` (ignored by git).
2) Extract/unpack using DSPRE (or your preferred workflow) into `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` (ignored by git).

## Quick start

From repo root:

```bash
python Tools/Update-Header-Data-Script/update_header_data.py update
```

Dry-run (no writes):

```bash
python Tools/Update-Header-Data-Script/update_header_data.py update --dry-run
```

Validation only (no writes):

```bash
python Tools/Update-Header-Data-Script/update_header_data.py validate
```

## Outputs

- Backups:
  - `Tools/Update-Header-Data-Script/backups/Header-Data-Main_YYYYMMDD-HHMMSS.csv`
- Reports:
  - `Tools/Update-Header-Data-Script/reports/header_summary_YYYYMMDD-HHMMSS.txt`
  - `Tools/Update-Header-Data-Script/reports/header_changes_YYYYMMDD-HHMMSS.csv`
  - `Tools/Update-Header-Data-Script/reports/header_missing_files_YYYYMMDD-HHMMSS.csv`
- Notes (generated/maintained):
  - `Data/Header-Data/Headers/0009_R01/README.md` (auto-generated; overwritten each run)
  - `Data/Header-Data/Headers/0009_R01/notes.md` (human notes; preserved)
  - `Data/Header-Data/Headers/INDEX.md` (auto-generated)

## Editing policy

The tool always overwrites columns that have a 1:1 ROM source (e.g. `Matrix`, `Script File`, `Event File`, `Wild File`, etc.).

It preserves curated fields like `Type` unless blank/`TBD`.

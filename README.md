# Pokemon Spectral Dream

This repository contains **project data and tooling**, but **does not include** any Nintendo DS ROM files or extracted ROM contents.

## Legal / distribution note

- ROMs (and extracted ROM contents like `DSPRE_contents`) are **not distributed** in this repo.
- You can use the provided patch file(s) in `ROM/` to patch your **own** ROM.

## Quick start (BYO ROM)

1) Put your ROM at `ROM/Pokemon-Spectral-Dream.nds` (it is ignored by git).
2) If you need header syncing, extract/unpack using DSPRE into `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` (also ignored by git).
3) Run tools from repo root, for example:

```bash
python Tools/Update-Encounter-Data-Script/update_encounter_data.py --help
python Tools/Update-Trainer-Data-Script/update_trainer_data.py --help
python Tools/Update-Header-Data-Script/update_header_data.py --help
```

See `ROM/README.md` for details.

## ROM folder (BYO ROM)

This repo **does not** include any `.nds` ROMs or extracted ROM contents.

- **Place your ROM here**: `ROM/Pokemon-Spectral-Dream.nds`
  - This is **ignored by git** (see `.gitignore`).

## Header tooling (DSPRE extraction)

Some tools (notably `Tools/Update-Header-Data-Script/update_header_data.py`) read from a local extraction folder:

- `ROM/Pokemon-Spectral-Dream_DSPRE_contents/`

That folder is **local-only** and **ignored by git**. Create it by extracting/unpacking your ROM using DSPRE (or your preferred workflow) into that path.

## Patch artifacts

This folder contains patch artifacts you can apply to your own base ROM:

- `Pokemon-Spectral-Dream.xdelta` (xdelta patch)
- `Pokemon-Spectral-Dream.mch` (cheat/patch file used by some emulators)

To apply the `.xdelta`, use an xdelta tool (e.g. `xdelta3`) and make sure your **input/base ROM matches** the exact ROM the patch was created from.


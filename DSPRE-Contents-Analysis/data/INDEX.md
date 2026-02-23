# Data Directory Index

Generated: 2026-02-23

This directory contains binary asset files copied from the ROM's `data/` sections.
Most files here are **not human-readable** without specialized Nintendo DS tools.

---

## Subdirectories

### `data/` (root — map/area assets)

File types: `.NANR` × 5, `.NCER` × 4, `.NCGR` × 8, `.NCLR` × 7, `.NSCR` × 2, `.atr` × 1, `.bin` × 2, `.dat` × 8, `.md` × 1, `.narc` × 19, `.ncgr` × 5, `.nclr` × 2, `.nsbca` × 2, `.nsbmd` × 2, `.nsbtx` × 11, `.txt` × 5

| Extension | Format | Description |
|-----------|--------|-------------|
| `.narc` | NARC | Nintendo ARChive — packed container of related files (graphics, sound, etc.) |
| `.NCGR` / `.ncgr` | NCGR | Nintendo Character Graphic Resource — tile/sprite pixel data |
| `.NCLR` / `.nclr` | NCLR | Nintendo CoLor Resource — palette data |
| `.NCER` | NCER | Nintendo CEll Resource — sprite cell layout |
| `.NANR` | NANR | Nintendo ANimation Resource — animation sequences |
| `.NSCR` | NSCR | Nintendo SCreen Resource — background tilemap |
| `.nsbmd` | NSBMD | Nintendo DS Binary Model Data — 3D model |
| `.nsbtx` | NSBTX | Nintendo DS Binary Texture — 3D texture atlas |
| `.nsbca` | NSBCA | Nintendo DS Binary Character Animation — 3D animation |
| `.bin` | Binary | Raw binary data (misc) |
| `.dat` | Binary | Raw data file |
| `.atr` | Binary | Attribute file |
| `.txt` | Text | Area lighting configuration (human-readable) |

### `overlay/` — ROM Overlays

File types: `.backup` × 2, `.bin` × 149

ROM overlays are compiled ARM code sections that are loaded into RAM at runtime.
They cannot be read as plain text — disassembly tools (e.g. ndsdis, ghidra-nds) are
required to analyze their contents.

The key overlays in this ROM are modified by `Tools/hg-engine/` which patches
them during the build process.

### `pbr/` — Pokemon Battle Revolution References

File types: `.inc` × 1, `.narc` × 21, `.sdat` × 1

Contains `.inc` include files listing NARC and SDAT asset paths used for
Pokemon Battle Revolution battle animations and sounds.

---

## Note on NARC Files

NARC files are containers — each holds a numbered list of sub-files. To extract
sub-files from a NARC you need a tool such as:
- DSPRE (DS Pokemon ROM Editor)
- knarc / Tinke
- NitroPacker

The `.narc` files in this directory are **binary** — they cannot be read or
edited as plain text.

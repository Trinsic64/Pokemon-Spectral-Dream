# Design — Using HeartGold reference data (`Data/Heart-Gold-Data`)

HG reference root:
`Data/Heart-Gold-Data/HG-ROM/Heart-Gold-v0-1_DSPRE_contents/`

This is a DSPRE extraction with the same high-level structure as your Spectral Dream extraction:
- `unpacked/dynamicHeaders/` (header wiring)
- `unpacked/scripts/` (script NARC entries, numeric files)
- `unpacked/eventFiles/`
- `unpacked/textArchives/`
- `data/fielddata/maptable/mapname.bin` (header → internal name table)
- plus `expanded/textArchives/*.txt` (human-readable text dumps)

## Recommended workflow: generate an HG header index CSV (so we can find E4 rooms by header ID)
Your repo already has a header-indexing tool:
`Tools/Update-Header-Data-Script/update_header_data.py`

When you’re ready, run it against the HG extraction but **write to a separate CSV**:

```bash
python Tools/Update-Header-Data-Script/update_header_data.py update ^
  --dspre-root "Data/Heart-Gold-Data/HG-ROM/Heart-Gold-v0-1_DSPRE_contents" ^
  --csv "Data/Heart-Gold-Data/HG-Headers.csv" ^
  --notes-dir "Data/Heart-Gold-Data/HG-Headers"
```

This produces:
- `Data/Heart-Gold-Data/HG-Headers.csv` (header→script/event/text mapping)
- `Data/Heart-Gold-Data/HG-Headers/*/README.md` (per-header reference)

With this, you can quickly locate:
- Indigo Plateau / Elite Four headers
- which script files and text archives HG uses for E4 gating, room transitions, Hall of Fame, etc.

## Text reuse (fastest)
HG text dumps already exist in:
`Data/Heart-Gold-Data/HG-ROM/Heart-Gold-v0-1_DSPRE_contents/expanded/textArchives/*.txt`

Use these as the source when you want:
- a “standard HG” style line for a guard, door, or badge gate
- short functional dialogue you don’t want to rewrite

## Script/event reuse (when you want HG behavior)
If you choose to reuse HG’s E4 behavior later (instead of the MVP “E4 challenge flow”):
- Identify the relevant HG headers in `HG-Headers.csv`
- Copy/adapt the corresponding NARC entries from:
  - `.../unpacked/scripts/<####>`
  - `.../unpacked/eventFiles/<####>`
  - `.../unpacked/textArchives/<####>`

Then map them to your Spectral Dream headers via `Data/Header-Data/Header-Data-Main.csv`.

## What we’ll reuse first (recommended)
Given your constraints (minimal story, playable, future Standard-ready):
- **Text**: reuse HG lines for generic gating and short “system” explanations.
- **Patterns**: reuse HG’s *structure* (badge checks, door unlocks, victory flow), not necessarily the exact maps.
- **E4**: for now, keep the MVP “E4 challenge flow” driven by your existing trainer IDs; later swap to HG E4 assets if desired.


# Update-Item-Data-Script

Compiles item property and in-game location data from ROM source files into
four categorised CSV sheets under `Data/Item-Data/`.

---

## Quick Start

```powershell
# From the repo root
python Tools/Update-Item-Data-Script/update_item_data.py update
```

That's it. The four CSV files will be written (or refreshed) in `Data/Item-Data/`.

---

## Output Files

| File | Contents | Rows (typical) |
|------|----------|---------------|
| `Data/Item-Data/All-Item-Data.csv` | Every item — master reference | ~2 500 |
| `Data/Item-Data/Medicine-Data.csv` | `POCKET_MEDICINE` items only | ~70 |
| `Data/Item-Data/Berry-Data.csv` | `POCKET_BERRIES` items only | ~65 |
| `Data/Item-Data/PokeBall-Data.csv` | `POCKET_BALLS` items only | ~27 |

---

## Data Sources

### 1. `Tools/hg-engine/include/constants/item.h`

Defines all `ITEM_XXX` constants as `#define ITEM_NAME numeric_id`.
Used to resolve both symbolic names and numeric IDs throughout the pipeline.

### 2. `Tools/hg-engine/data/itemdata/itemdata.c`

C source file with one `[ITEM_XXX] = { … }` struct per item.
Provides: price, fieldPocket, holdEffect, naturalGiftPower/Type, partyUseParam
heal/restore flags, EV modifiers, and more.

The `ITEM_PRICE(n)` macro encodes prices split across `.price` (low 16 bits)
and `.price_high` (bits 16–19); the tool reconstructs the full integer.

### 3. `Tools/hg-engine/src/field/mart.c`

Defines static per-location shop inventory arrays (`u16 sXxxMart[]`) and the
badge-gated mart (`sBadgeMart[]`).

Static arrays are indexed by **declaration order** (first array = index 0).
Script files set `Var 0x8004` to this index before calling the mart CommonScript.

### 4. `Data/Header-Data/Header-Data-Main.csv` + Script Files

Each header row references a `Script File` number.
The tool reads every script under
`ROM/Pokemon-Spectral-Dream_DSPRE_contents/expanded/scripts/`
and detects two patterns:

| Pattern | Meaning |
|---------|---------|
| `SetVar 0x8004 N` → `CommonScript 2048/2052` | Header opens mart inventory at index N |
| `SetVar 0x8004 N` → `CommonScript 2033` | Header gives item with ID N |
| `GiveItem ITEM_XXX qty` | Header gives item directly |

---

## Column Schemas

### All-Item-Data.csv

| Column | Description |
|--------|-------------|
| `Item_ID` | Numeric item ID |
| `Item_Name` | `ITEM_XXX` constant name |
| `Pocket` | Bag pocket label (Items / Medicine / Poké Balls / etc.) |
| `Price` | Buy price in Pokédollars |
| `Sell_Price` | Sell price (`Price ÷ 2`) |
| `Hold_Effect` | Hold-effect ID (see `hold_item_effects.h`) |
| `Hold_Effect_Param` | Parameter for hold effect |
| `Fling_Power` | Base power when flung |
| `Fling_Effect` | Effect ID when flung |
| `Natural_Gift_Power` | Natural Gift move base power |
| `Natural_Gift_Type` | Natural Gift move type (numeric) |
| `Prevent_Toss` | TRUE if the item cannot be tossed |
| `Selectable` | TRUE if selectable in battle |
| `Field_Use_Func` | Field-use handler ID |
| `Battle_Use_Func` | Battle-use handler ID |
| `Shop_Locations` | Pipe-separated list of headers/marts where this item is sold |
| `Given_At_Locations` | Pipe-separated list of headers where this item is given |

### Medicine-Data.csv

All columns from `All-Item-Data.csv` **except** `Pocket`, `Hold_Effect*`,
`Fling_*`, `Natural_Gift_*`, `Prevent_Toss`, `Selectable`, `Field/Battle_Use_Func`,
plus these medicine-specific columns:

| Column | Description |
|--------|-------------|
| `HP_Restore` | TRUE if restores HP |
| `HP_Restore_Param` | Amount restored (255 = full) |
| `SLP/PSN/BRN/FRZ/PRZ/CFS/INF_Heal` | Status condition cured |
| `Guard_Spec` | TRUE if guard spec effect |
| `Revive` / `Revive_All` | Revive one / all fainted |
| `Level_Up` / `Evolve` | Triggers level-up / evolution |
| `PP_Restore` / `PP_Restore_Param` | Restores PP; amount (255 = all) |
| `PP_Restore_All` / `PP_Up` / `PP_Max` | PP variants |
| `ATK/DEF/SpATK/SpDEF/Speed/Accuracy/CritRate_Stages` | Stat-stage changes |
| `HP/ATK/DEF/Speed/SpATK/SpDEF_EV_Up` | EV raises |
| `HP/ATK/DEF/Speed/SpATK/SpDEF_EV_Param` | EV raise amount |
| `Friendship_Lo/Med/Hi` | Friendship modifier tiers |

### Berry-Data.csv

| Column | Description |
|--------|-------------|
| `Item_ID`, `Item_Name`, `Price`, `Sell_Price` | Core fields |
| `Hold_Effect`, `Hold_Effect_Param` | Berry held-item behaviour |
| `Natural_Gift_Power`, `Natural_Gift_Type` | Natural Gift stats |
| `Pluck_Effect` | Effect when stolen by Pluck/Bug Bite |
| `SLP/PSN/BRN/FRZ/PRZ_Heal` | Status healed when consumed |
| `HP_Restore`, `HP_Restore_Param` | HP restored when consumed |
| `Shop_Locations`, `Given_At_Locations` | Location data |

### PokeBall-Data.csv

| Column | Description |
|--------|-------------|
| `Item_ID`, `Item_Name`, `Price`, `Sell_Price` | Core fields |
| `Hold_Effect`, `Hold_Effect_Param` | Held-item effect (unused for most balls) |
| `Shop_Locations`, `Given_At_Locations` | Where the ball is sold or received |

---

## CLI Reference

```
python update_item_data.py [update|validate] [options]
```

| Flag | Default | Description |
|------|---------|-------------|
| `update` | *(default cmd)* | Parse all sources and write CSVs |
| `validate` | | Check that all source files exist |
| `--repo-root PATH` | 2 levels up from script | Override repository root |
| `--item-h PATH` | auto-derived | Path to `item.h` |
| `--itemdata-c PATH` | auto-derived | Path to `itemdata.c` |
| `--mart-c PATH` | auto-derived | Path to `mart.c` |
| `--header-csv PATH` | auto-derived | Path to `Header-Data-Main.csv` |
| `--scripts-dir PATH` | auto-derived | Path to `expanded/scripts/` |
| `--output-dir PATH` | `Data/Item-Data/` | Where to write the four CSVs |
| `--backup-dir PATH` | `backups/` | Where to write CSV backups |
| `--reports-dir PATH` | `reports/` | Where to write run reports |
| `--dry-run` | off | Parse without writing any files |
| `--verbose` | off | Extra output (reserved) |

---

## Reports

Each run generates four timestamped files in `reports/`:

| File | Description |
|------|-------------|
| `item_summary_<ts>.txt` | Human-readable run summary |
| `mart_index_map_<ts>.csv` | Maps mart array index → C name → item list |
| `badge_mart_<ts>.csv` | Badge-gated mart items and their unlock requirements |
| `script_analysis_<ts>.csv` | Per-header mart indices and give-item IDs found |
| `items_no_location_<ts>.csv` | Items with no shop or gift location detected |

Existing CSVs are backed up (if non-empty) to `backups/<name>_<timestamp>.csv`
before each run.

---

## Mart Inventory Index System

PokéMart NPC scripts follow this pattern:

```
SetVar 0x8004 N      ← N = static array index from mart.c
CommonScript 2011    ← open NPC dialogue
CommonScript 2048    ← open regular MartScreen
  (or 2052 for special MartScreen)
```

The index N maps to the static arrays in `mart.c` **in declaration order**:

| Index | C Name | Location |
|-------|--------|----------|
| 0 | `sCherrygroveCityMart` | Air Mail, Heal Ball |
| 1 | `sVioletCityMart` | Tunnel Mail, Heal Ball, Net Ball |
| 2 | `sAzaleaCityMart` | Bloom Mail, Heal Ball, Net Ball |
| 3 | `sGoldenrodDepartmentUpper2F` | Potions, status heals |
| 4 | `sGoldenrodDepartmentLower2F` | Balls, Repels, Mail |
| 5 | `sGoldenrodDepartment3F` | X-items |
| 6 | `sGoldenrodDepartment4F` | Vitamins |
| 7 | `sGoldenrodDepartment5F` | TMs (Goldenrod set) |
| 8 | `sGoldenrodHerbs` | Heal/Energy Powder, Roots |
| 9 | `sEcruteakMart` | Heart Mail, Heal Ball, Net Ball |
| 10 | `sOlivineMart` | Heart Mail, Heal Ball, Net Ball |
| 11 | `sCianwoodPharmacy` | Potions, Full Heal, Revive |
| 12 | `sBlackthornAndBattleFrontierMart` | Air Mail, Net Ball, Dusk Ball |
| 13 | `sIndigoPlateau` | Ultra Ball, Max Repel, Max Potion, … |
| 14 | `sVermilionAndSafariMart` | Air Mail, Nest Ball, Dusk Ball, Quick Ball |
| 15 | `sSaffronMart` | Air Mail, Dusk Ball, Quick Ball |
| 16 | `sLavenderMart` | Air Mail, Dusk Ball, Quick Ball |
| 17 | `sCeruleanMart` | Air Mail, Quick Ball |
| 18 | `sCeladonDepartmentUpper2F` | Potions, status heals |
| 19 | `sCeladonDepartmentLower2F` | Balls, Repels, Mail |
| 20 | `sCeladonDepartment3F` | TMs (Celadon set) |
| 21 | `sCeladonDepartment4F` | Mail items |
| 22 | `sCeladonDepartmentLeft5F` | X-items |
| 23 | `sCeladonDepartmentRight5F` | Vitamins |
| 24 | `sFuschiaMart` | Steel Mail, Dusk Ball, Quick Ball |
| 25 | `sPewterMart` | Steel Mail, Nest Ball, Quick Ball |
| 26 | `sViridianMart` | Steel Mail, Net Ball, Heal Ball |
| 27 | `sMtMoonSquare` | Poke Doll, Drinks, Repel, Heart Mail |
| 28 | `sMahoganyPreRocketHideout` | Tiny Mushroom, Poke Ball, Potion |
| 29 | `sMahoganyPostRocketHideout` | Great Ball, Super Potion, Antidote, … |

The badge-gated mart (`sBadgeMart`) is the standard PokéMart that unlocks
progressively — items appear as the player earns badges.

---

## Adding or Modifying Mart Inventories

1. Edit `Tools/hg-engine/src/field/mart.c` to add/change an array.
2. Optionally update the script file for the relevant header to set the correct
   `SetVar 0x8004 N` index.
3. Re-run this tool: `python Tools/Update-Item-Data-Script/update_item_data.py update`

The CSVs will be regenerated automatically.

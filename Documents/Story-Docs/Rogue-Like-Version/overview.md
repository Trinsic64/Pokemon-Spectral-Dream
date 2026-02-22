# Roguelike (Baseline) — Overview

This “Roguelike” version is the **minimum playable baseline** of Pokémon Spectral Dream.

## What it is
- **Fixed progression** (no procedural/randomized content).
- **Bare-minimum story**: only the scenes/events needed to keep the game playable and to gate progression.
- **Core mechanics focus**: exploration, trainers, gyms, badges, and endgame completion.

## What it is not
- Not a separate fork that requires starting over later.
- Not a randomized roguelite run system.
- Not a full narrative/cutscene pass.

## Design rules (to stay Standard-ready)
- **Use HGSS scripts / CommonScripts / text when possible**.
- New story logic should be **small** and expressed as:
  - a small set of **flags + one stage variable**
  - repeatable gating patterns (guards, warps, “unlock next route”)
- Any new scripts/text must be **safe to extend** for the Standard version (add scenes/branches without rewriting core gates).

## Sources of truth (repo)
- **Map header index**: `Data/Header-Data/Header-Data-Main.csv`
- **Per-map notes**: `Data/Header-Data/Headers/<####_InternalName>/notes.md`
- **Trainer roster**: `Data/Trainer-Data/Trainer-Data-Main.csv`
- **Flags/vars registry**: `Data/Flag-Data/Flag-Data-Main.csv`, `Data/Variable-Data/Variable-Data-Main.csv`

## Playability definition (MVP)
- New game starts and you can move.
- Starter + Pokédex + a small item kit are granted.
- Progression gates work through Gym 1 → Gym 8 → Elite Four (minimal cutscenes OK).

## Utility unlock roadmap (HGSS-aligned)
This is the “when should the player have X?” checklist for the Roguelike baseline. **Prefer keeping vanilla HGSS gift points** unless they conflict with your simplified critical path.

### By `ROGUE_STORY_STAGE` milestone
- **Stage 1** (starter chosen; before Gym 1)
  - **Pokédex** (already granted in starter flow)
  - **Running Shoes** (system unlock; not an inventory item)
  - **Town Map** (`ITEM_TOWN_MAP` = `442`)
  - **Early optional**: **Apricorn Box** (`ITEM_APRICORN_BOX` = `468`) is already gifted by `0079_LOBA_05_HS09` (script `0228`)
- **Stage 2** (post Gym 1; before Gym 2)
  - **Old Rod** (`ITEM_OLD_ROD` = `445`) — vanilla HGSS: Route 32 PokéCenter fisherman
  - **HM01 Cut** — vanilla HGSS: Ilex Forest (Farfetch’d)
- **Stage 3** (post Gym 2; before Gym 3)
  - **HM06 Rock Smash** — vanilla HGSS: Route 36
  - **Bike** (`ITEM_BIKE` = `450`) — vanilla HGSS: Goldenrod Bike Shop
- **Stage 5** (post Gym 4; before Gym 5)
  - **HM03 Surf** — vanilla HGSS: Ecruteak (Dance Theater event)
  - **Dowsing Machine** (`ITEM_DOWSING_MACHINE` = `471`) — vanilla HGSS: Ecruteak house gift
  - **HM04 Strength** — vanilla HGSS: Route 42 (hiker outside Mt. Mortar)
- **Stage 6** (post Gym 5; before Gym 6)
  - **HM02 Fly** — vanilla HGSS: Cianwood (after beating Chuck, from wife)
  - **Good Rod** (`ITEM_GOOD_ROD` = `446`) — vanilla HGSS: Olivine Fishing Guru
- **Stage 8** (post Gym 7; before Gym 8 / endgame)
  - **HM05 Whirlpool** — vanilla HGSS: Team Rocket HQ (from Lance)
  - **Super Rod** (`ITEM_SUPER_ROD` = `447`) — vanilla HGSS: Route 12 Fishing Guru
- **Stage 9** (post Gym 8; endgame)
  - **HM07 Waterfall** — vanilla HGSS: Ice Path (1F)
  - Set `ROGUE_E4_UNLOCKED` and route into Elite Four flow
- **Postgame (optional / Standard-ready)**
  - **HM08 Rock Climb** — vanilla HGSS: Pallet Town (Oak, after 16 badges)

### Existing HGSS content to preserve (examples you called out)
- `0013_MAUN_03_HS01` → script `0847`: **dialogue only** (no gifts)
- `0015_MAUN_05_HS02` → script `0854`: **dialogue only** (no gifts)
- `0079_LOBA_05_HS09` → script `0228`: **gives Apricorn Box once** (flag `109`, item `468`)
- `0117_MELT_10_HS12` → script `0139`: currently **empty** (good candidate slot if we need a repurposed gift point)
- `0118_MELT_11_GV02` → script `0244`: **dialogue only**
- `0137_DANB_01_GH02` → script `0235`: **dialogue only**

### External HGSS reference links (for quick lookup)
- [PokémonDB HM locations (HGSS)](https://pokemondb.net/heartgold-soulsilver/hms)
- [StrategyWiki key items list (HGSS)](https://strategywiki.org/wiki/Pok%C3%A9mon_HeartGold_and_SoulSilver/Key_Items)

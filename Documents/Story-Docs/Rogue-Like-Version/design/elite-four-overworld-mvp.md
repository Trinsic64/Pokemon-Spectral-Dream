# Design — Elite Four MVP (trainers exist, overworld not built)

You confirmed:
- **E4 trainers already exist** in `Data/Trainer-Data/Trainer-Data-Main.csv`
- **E4 overworld/maps are not implemented yet**

## Chosen MVP approach
**Approach 1 (minimal custom facility)**, but implemented as an **E4 challenge flow** that can run from:
- an NPC in the **settings room**, or
- a dedicated “E4 Terminal” room/header (small interior map)

This makes the Roguelike baseline **completable now** without waiting on overworld map work.

Later, when E4 maps exist, we keep the same trainer IDs + story flags and swap the entry method to a real Indigo/E4 facility.

## Required gating
Entry condition (either is acceptable):
- Badge 8 obtained, OR
- `FLAG_ROGUE_E4_UNLOCKED` (`0xA01` / dec `2561`) is TRUE

## Trainer IDs (recommended defaults)
Pick one variant each (you can override in `templates/elite-four.md`):
- **Bruno**: 923 (`E4 1.1.1`)
- **Karen**: 925 (`E4 2.1.1`)
- **Koga**: 927 (`E4 3.1.1`, Double Battle)
  - If you want single battles only, pick a non-double variant (update trainer sheet accordingly).
- **Will**: 931 (`E4 4.1.1`)
- **Champion (Finn)**: 933 (`E4 CHAMP 1.1`)

## Battle flow (script-level)
Pseudo sequence:
1. Confirm gate (badge/flag)
2. (Optional) “Start E4 run?” Yes/No
3. Battle Bruno → if lost, return to safe point
4. Heal (optional, recommended for playtesting)
5. Battle Karen → heal
6. Battle Koga → heal
7. Battle Will → heal
8. Battle Finn
9. On win:
   - set completion:
     - `SetFlag 0xA02` (`ROGUE_RUN_COMPLETED`, dec 2562)
     - `SetVar 0x401A` (`ROGUE_STORY_STAGE`) = `10`
   - then trigger the existing “end”:
     - prefer Hall of Fame flow if wired (`HallOfFameAnime` / existing Hall of Fame script)
     - otherwise show endgame screen and return control

## Where it should live
For minimal friction, put the E4 trigger in:
- the **settings room** (since it’s already intended as a playtest hub)

If you prefer a dedicated place on the world map, reserve a header for an “E4 Terminal Room”:
- candidate placeholders in your header list:
  - `0541` (`TEST2`) — has real script/event wiring (safer than NEWMAP)
  - `0542–0544` (`NEWMAP`) — placeholders, but can be repurposed once their maps exist

## Failure handling
On any E4 loss:
- call standard loss handling (`LostBattle`)
- warp to a safe hub (start town Pokécenter or start room `0012`)

## Documentation linkage
- Fill `templates/elite-four.md` with final trainer IDs + header choices.
- Once chosen, add the E4 room header(s) to `templates/critical-path-headers.csv`.


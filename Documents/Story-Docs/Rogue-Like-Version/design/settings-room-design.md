# Design — Settings room (playtest preferences)

## Purpose
The settings room is for **playtesting convenience**, not permanent gameplay balance. It should:
- be optional (defaults = intended baseline)
- not break progression
- be safe to keep when we later build the Standard version (Standard can ignore it or gate it)

## Storage model (blueprint-first)
We keep progression and settings separate:

- **Progression variable**: `0x401A` (`ROGUE_STORY_STAGE`) — progression only
- **Roguelike lifecycle flags**:
  - `2559` (`0x9FF`) `ROGUE_MODE_ACTIVE`
  - `2560` (`0xA00`) `ROGUE_INTRO_DONE`
  - `2561` (`0xA01`) `ROGUE_E4_UNLOCKED`
  - `2562` (`0xA02`) `ROGUE_RUN_COMPLETED`

### Reserve ranges for settings
To avoid collisions and keep it organized:
- **Settings flags**: start at `0xA10` (dec 2576) and increment upward
- **Settings variables**: start at `0x401B` (dec 16411) and increment upward

This gives us a predictable “block” of IDs for playtest settings.

## Recommended MVP settings (safe, low-risk)
These are “fastest to implement” because they don’t require engine changes:

| Setting | Kind | Proposed ID | Default | Meaning |
|---|---|---|---|---|
| SkipIntroText | flag | `0xA10` | OFF | Don’t show the Roguelike explanation boxes on new saves |
| StarterKitTier | var | `0x401B` | 0 | 0=normal, 1=extra items, 2=debug kit (exact items defined in docs) |
| StartingMoneyBonus | var | `0x401C` | 0 | Adds starting money (0/1000/5000/etc) |
| HealOnBlackout | flag | `0xA11` | ON | Playtest safety: always heal / avoid softlocks |
| FastTravelUnlocks | var | `0x401D` | 0 | Optional: unlock some flypoints/warps for testing (careful: can break story) |

## “Maybe later” settings (higher risk)
These typically require hg-engine/armips changes or deeper data surgery:
- EXP multiplier
- trainer level scaling
- encounter randomization
- speed-up battle animations globally

If you want any of these, list them in `templates/settings-room.md` and we’ll decide whether it’s:
- script-only feasible, or
- requires engine changes (hg-engine build)

## NPC design pattern
Keep NPC scripts uniform:
1. Short explanation message
2. Menu (Yes/No or list)
3. Set a flag/var
4. Confirmation message (“Done.”)

This makes it easy to expand without rewriting logic.

## Where it lives
Two supported placements:
- **In header `0012`** as a corner “settings booth” (fastest)
- **Separate settings room** accessible via a door/warp from `0012` (cleaner)

The exact choice should be recorded in `templates/start-bootstrap.md`.


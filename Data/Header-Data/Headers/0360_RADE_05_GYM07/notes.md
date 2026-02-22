# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `700`
- **Leader**: Chuck (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 7.x)

### Entry condition
- Should be reachable after Badge 6 / Stage 7.

### Exit condition
- Award **Badge 7** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `8`.
- Optional: set flag `0xA09` (`ROGUE_GYM7_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

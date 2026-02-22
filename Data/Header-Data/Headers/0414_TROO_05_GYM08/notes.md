# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `800`
- **Leader**: Clair (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 8.x; some rows have blank `Location` but the leader exists.)

### Entry condition
- Should be reachable after Badge 7 / Stage 8.

### Exit condition
- Award **Badge 8** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `9`.
- Set flag `0xA01` (`ROGUE_E4_UNLOCKED`).
- Optional: set flag `0xA0A` (`ROGUE_GYM8_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

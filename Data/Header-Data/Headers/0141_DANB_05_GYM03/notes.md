# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `300`
- **Leader**: Whitney (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 3.x)

### Entry condition
- Should be reachable after Badge 2 / Stage 3.

### Exit condition
- Award **Badge 3** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `4`.
- Optional: set flag `0xA05` (`ROGUE_GYM3_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `500`
- **Leader**: Pryce (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 5.x)

### Entry condition
- Should be reachable after Badge 4 / Stage 5.

### Exit condition
- Award **Badge 5** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `6`.
- Optional: set flag `0xA07` (`ROGUE_GYM5_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

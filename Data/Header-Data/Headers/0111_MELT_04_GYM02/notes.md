# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `200`
- **Leader**: Bugsy (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 2.x)

### Entry condition
- Should be reachable after Badge 1 / Stage 2.

### Exit condition
- Award **Badge 2** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `3`.
- Optional: set flag `0xA04` (`ROGUE_GYM2_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

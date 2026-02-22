# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `600`
- **Leader**: Jasmine (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 6.x)

### Entry condition
- Should be reachable after Badge 5 / Stage 6.

### Exit condition
- Award **Badge 6** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `7`.
- Optional: set flag `0xA08` (`ROGUE_GYM6_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

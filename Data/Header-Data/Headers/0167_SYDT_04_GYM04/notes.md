# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `400`
- **Leader**: Morty (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 4.x)

### Entry condition
- Should be reachable after Badge 3 / Stage 4.

### Exit condition
- Award **Badge 4** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `5`.
- Optional: set flag `0xA06` (`ROGUE_GYM4_CLEARED`).

### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

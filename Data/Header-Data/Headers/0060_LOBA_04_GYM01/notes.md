# Notes

## Roguelike (baseline)
- **RogueRole**: `Gym`
- **RogueSeq**: `100`
- **Leader**: Falkner (see `Data/Trainer-Data/Trainer-Data-Main.csv`, Gym Leader 1.x)
### Entry condition
- Accessible once the Roguelike baseline has started (starter granted).
### Exit condition
- Award **Badge 1** (prefer standard HGSS badge flow).
- Set var `0x401A` (`ROGUE_STORY_STAGE`) = `2`.
- Optional: set flag `0xA03` (`ROGUE_GYM1_CLEARED`).
### Notes
- Keep gym text minimal; reuse HGSS/CommonScripts where possible.

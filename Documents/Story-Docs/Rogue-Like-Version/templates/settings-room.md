# Template — Settings room (playtest preferences)

Goal: NPCs in the settings room let players tweak **playtest preferences** without breaking the main progression.

## Location
- **Settings room header**: `TBD`
- **Entry from start (0012)**: `TBD`

## Rules
- Settings should be **optional** (default values should produce a sane “intended” baseline run).
- Prefer using **variables** for multi-value settings and **flags** for on/off.
- Don’t reuse `ROGUE_STORY_STAGE` (`0x401A`) for settings (keep it progression-only).

## Toggles / Settings list
Fill this table. If you’re unsure about an ID, write `TBD` and we’ll reserve the next free-to-use slots.

| Setting name | Type (flag/var) | ID (hex/dec) | Default | Allowed values | What it changes | Notes |
|---|---|---|---|---|---|---|
| Skip_intro_text | flag | TBD | OFF | ON/OFF | Skips Roguelike explanation boxes on new saves | |
| Starter_kit_level | var | TBD | 0 | 0..n | Adds extra starting items based on selection | |
| Exp_multiplier | var | TBD | 0 | 0..n | (Only if supported) | Might require engine work |
| Money_bonus | var | TBD | 0 | 0..n | Starting money bonus | |
| Heal_on_blackout | flag | TBD | ON | ON/OFF | Safety for playtesting | |

## NPC interactions
For each NPC, specify:
- NPC name (display text): `TBD`
- Which settings they control: `TBD`
- Menu style: (Yes/No / multi-choice / repeated) `TBD`


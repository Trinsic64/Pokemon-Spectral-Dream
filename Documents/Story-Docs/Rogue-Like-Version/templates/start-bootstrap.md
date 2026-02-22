# Template — Start bootstrap (Header 0012)

## Spawn / start
- **Start header**: `0012` (`MAUN 02 PROT`)
- **Start X/Y + facing** (if relevant): `TBD`
- **One-time intro trigger**:
  - Trigger location: `TBD` (level script vs invisible trigger event)
  - Condition: `FLAG_ROGUE_INTRO_DONE` (0xA00 / dec 2560) is `FALSE`

## Intro message (Roguelike explanation)
Provide 1–3 short message boxes. Keep it functional and minimal.

### Message 1
Text:

```
TBD
```

### Message 2 (optional)
Text:

```
TBD
```

### Message 3 (optional)
Text:

```
TBD
```

## Starting key items (forced)
List the exact items you want the player to receive before reaching the overworld.

| Item | Qty | Why | Notes |
|---|---:|---|---|
| TBD | TBD | TBD | TBD |

## Starting consumables (forced)
| Item | Qty | Why | Notes |
|---|---:|---|---|
| Poké Ball | TBD | Basic catching | |
| Potion | TBD | Basic safety | |

## Lab flow
The player should be able to reach the lab and choose a starter “like normal”.

- **Lab header(s)**: `TBD`
- **Starter selection method**: existing selection room flow (no rewrite)
- **After starter choice**, confirm we also grant/ensure:
  - Pokédex: `Yes/No`
  - Any other core key items: `TBD`

## Settings room entry
Where/how does the player access the “settings room” from the start area?

- **Entry method**: (door / warp tile / NPC menu) `TBD`
- **Settings room header** (if separate map): `TBD`
- If settings are in the same room: list the NPC IDs / positions: `TBD`


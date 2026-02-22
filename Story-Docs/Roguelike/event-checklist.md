# Roguelike (Baseline) — Event Checklist

Use this checklist per milestone to ensure the ROM is **playable**, not “content complete”.

## For each milestone map
- [ ] Player can enter the map without softlock.
- [ ] If there is a blocker (guard/door/warp), it has:
  - [ ] an entry condition (flag/variable/badge)
  - [ ] clear feedback text (“You can’t go this way yet.” is fine)
- [ ] The required battle(s) start and resolve.
- [ ] On win, we set the next state (badge/flag/var) and **unlock the next area**.
- [ ] On loss, flow returns to a safe state (Pokécenter / last warp).

## Global baseline requirements
- [ ] Starter is granted and recorded as the player’s starter choice.
- [ ] Pokédex is granted if required for downstream scripts.
- [ ] A minimal item kit is granted (balls + potions).
- [ ] Gym badge gates are consistent (prefer badge checks over custom flags where possible).
- [ ] Endgame completion can be achieved (E4 + final completion flag).


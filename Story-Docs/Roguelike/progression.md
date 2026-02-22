# Roguelike (Baseline) — Progression

This file is the **human-readable critical path**. It should stay short and functional.

## Critical path (intended order)
1. **Start / Tutorial-lite**: starter + Pokédex + item kit → reach first route
2. **Gym 1**: Lobart Gym 1 (Normal) — Falkner
3. **Gym 2**: Melton Gym 2 (Fighting) — Bugsy
4. **Gym 3**: Danberra Gym 3 (Grass) — Whitney
5. **Gym 4**: Sydtree Gym 4 (Water) — Morty
6. **Gym 5**: Bairns Gym 5 (Fire) — Pryce
7. **Gym 6**: Dalice Gym 6 (Electric) — Jasmine
8. **Gym 7**: Radelaide Gym 7 (Flying) — Chuck
9. **Gym 8**: Troome Gym 8 — Clair (location strings in trainer sheet are currently inconsistent; header index uses `TROO 05 GYM08`.)
10. **Elite Four**: Bruno → Karen → Koga → Will → (Champion TBD)

## Minimal story beats (only if required for playability)
- Starter / basic onboarding
- Rival / alliance encounters only when they **block progression**
- Badge gates and a clear endgame trigger

## Implementation mapping
- Machine-readable tracking lives in `critical-path.csv`.
- Per-map implementation notes live in `Data/Header-Data/Headers/*/notes.md`.


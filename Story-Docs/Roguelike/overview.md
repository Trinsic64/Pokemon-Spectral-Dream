# Roguelike (Baseline) — Overview

This “Roguelike” version is the **minimum playable baseline** of Pokémon Spectral Dream.

## What it is
- **Fixed progression** (no procedural/randomized content).
- **Bare-minimum story**: only the scenes/events needed to keep the game playable and to gate progression.
- **Core mechanics focus**: exploration, trainers, gyms, badges, and endgame completion.

## What it is not
- Not a separate fork that requires starting over later.
- Not a randomized roguelite run system.
- Not a full narrative/cutscene pass.

## Design rules (to stay Standard-ready)
- **Use HGSS scripts / CommonScripts / text when possible**.
- New story logic should be **small** and expressed as:
  - a small set of **flags + one stage variable**
  - repeatable gating patterns (guards, warps, “unlock next route”)
- Any new scripts/text must be **safe to extend** for the Standard version (add scenes/branches without rewriting core gates).

## Sources of truth (repo)
- **Map header index**: `Data/Header-Data/Header-Data-Main.csv`
- **Per-map notes**: `Data/Header-Data/Headers/<####_InternalName>/notes.md`
- **Trainer roster**: `Data/Trainer-Data/Trainer-Data-Main.csv`
- **Flags/vars registry**: `Data/Flag-Data/Flag-Data-Main.csv`, `Data/Variable-Data/Variable-Data-Main.csv`

## Playability definition (MVP)
- New game starts and you can move.
- Starter + Pokédex + a small item kit are granted.
- Progression gates work through Gym 1 → Gym 8 → Elite Four (minimal cutscenes OK).


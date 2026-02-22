# Design — Start bootstrap wiring (Header 0012)

Start header: `0012` (`MAUN 02 PROT`)

Header wiring (from `Data/Header-Data/Header-Data-Main.csv` / per-header README):
- Script File: `0846` (PC/Mailbox interaction only)
- Level Script File: `0619` (**currently empty** script export)
- Event File: `0061`
- Text Archive: `0546` (currently contains PC/Mailbox/Wii lines)

## Goal
On a **new save**, the first time the player gains control on header `0012`:
1) show a short **Roguelike-mode intro** explaining the current state of the game
2) grant **starting key items** (exact list defined in `templates/start-bootstrap.md`)
3) ensure the player can proceed to the **lab “like normal”** to choose a starter
4) expose a **settings room** (NPCs / separate room) for playtest preferences

## Where the bootstrap should live
Because Script File `0846` is only PC interaction, the bootstrap should be driven by one of:

### Option A (recommended): Level Script `0619`
Put a one-time “OnLoad” script in the level script file `0619` that runs when the map loads.

Pseudo-flow:
- On map load:
  - `CheckFlag 2560` (`ROGUE_INTRO_DONE`)
  - If already set: `End`
  - Else:
    - `LockAll`
    - show 1–3 messages (intro text)
    - grant items/key items
    - `SetFlag 2559` (`ROGUE_MODE_ACTIVE`)
    - `SetFlag 2560` (`ROGUE_INTRO_DONE`)
    - `SetVar 0x401A 1` (`ROGUE_STORY_STAGE = 1`)
    - optionally warp/step the player into the intended “first route” tile if needed
    - `ReleaseAll`

Why this is best:
- No dependence on touching PCs/NPCs.
- Clean one-time logic with a single guard flag.
- Extensible later (Standard can branch on `ROGUE_MODE_ACTIVE`).

### Option B: Invisible trigger in Event File `0061`
Add an invisible event (trigger region) near the spawn point:
- On step-in: run the bootstrap script (same guard flag).

Why this is useful:
- If level scripts are already used for other things, triggers keep concerns separate.
- You can position the trigger “before overworld exit” to ensure players see the intro.

## Intro text placement
We have two viable approaches:
- **Reuse Text Archive `0546`**: add new message entries for Roguelike intro and settings room hints.
  - Pros: fewer moving parts (header already points to 0546).
  - Cons: 0546 currently contains PC/Mailbox/Wii strings; mixed concerns.
- **Repoint `0012` to a dedicated text archive** for “Roguelike intro / settings”.
  - Pros: cleaner separation for later Standard version.
  - Cons: requires header changes and text archive management.

For the preparing stage, you should fill the desired intro text in `templates/start-bootstrap.md` first.

## Settings room implementation
Two implementations; both are compatible with “lab like normal”.

### A) Settings NPCs in `0012`
Add 2–5 NPCs in `0012` (Event File `0061`):
- Each NPC opens a small menu and sets flags/vars for playtest options (see `templates/settings-room.md`).
- Gate their availability behind `ROGUE_INTRO_DONE` (optional).

### B) Separate settings room map
Create a dedicated interior header (door in `0012`):
- Minimal map, just NPCs + exit.
- Keeps the start room clean and avoids crowding.

## Lab “like normal”
We do **not** rewrite starter selection; we only ensure:
- the player can physically reach the lab headers
- the intro/key items do not softlock any existing lab scripts
- after starter selection, we can (optionally) ensure key items are granted if some are normally obtained later

The exact lab header IDs should be filled in `templates/critical-path-headers.csv` (row `Lab (starter selection)`).


# AI Event Editing — Opening Prompt Template

Copy the prompt below into a new AI conversation. Fill in the `[BRACKETED]` sections
with your specific task. The AI needs all of this context to operate the tools correctly.

---

## The Prompt

```
You are working on a Pokémon ROM hack called "Pokémon Spectral Dream" built on
HeartGold using the hg-engine toolchain and DSPRE (DS Pokémon ROM Editor).

Read the following instructions file FIRST before doing anything else:
@DSPRE-Contents-Analysis/AI-INSTRUCTIONS.md

This file explains the full toolchain, data formats, coordinate system, constraints,
and step-by-step workflows for editing event files.

Key rules:
- NEVER edit files in `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` or `events/raw/`
- ALL edits go through the CSV files in `DSPRE-Contents-Analysis/events/`
- ALWAYS create a backup before editing: `python tools/backup_events.py create --name <name>`
- ALWAYS serialize after editing: `python tools/serialize_events.py --event NNNN --validate`
- ALWAYS use --dry-run first with batch_edit.py before applying changes
- Run all tools from the `DSPRE-Contents-Analysis/` directory

Reference files for lookups:
- @Data/Header-Data/Header-Data-Main.csv (map names → event files, script files)
- @Data/Flag-Data/Flag-Data-Main.csv (flag allocation)
- @DSPRE-Contents-Analysis/events/overworlds.csv (existing NPC/item entities)
- @DSPRE-Contents-Analysis/constants/ (species, items, moves, abilities CSVs)
- @Tools/hg-engine/src/field/overworld_table.c (sprite tag → graphic mapping)

## My Task

[DESCRIBE YOUR TASK HERE — Examples below]

### Example tasks you can paste and modify:

#### Add Item Balls
"Add 5 item balls to these maps with these items:
- Route 5 (Event File 14): Rare Candy, TM01
- Lobart Cavern (Event File 117): Max Revive, Full Restore, Nugget
Use map_lookup.py --suggest-placement to find positions.
Allocate flags for each item. Generate item-pickup scripts."

#### Change NPC Sprites
"Change all Ace Trainer overworld sprites on Route 9 (Event File 43) to use
more varied trainer classes. Check reclassify_trainer.py list-classes for options.
Keep the trainer battles and scripts the same, just change the visual sprites."

#### Add HM Obstacles
"Add a Rock Smash obstacle blocking access to an item ball in Well Cave F1
(Event File 111). Place the rock on a walkable tile near the cave entrance,
and put a Rare Candy item ball behind it. Allocate flags for both the rock
and the item. Generate the Rock Smash and item pickup scripts."

#### Bulk Trainer Reclassification
"Reclassify these trainers to new classes for more visual variety:
- Trainer 50: Change from Ace Trainer to Hiker
- Trainer 51: Change from Ace Trainer to Fisherman
- Trainer 52: Change from Ace Trainer to Bug Catcher
Use reclassify_trainer.py with --dry-run first, then apply.
After reclassifying, serialize all affected event files."

#### Survey and Report
"List all event files that have more than 10 overworld entities.
For each one, show the map name, NPC count, and how many unique
overlay_entry (sprite) values are used. Flag any that use more than
12 unique sprites as potential VRAM overflow risks."
```

---

## How to Fill In Your Task

1. **Be specific about map targets**: Use map names AND event file numbers.
   Find event file numbers in `Data/Header-Data/Header-Data-Main.csv` under "Event File".

2. **Specify items by name**: The AI can look them up in `constants/items.csv`.
   Examples: "Rare Candy", "TM01", "Max Revive", "Full Restore".

3. **Specify sprites by name or tag**: If you know the tag number from
   `overworld_table.c`, use it. Otherwise describe the NPC
   (e.g. "Hiker sprite", "Fisherman sprite") and the AI will look it up.

4. **Say whether placement matters**: If you want the AI to use
   `--suggest-placement` to auto-pick positions, say so. If you'll manually
   reposition later, say "place in the center of the map, I'll adjust manually."

5. **Say whether scripts are needed**: If the AI should also generate
   DSPRE script text (for item pickups, NPC dialogue, trainer battles),
   mention it. If scripts already exist, say "scripts are already written,
   just add the event entities."

---

## What the AI Will Do

When given a task, a well-instructed AI will:

1. Read `AI-INSTRUCTIONS.md` for the full tool reference
2. Create a backup with a descriptive name
3. Look up relevant map data (header CSV, event files, collision grids)
4. Allocate flags if needed
5. Find safe placement positions using map collision data
6. Create a JSON manifest for `batch_edit.py`
7. Dry-run the manifest to preview changes
8. Apply the changes
9. Serialize affected event files with `--validate`
10. Generate any needed script text
11. Report what was done and what files were created in `events/edited/`

The edited binary files in `events/edited/` need to be manually copied into
a duplicate ROM's `unpacked/eventFiles/` directory and repacked using DSPRE.

---

## Troubleshooting Tips for the AI

- **"No header found for event file"**: The event file number might not match.
  Check `Header-Data-Main.csv` for the correct event file number.
- **"duplicate ow_id"**: Two overworlds in the same event file share an ID.
  Change one of them to a unique value.
- **Serialized file size differs from original**: This is expected if you added
  or removed entities. The serializer handles this correctly.
- **PowerShell f-string issues**: Avoid using escaped quotes in f-strings
  when running Python one-liners in PowerShell. Write small helper scripts instead.

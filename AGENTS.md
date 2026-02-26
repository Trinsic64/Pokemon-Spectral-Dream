# Agents

## Cursor Cloud specific instructions

### Overview

Pokemon Spectral Dream is a Nintendo DS ROM-hack data/tooling repo. It contains **no web services, no databases, and no Docker**. The codebase is Python scripts + CSV/JSON game data.

### Services

| Service | Type | Notes |
|---|---|---|
| CLI tools (Encounter/Trainer/Header/Item) | Python stdlib-only scripts | Run from repo root; no pip install needed |
| AI Event Editor (`Tools/AI-Event-Editor/`) | Python GUI app (CustomTkinter) | Requires `pip install -r Tools/AI-Event-Editor/requirements.txt` + `python3-tk` system package; needs a display for the GUI |
| DSPRE-Contents-Analysis tools | Python stdlib-only scripts | Operate on extracted ROM contents (not in repo) |

### Running CLI tools

All CLI tools are run from the repo root. See `README.md` for examples:
```
python3 Tools/Update-Encounter-Data-Script/update_encounter_data.py --help
python3 Tools/Update-Trainer-Data-Script/update_trainer_data.py --help
python3 Tools/Update-Header-Data-Script/update_header_data.py --help
python3 Tools/Update-Item-Data-Script/update_item_data.py --help
```

### Linting

No formal linting config exists in the repo. Use `flake8` for basic checks:
```
flake8 --max-line-length=120 --select=E9,F63,F7,F82 Tools/ DSPRE-Contents-Analysis/tools/
```

### Testing

No automated test suite exists. Verification is done by running the tools with `--dry-run` flags and checking output. The encounter and trainer tools are self-contained and can be tested without a ROM. The header and item tools require local ROM extraction (not in repo).

### Non-obvious caveats

- The Header Data tool and Item Data tool require a local DSPRE ROM extraction at `ROM/Pokemon-Spectral-Dream_DSPRE_contents/` which is gitignored and not available in CI/cloud environments.
- The AI Event Editor is primarily a **Windows** desktop app (has `ctypes.windll` DPI calls). It runs on Linux with `python3-tk` installed but the DPI code silently falls back.
- Most tools intentionally use **only the Python standard library** to avoid dependency complexity. The AI Event Editor is the only component with pip dependencies.
- There are 2 pre-existing `F821` flake8 errors (undefined name `e`) in `Tools/AI-Event-Editor/src/panels/execute_panel.py:165` and `npc_panel.py:213`. These are in the existing codebase.

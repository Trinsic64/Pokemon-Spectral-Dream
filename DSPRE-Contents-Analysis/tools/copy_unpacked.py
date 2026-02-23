#!/usr/bin/env python3
"""
copy_unpacked.py

Copies the DSPRE_contents/unpacked/ directory (binary files extracted by DSPRE
from ROM NARCs) into DSPRE-Contents-Analysis/unpacked/, preserving subdirectory
structure.

Subdirectories found in unpacked/:
  dynamicHeaders/   - binary map header files
  personalPokeData/ - Pokemon base stat binary files
  safariZone/       - safari zone encounter binary files
  moveData/         - move data binary files
  textArchives/     - text archive binary files

Standard-library only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_UNPACKED = REPO_ROOT / "ROM" / "Pokemon-Spectral-Dream_DSPRE_contents" / "unpacked"
DEST_UNPACKED = Path(__file__).resolve().parents[1] / "unpacked"


def copy_subdir(src: Path, dst: Path) -> int:
    """Copy all files from src into dst. Returns count of files copied."""
    if not src.exists():
        print(f"  [SKIP] Source does not exist: {src}")
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dst / item.name)
            count += 1
    return count


def main() -> None:
    print(f"Source: {SOURCE_UNPACKED}")
    print(f"Dest  : {DEST_UNPACKED}")
    print()

    if not SOURCE_UNPACKED.exists():
        print("[ERROR] Source unpacked/ directory does not exist.")
        return

    total = 0
    for subdir in sorted(SOURCE_UNPACKED.iterdir()):
        if subdir.is_dir():
            n = copy_subdir(subdir, DEST_UNPACKED / subdir.name)
            print(f"  Copied {n:4d} files  unpacked/{subdir.name}/")
            total += n

    print()
    print(f"Done. {total} files copied.")


if __name__ == "__main__":
    main()

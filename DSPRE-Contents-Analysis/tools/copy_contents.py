#!/usr/bin/env python3
"""
copy_contents.py

Copies files from ROM/Pokemon-Spectral-Dream_DSPRE_contents into the
DSPRE-Contents-Analysis directory without modifying the source files.

Folder mapping:
  expanded/scripts/      -> ../scripts/
  expanded/textArchives/ -> ../textArchives/
  data/data/             -> ../data/
  data/pbr/              -> ../data/pbr/
  overlay/               -> ../data/overlay/

Standard-library only.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = REPO_ROOT / "ROM" / "Pokemon-Spectral-Dream_DSPRE_contents"
DEST_ROOT = Path(__file__).resolve().parents[1]

COPY_MAPPINGS: list[tuple[Path, Path]] = [
    (SOURCE_ROOT / "expanded" / "scripts", DEST_ROOT / "scripts"),
    (SOURCE_ROOT / "expanded" / "textArchives", DEST_ROOT / "textArchives"),
    (SOURCE_ROOT / "data" / "data", DEST_ROOT / "data"),
    (SOURCE_ROOT / "data" / "pbr", DEST_ROOT / "data" / "pbr"),
    (SOURCE_ROOT / "overlay", DEST_ROOT / "data" / "overlay"),
]


def copy_dir(src: Path, dst: Path) -> int:
    """Copy all files from src into dst, returning the count of files copied."""
    if not src.exists():
        print(f"  [SKIP] Source does not exist: {src}")
        return 0
    dst.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_file in src.iterdir():
        if src_file.is_file():
            dst_file = dst / src_file.name
            shutil.copy2(src_file, dst_file)
            count += 1
    return count


def main() -> None:
    print(f"Source root : {SOURCE_ROOT}")
    print(f"Dest root   : {DEST_ROOT}")
    print()

    total = 0
    for src, dst in COPY_MAPPINGS:
        n = copy_dir(src, dst)
        print(f"  Copied {n:4d} files  {src.relative_to(SOURCE_ROOT)}  ->  {dst.relative_to(DEST_ROOT)}")
        total += n

    print()
    print(f"Done. {total} files copied total.")


if __name__ == "__main__":
    main()

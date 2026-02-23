#!/usr/bin/env python3
"""
unpack_narc.py

Generic NARC (Nitro ARChive) unpacker for Nintendo DS ROM files.
Implements the BTAF/BTNF/GMIF format documented in DSPRE's Narc.cs.

Usage:
  python unpack_narc.py <narc_file> <output_dir>
  python unpack_narc.py --help

NARC binary format (little-endian):
  [16-byte header]
    4 bytes  "NARC" magic (0x4352414E)
    4 bytes  BOM + version (0xFFFE0100)
    4 bytes  total file size
    2 bytes  header section size (always 0x10)
    2 bytes  number of sections (always 3)

  [BTAF section - File Allocation Table]
    4 bytes  "BTAF" magic (0x46415442)
    4 bytes  section size
    4 bytes  number of files
    For each file:
      4 bytes  start offset (relative to GMIF data start, 4-byte aligned)
      4 bytes  end offset

  [BTNF section - File Name Table]
    4 bytes  "BTNF" magic (0x464E5442)
    4 bytes  section size (0x10 for NARCs without names)
    8 bytes  filler

  [GMIF section - File Image]
    4 bytes  "GMIF" magic (0x46494D47)
    4 bytes  section size
    [file data, padded to 4-byte boundaries with 0xFF]

Standard-library only.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

NARC_MAGIC = 0x4352414E   # "NARC"
BTAF_MAGIC = 0x46415442   # "BTAF"
BTNF_MAGIC = 0x464E5442   # "BTNF"
GMIF_MAGIC = 0x46494D47   # "GMIF"


class NarcUnpackError(Exception):
    pass


def unpack_narc(narc_path: Path, output_dir: Path, zero_pad: int = 4) -> list[Path]:
    """
    Unpack all files from a NARC archive into output_dir.

    Returns a list of the output file paths (zero-padded numeric names).
    Raises NarcUnpackError on format errors.
    """
    data = narc_path.read_bytes()
    pos = 0

    def read_u32(offset: int) -> int:
        return struct.unpack_from("<I", data, offset)[0]

    def read_u16(offset: int) -> int:
        return struct.unpack_from("<H", data, offset)[0]

    # ---- NARC header ----
    if read_u32(0) != NARC_MAGIC:
        raise NarcUnpackError(f"Not a NARC file: {narc_path}")
    # skip BOM+version (4), total_size (4), header_size (2), num_sections (2)
    pos = 0x10

    # ---- BTAF section ----
    if read_u32(pos) != BTAF_MAGIC:
        raise NarcUnpackError(f"Expected BTAF at offset {pos:#x}")
    btaf_size  = read_u32(pos + 4)
    num_files  = read_u32(pos + 8)
    fat_start  = pos + 12

    fat: list[tuple[int, int]] = []
    for i in range(num_files):
        start = read_u32(fat_start + i * 8)
        end   = read_u32(fat_start + i * 8 + 4)
        fat.append((start, end))

    pos += btaf_size

    # ---- BTNF section ----
    if read_u32(pos) != BTNF_MAGIC:
        raise NarcUnpackError(f"Expected BTNF at offset {pos:#x}")
    btnf_size = read_u32(pos + 4)
    pos += btnf_size

    # ---- GMIF section ----
    if read_u32(pos) != GMIF_MAGIC:
        raise NarcUnpackError(f"Expected GMIF at offset {pos:#x}")
    gmif_data_start = pos + 8  # skip "GMIF" magic + section_size

    # ---- Extract files ----
    output_dir.mkdir(parents=True, exist_ok=True)
    out_paths: list[Path] = []

    for i, (start, end) in enumerate(fat):
        file_data = data[gmif_data_start + start: gmif_data_start + end]
        out_name = str(i).zfill(zero_pad)
        out_path = output_dir / out_name
        out_path.write_bytes(file_data)
        out_paths.append(out_path)

    return out_paths


def main() -> None:
    if len(sys.argv) < 3 or "--help" in sys.argv:
        print(__doc__)
        print("Usage: python unpack_narc.py <narc_file> <output_dir>")
        sys.exit(0)

    narc_path  = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not narc_path.exists():
        print(f"[ERROR] NARC file not found: {narc_path}")
        sys.exit(1)

    try:
        paths = unpack_narc(narc_path, output_dir)
        print(f"Extracted {len(paths)} files from {narc_path.name} -> {output_dir}")
    except NarcUnpackError as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

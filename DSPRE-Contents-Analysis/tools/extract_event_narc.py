#!/usr/bin/env python3
"""
extract_event_narc.py

Extracts the event binary files from the ROM into events/raw/.

Primary source: unpacked/eventFiles/ (already extracted by DSPRE when the
ROM project was last opened). This is the preferred path because DSPRE has
already done the NDS filesystem + NARC unpacking work.

Fallback: If the .nds file is present and unpacked/eventFiles/ is absent,
this tool parses the NDS NITRO filesystem (FAT + FNT) to locate the event
NARC at ROM path a/0/3/2, extracts it, then calls unpack_narc.py to
unpack it into events/raw/.

Standard-library only.
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]

UNPACKED_EVENTS = ANALYSIS_ROOT / "unpacked" / "eventFiles"
EVENTS_RAW = ANALYSIS_ROOT / "events" / "raw"
EVENTS_NARC = ANALYSIS_ROOT / "events" / "zone_event_hg.narc"
NDS_PATH = REPO_ROOT / "ROM" / "Pokemon-Spectral-Dream.nds"

# Path inside NDS NITRO filesystem to the event NARC
NDS_EVENT_PATH = "a/0/3/2"


# ---------------------------------------------------------------------------
# NDS NITRO filesystem reader
# ---------------------------------------------------------------------------

def _read_uint32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def _read_uint16(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def extract_file_from_nds(nds_path: Path, rom_path: str) -> bytes | None:
    """
    Extract a file from an NDS ROM by its filesystem path (e.g. 'a/0/3/2').
    Returns the file bytes, or None if not found.
    """
    try:
        data = nds_path.read_bytes()
    except FileNotFoundError:
        return None

    fnt_offset = _read_uint32(data, 0x40)
    fat_offset = _read_uint32(data, 0x48)
    fat_size   = _read_uint32(data, 0x4C)
    fat_count  = fat_size // 8

    # Build FAT list: [(start, end), ...]
    fat = []
    for i in range(fat_count):
        start = _read_uint32(data, fat_offset + i * 8)
        end   = _read_uint32(data, fat_offset + i * 8 + 4)
        fat.append((start, end))

    # Navigate FNT directory tree
    parts = [p for p in rom_path.strip("/").split("/") if p]
    dir_id = 0xF000  # root directory ID

    for part_idx, part in enumerate(parts):
        is_last = (part_idx == len(parts) - 1)

        # Each dir entry in FNT root table is 8 bytes:
        # uint32 subtable_offset, uint16 first_file_id, uint16 parent_dir_count
        dir_entry_offset = fnt_offset + (dir_id & 0x0FFF) * 8
        subtable_offset = _read_uint32(data, dir_entry_offset)
        first_file_id   = _read_uint16(data, dir_entry_offset + 4)

        # Walk subtable
        pos = fnt_offset + subtable_offset
        current_file_id = first_file_id
        found_id = None
        found_is_dir = False

        while True:
            type_len = data[pos]
            if type_len == 0:
                break  # end of directory

            name_len = type_len & 0x7F
            is_subdir = bool(type_len & 0x80)
            pos += 1
            name = data[pos: pos + name_len].decode("ascii", errors="replace")
            pos += name_len

            if is_subdir:
                subdir_id = _read_uint16(data, pos)
                pos += 2
                if name == part:
                    found_id = subdir_id
                    found_is_dir = True
                    break
            else:
                if name == part and is_last:
                    found_id = current_file_id
                    found_is_dir = False
                    break
                current_file_id += 1

        if found_id is None:
            return None

        if is_last and not found_is_dir:
            start, end = fat[found_id]
            return data[start:end]

        dir_id = found_id

    return None


def copy_from_unpacked() -> int:
    """Copy binary event files from unpacked/eventFiles/ to events/raw/."""
    EVENTS_RAW.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_file in sorted(UNPACKED_EVENTS.iterdir()):
        if src_file.is_file():
            shutil.copy2(src_file, EVENTS_RAW / src_file.name)
            count += 1
    return count


def main() -> None:
    EVENTS_RAW.mkdir(parents=True, exist_ok=True)

    # Preferred path: already-unpacked event files
    if UNPACKED_EVENTS.exists() and any(UNPACKED_EVENTS.iterdir()):
        n = copy_from_unpacked()
        print(f"Copied {n} binary event files from unpacked/eventFiles/ -> events/raw/")
        return

    # Fallback: extract NARC from .nds, then unpack it
    print("unpacked/eventFiles/ not found. Trying NDS extraction...")
    if not NDS_PATH.exists():
        print(f"[ERROR] ROM not found at {NDS_PATH}")
        return

    print(f"Reading {NDS_PATH.name}  ({NDS_PATH.stat().st_size:,} bytes)...")
    narc_data = extract_file_from_nds(NDS_PATH, NDS_EVENT_PATH)
    if narc_data is None:
        print(f"[ERROR] Could not find '{NDS_EVENT_PATH}' in NDS filesystem.")
        return

    EVENTS_NARC.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_NARC.write_bytes(narc_data)
    print(f"Saved NARC ({len(narc_data):,} bytes) -> events/zone_event_hg.narc")
    print("Run unpack_narc.py next to extract individual event files.")


if __name__ == "__main__":
    main()

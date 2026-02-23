#!/usr/bin/env python3
"""
analyze_text.py

Indexes all text archive .txt files in ../textArchives/ and generates:
  analysis/text-archive-summary.csv  - per-file: entry count, preview, map linkage

Cross-references Header-Data-Main.csv to identify which maps use each archive.

Standard-library only.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYSIS_ROOT = Path(__file__).resolve().parents[1]
TEXT_DIR = ANALYSIS_ROOT / "textArchives"
ANALYSIS_DIR = ANALYSIS_ROOT / "analysis"
HEADER_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"

# Control codes that appear in HGSS text
CONTROL_CODE_RE = re.compile(r"\{[^}]+\}")
ESCAPE_SEQ_RE = re.compile(r"\\[nrte]")


def clean_text(raw: str) -> str:
    """Strip control codes and escape sequences for display."""
    s = CONTROL_CODE_RE.sub("", raw)
    s = ESCAPE_SEQ_RE.sub(" ", s)
    return s.strip()


def parse_text_archive(path: Path) -> dict:
    """Parse a DSPRE text archive file. Returns metadata about its contents."""
    info: dict = {
        "file": path.stem,
        "entry_count": 0,
        "line_count": 0,
        "first_entry": "",
        "longest_entry_len": 0,
        "has_control_codes": False,
        "key": "",
    }

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return info

    info["line_count"] = len(lines)

    # Extract key comment if present
    for line in lines[:3]:
        if line.startswith("# Key:"):
            info["key"] = line.split(":", 1)[1].strip()
            break

    # Count non-empty, non-comment lines as entries
    entries: list[str] = []
    for line in lines:
        if not line or line.startswith("#"):
            continue
        entries.append(line)

    info["entry_count"] = len(entries)

    if entries:
        first = clean_text(entries[0])
        info["first_entry"] = first[:120]  # truncate for CSV

    if entries:
        info["longest_entry_len"] = max(len(e) for e in entries)

    for entry in entries:
        if CONTROL_CODE_RE.search(entry):
            info["has_control_codes"] = True
            break

    return info


def load_header_text_map(header_csv: Path) -> dict[str, list[str]]:
    """Return {text_archive_number_str: [map_name, ...]}.

    Keys are zero-padded to 4 digits to match filenames like '0738'.
    """
    mapping: dict[str, list[str]] = defaultdict(list)
    if not header_csv.exists():
        return mapping
    with header_csv.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            archive_ref = row.get("Text Archive", "").strip()
            internal_name = row.get("Internal Name", "").strip()
            if archive_ref and internal_name:
                try:
                    key = str(int(archive_ref)).zfill(4)
                except ValueError:
                    key = archive_ref
                mapping[key].append(internal_name)
    return mapping


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    archive_to_maps = load_header_text_map(HEADER_CSV)

    txt_files = sorted(TEXT_DIR.glob("*.txt"))
    print(f"Indexing {len(txt_files)} text archive files...")

    rows: list[dict] = []
    for tf in txt_files:
        info = parse_text_archive(tf)
        file_num = tf.stem
        maps_using = "; ".join(archive_to_maps.get(file_num, []))

        rows.append({
            "archive_file": file_num,
            "maps_using_archive": maps_using,
            "key": info["key"],
            "entry_count": info["entry_count"],
            "longest_entry_len": info["longest_entry_len"],
            "has_control_codes": "yes" if info["has_control_codes"] else "no",
            "first_entry_preview": info["first_entry"],
        })

    out = ANALYSIS_DIR / "text-archive-summary.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=[
            "archive_file", "maps_using_archive", "key",
            "entry_count", "longest_entry_len", "has_control_codes",
            "first_entry_preview",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"  -> analysis/text-archive-summary.csv  ({len(rows)} rows)")

    total_entries = sum(r["entry_count"] for r in rows)
    mapped_count = sum(1 for r in rows if r["maps_using_archive"])
    print(f"     Total text entries across all archives: {total_entries:,}")
    print(f"     Archives linked to a known map: {mapped_count} / {len(rows)}")
    print("\nDone.")


if __name__ == "__main__":
    main()

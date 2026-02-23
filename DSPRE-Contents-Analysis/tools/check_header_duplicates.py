#!/usr/bin/env python3
"""
check_header_duplicates.py

Analyzes Header-Data-Main.csv for duplicate values across all columns.
Outputs a structured report CSV to Report-Docs with LikelyValid flags:
- TRUE: shared by design (Script File, Event File, Matrix, etc.)
- FALSE: should usually be unique (Internal Name)
- REVIEW: context-dependent (MapSec, Wild File, etc.)

Usage:
    python tools/check_header_duplicates.py                    # run analysis, write report
    python tools/check_header_duplicates.py --csv path/to.csv   # custom input
    python tools/check_header_duplicates.py --output path.csv  # custom output
    python tools/check_header_duplicates.py --no-valid         # exclude LikelyValid=TRUE (suspicious only)

Standard-library only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HEADER_CSV = REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"
REPORT_DIR = REPO_ROOT / "Report-Docs"
DEFAULT_REPORT = REPORT_DIR / "header_duplicates_report.csv"

# Columns where duplicates are expected (shared resources across connected areas)
LIKELY_VALID_COLUMNS = {
    "Script File",
    "Level Script File",
    "Event File",
    "Text Archive",
    "Matrix",
    "Area Data",
    "Texture File",
    "Building File",
    "AreaIcon",
    "Music Day",
    "Music Night",
    "Weather",
    "Camera Angle",
    "Move Model Bank",
    "BattleBackground",
    "MomCallIntroParam",
    "Area_Unknown06",
    "Area_Unknown08",
}

# Columns that should usually be unique
LIKELY_INVALID_COLUMNS = {
    "Internal Name",
}

# Placeholder Internal Names that are allowed to duplicate
INTERNAL_NAME_PLACEHOLDERS = {"-", "NEWMAP"}


def load_header_data(path: Path) -> tuple[list[dict], list[str]]:
    """Load CSV and return rows plus fieldnames."""
    with path.open(encoding="utf-8", errors="replace") as fh:
        reader = csv.DictReader(fh)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return rows, fieldnames


def classify_likely_valid(column: str, value: str) -> str:
    """Return TRUE, FALSE, or REVIEW for a duplicate."""
    if column in LIKELY_VALID_COLUMNS:
        return "TRUE"
    if column in LIKELY_INVALID_COLUMNS:
        if column == "Internal Name" and value.strip() in INTERNAL_NAME_PLACEHOLDERS:
            return "REVIEW"  # Placeholders can duplicate
        return "FALSE"
    return "REVIEW"


def find_duplicates(rows: list[dict], fieldnames: list[str]) -> list[dict]:
    """Find all duplicate values per column. Returns list of report rows."""
    header_col = "HEADER #"
    skip_columns = {header_col}

    report_rows: list[dict] = []

    for col in fieldnames:
        if col in skip_columns:
            continue

        # Group rows by normalized value
        value_to_headers: dict[str, list[str]] = defaultdict(list)
        for row in rows:
            raw = row.get(col, "")
            val = str(raw).strip() if raw is not None else ""
            h = row.get(header_col, "")
            header_str = str(h).strip() if h is not None else ""
            value_to_headers[val].append(header_str)

        # Only report values that appear in more than one row
        for val, headers in value_to_headers.items():
            if len(headers) < 2:
                continue
            likely_valid = classify_likely_valid(col, val)

            def _header_sort_key(h: str):
                if not h:
                    return (0, 0.0)
                try:
                    return (0, float(h))
                except ValueError:
                    return (1, h)

            report_rows.append({
                "Column": col,
                "Value": val,
                "HeaderNumbers": ",".join(sorted(headers, key=_header_sort_key)),
                "Count": len(headers),
                "LikelyValid": likely_valid,
            })

    return report_rows


def write_report(
    report_rows: list[dict],
    output_path: Path,
    *,
    exclude_valid: bool = False,
) -> int:
    """Write report CSV and optional summary. Returns count of rows written."""
    if exclude_valid:
        report_rows = [r for r in report_rows if r["LikelyValid"] != "TRUE"]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["Column", "Value", "HeaderNumbers", "Count", "LikelyValid"]
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report_rows)

    # Write summary
    summary_path = output_path.with_suffix(".summary.txt")
    by_valid = defaultdict(int)
    by_column = defaultdict(int)
    for r in report_rows:
        by_valid[r["LikelyValid"]] += 1
        by_column[r["Column"]] += 1

    with summary_path.open("w", encoding="utf-8") as fh:
        fh.write("Header Data Duplicate Report Summary\n")
        fh.write("=" * 40 + "\n\n")
        fh.write(f"Total duplicate groups: {len(report_rows)}\n\n")
        fh.write("By LikelyValid:\n")
        for k in ("TRUE", "FALSE", "REVIEW"):
            fh.write(f"  {k}: {by_valid[k]}\n")
        fh.write("\nTop duplicated columns (by number of duplicate values):\n")
        for col, cnt in sorted(by_column.items(), key=lambda x: -x[1])[:15]:
            fh.write(f"  {col}: {cnt}\n")

    return len(report_rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Header-Data-Main.csv for duplicate values and generate report."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=HEADER_CSV,
        help=f"Path to header CSV (default: {HEADER_CSV})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=DEFAULT_REPORT,
        help=f"Output report path (default: {DEFAULT_REPORT})",
    )
    parser.add_argument(
        "--no-valid",
        action="store_true",
        help="Exclude LikelyValid=TRUE from report (suspicious only)",
    )
    args = parser.parse_args()

    if not args.csv.exists():
        print(f"Error: CSV not found: {args.csv}", file=sys.stderr)
        return 1

    rows, fieldnames = load_header_data(args.csv)
    if not rows:
        print("No rows in CSV.", file=sys.stderr)
        return 1

    report_rows = find_duplicates(rows, fieldnames)
    written = write_report(report_rows, args.output, exclude_valid=args.no_valid)

    print(f"Report written to {args.output}")
    print(f"Summary: {args.output.with_suffix('.summary.txt')}")
    print(f"Duplicate groups in report: {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Header Data Updater (Repo Tool)

This is the repo-local entrypoint for updating:
  - Data/Header-Data/Header-Data-Main.csv

From the DSPRE extracted contents under:
  - ROM/Pokemon-Spectral-Dream_DSPRE_contents

It also maintains per-header notes folders under:
  - Data/Header-Data/Headers/####_InternalName/

Standard-library only (easy for new developers).
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import struct
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


# --------------------------------------------------------------------------------------
# Defaults (auto-derived from this file's location)
# --------------------------------------------------------------------------------------

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = Path(__file__).resolve().parent
DEFAULT_BACKUP_DIR = TOOL_DIR / "backups"
DEFAULT_REPORTS_DIR = TOOL_DIR / "reports"

DEFAULT_HEADER_CSV = DEFAULT_REPO_ROOT / "Data" / "Header-Data" / "Header-Data-Main.csv"
DEFAULT_HEADER_NOTES_DIR = DEFAULT_REPO_ROOT / "Data" / "Header-Data" / "Headers"
DEFAULT_DSPRE_ROOT = DEFAULT_REPO_ROOT / "ROM" / "Pokemon-Spectral-Dream_DSPRE_contents"
DEFAULT_ROM_NDS = DEFAULT_REPO_ROOT / "ROM" / "Pokemon-Spectral-Dream.nds"


# --------------------------------------------------------------------------------------
# Constants / enums (ported from 08_AI/tools/ExtractMapHeaders.ps1)
# --------------------------------------------------------------------------------------

AREA_ICON_LABELS = {
    0: "Not Displayed",
    1: "Wall",
    2: "Wood",
    3: "Town",
    4: "Cave",
    5: "Forest",
    6: "Water",
    7: "Field",
    8: "Lake",
    9: "Gray",
}

MAP_TYPE_LABELS = {
    1: "City/Town",
    2: "Route",
    3: "Cave",
    4: "Interior",
    5: "Pokemon Center",
    6: "Underground",
}

WEATHER_LABELS = {
    0: "Normal",
    1: "Rain",
    2: "Heavy Rain",
    3: "Thunderstorm",
    5: "Snow",
    6: "Blizzard",
    7: "Sandstorm",
    8: "Diamond Dust",
    9: "Fog (variant 1)",
    10: "Fog (variant 2)",
    11: "Darkness",
    12: "Darkness (alt)",
    13: "Low Light",
}

FOLLOW_MODE_LABELS = {
    0: "Unallowed",
    1: "Small Only",
    2: "All",
}


CSV_AUTHORITATIVE_COLUMNS = [
    "Internal Name",
    "Matrix",
    "Script File",
    "Level Script File",
    "Event File",
    "Text Archive",
    "Wild File",
    "Area Data",
    "Texture File",
    "Building File",
    "AreaIcon",
    "Music Day",
    "Music Night",
    "Weather",
    "Camera Angle",
    "Move Model Bank",
    "MapSec",
    "WorldMapX",
    "WorldMapY",
    "FlyAllowed",
    "EscapeRopeAllowed",
    "RunningAllowed",
    "BikeAllowed",
    "FollowMode",
    "BattleBackground",
    "MomCallIntroParam",
    "IsKanto",
    "Area_Unknown06",
    "Area_Unknown08",
]


# --------------------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class AreaData:
    building_pack: int
    texture_pack: int
    unknown06: int
    unknown08: int


@dataclass(frozen=True)
class DynamicHeader:
    header_id: int
    wild_encounter_bank: int
    area_data_index: int
    move_model_bank: int
    world_map_x: int
    world_map_y: int
    matrix_id: int
    script_file: int
    level_script_file: int
    text_archive: int
    music_day: int
    music_night: int
    event_file: int
    map_sec: int
    area_icon: int
    mom_call_intro_param: int
    is_kanto: bool
    weather: int
    map_type: int
    camera_angle: int
    follow_mode: int
    battle_background: int
    bike_allowed: bool
    running_allowed: bool
    escape_rope_allowed: bool
    fly_allowed: bool

    @property
    def map_type_label(self) -> str:
        return MAP_TYPE_LABELS.get(self.map_type, f"Unknown({self.map_type})")

    @property
    def weather_label(self) -> str:
        return WEATHER_LABELS.get(self.weather, f"Unknown({self.weather})")

    @property
    def area_icon_label(self) -> str:
        return AREA_ICON_LABELS.get(self.area_icon, f"Unknown({self.area_icon})")

    @property
    def follow_mode_label(self) -> str:
        return FOLLOW_MODE_LABELS.get(self.follow_mode, f"Unknown({self.follow_mode})")


# --------------------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------------------


def parse_mapname_bin(path: Path) -> List[str]:
    """
    DSPRE-style map names table: 16-byte ASCII chunks, NUL-padded.
    Returns a list where index == header id.
    """
    if not path.exists():
        return []
    data = path.read_bytes()
    chunk = 16
    names: List[str] = []
    for offset in range(0, len(data), chunk):
        names.append(data[offset : offset + chunk].decode("ascii", errors="ignore").rstrip("\x00"))
    return names


def parse_area_data(path: Path) -> Optional[AreaData]:
    if not path.exists():
        return None
    data = path.read_bytes()
    if len(data) < 8:
        return None
    building_pack, texture_pack, unknown06, unknown08 = struct.unpack_from("<HHHH", data, 0)
    return AreaData(
        building_pack=building_pack,
        texture_pack=texture_pack,
        unknown06=unknown06,
        unknown08=unknown08,
    )


def parse_dynamic_header(header_id: int, path: Path) -> Optional[DynamicHeader]:
    if not path.exists():
        return None
    data = path.read_bytes()
    if len(data) != 24:
        return None

    wild_encounter_bank = data[0]
    area_data_index = data[1]

    packed_world = struct.unpack_from("<H", data, 2)[0]
    move_model_bank = packed_world & 0xF
    world_map_x = (packed_world >> 4) & 0x3F
    world_map_y = (packed_world >> 10) & 0x3F

    matrix_id = struct.unpack_from("<H", data, 4)[0]
    script_file = struct.unpack_from("<H", data, 6)[0]
    level_script_file = struct.unpack_from("<H", data, 8)[0]
    text_archive = struct.unpack_from("<H", data, 10)[0]
    music_day = struct.unpack_from("<H", data, 12)[0]
    music_night = struct.unpack_from("<H", data, 14)[0]
    event_file = struct.unpack_from("<H", data, 16)[0]

    mapsec_packed = struct.unpack_from("<H", data, 18)[0]
    map_sec = mapsec_packed & 0xFF
    area_icon = (mapsec_packed >> 8) & 0xF
    mom_call_intro_param = (mapsec_packed >> 12) & 0xF

    flags = struct.unpack_from("<I", data, 20)[0]
    is_kanto = (flags & 0x1) != 0
    weather = (flags >> 1) & 0x7F
    map_type = (flags >> 8) & 0xF
    camera_angle = (flags >> 12) & 0x3F
    follow_mode = (flags >> 18) & 0x3
    battle_background = (flags >> 20) & 0x1F
    bike_allowed = ((flags >> 25) & 0x1) == 1
    running_allowed = ((flags >> 26) & 0x1) == 1
    escape_rope_allowed = ((flags >> 27) & 0x1) == 1
    fly_allowed = ((flags >> 28) & 0x1) == 1

    return DynamicHeader(
        header_id=header_id,
        wild_encounter_bank=wild_encounter_bank,
        area_data_index=area_data_index,
        move_model_bank=move_model_bank,
        world_map_x=world_map_x,
        world_map_y=world_map_y,
        matrix_id=matrix_id,
        script_file=script_file,
        level_script_file=level_script_file,
        text_archive=text_archive,
        music_day=music_day,
        music_night=music_night,
        event_file=event_file,
        map_sec=map_sec,
        area_icon=area_icon,
        mom_call_intro_param=mom_call_intro_param,
        is_kanto=is_kanto,
        weather=weather,
        map_type=map_type,
        camera_angle=camera_angle,
        follow_mode=follow_mode,
        battle_background=battle_background,
        bike_allowed=bike_allowed,
        running_allowed=running_allowed,
        escape_rope_allowed=escape_rope_allowed,
        fly_allowed=fly_allowed,
    )


# --------------------------------------------------------------------------------------
# CSV / notes utilities
# --------------------------------------------------------------------------------------


def bool_to_csv(v: bool) -> str:
    return "TRUE" if v else "FALSE"


def safe_int_str(v: int) -> str:
    return str(int(v))


_INVALID_PATH_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')


def sanitize_dir_component(text: str, fallback: str = "UNKNOWN") -> str:
    text = (text or "").strip()
    if not text:
        return fallback
    text = _INVALID_PATH_CHARS.sub("_", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._ ")
    return text or fallback


def header_dir_name(header_id: int, internal_name: str) -> str:
    return f"{header_id:04d}_{sanitize_dir_component(internal_name)}"


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(csv_path: Path) -> Tuple[List[str], List[dict]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return fieldnames, rows


def write_csv_rows(csv_path: Path, fieldnames: List[str], rows: List[dict]) -> None:
    ensure_parent_dir(csv_path)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------------------------
# Validation / reporting
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationFinding:
    header_id: int
    kind: str
    detail: str


def validate_row_files(dspre_root: Path, header_id: int, row: dict) -> List[ValidationFinding]:
    findings: List[ValidationFinding] = []

    def check_num_file(folder: str, col: str, width: int = 4) -> None:
        raw = (row.get(col) or "").strip()
        if not raw:
            return
        if not raw.isdigit():
            return
        n = int(raw)
        name = f"{n:0{width}d}"
        p = dspre_root / "unpacked" / folder / name
        if not p.exists():
            findings.append(ValidationFinding(header_id, "missing_file", f"{col} -> {p}"))

    check_num_file("matrices", "Matrix")
    check_num_file("scripts", "Script File")
    check_num_file("scripts", "Level Script File")
    check_num_file("eventFiles", "Event File")
    check_num_file("textArchives", "Text Archive")
    check_num_file("encounters", "Wild File")
    check_num_file("areaData", "Area Data")

    return findings


def diff_rows(before: dict, after: dict, columns: Iterable[str]) -> List[str]:
    changed: List[str] = []
    for col in columns:
        b = (before.get(col) or "").strip()
        a = (after.get(col) or "").strip()
        if b != a:
            changed.append(col)
    return changed


# --------------------------------------------------------------------------------------
# Main logic
# --------------------------------------------------------------------------------------


def run_update(
    dspre_root: Path,
    csv_path: Path,
    notes_dir: Path,
    backup_dir: Path,
    dry_run: bool,
    reports_dir: Optional[Path] = None,
) -> int:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")
    if not dspre_root.exists():
        # NOTE: `dspre_root` is intentionally NOT in the repo. It must be generated locally
        # from a user-supplied ROM (see ROM/README.md).
        rom_guess = dspre_root.parent / "Pokemon-Spectral-Dream.nds"
        if rom_guess == DEFAULT_ROM_NDS:
            rom_hint = f"- Expected ROM path: `{rom_guess}` (your own legally obtained ROM; ignored by git)"
        else:
            rom_hint = f"- If you are using the default layout, place your ROM at: `{DEFAULT_ROM_NDS}` (ignored by git)"

        raise FileNotFoundError(
            "\n".join(
                [
                    f"DSPRE contents not found: {dspre_root}",
                    "",
                    "This repo does not include extracted ROM contents. To use this tool:",
                    "1) Put your own ROM at `ROM/Pokemon-Spectral-Dream.nds`",
                    "2) Use DSPRE (or your extraction workflow) to extract/unpack into:",
                    "   `ROM/Pokemon-Spectral-Dream_DSPRE_contents/`",
                    "3) Re-run this command (or pass `--dspre-root <path>`).",
                    "",
                    rom_hint,
                ]
            )
        )

    dyn_dir = dspre_root / "unpacked" / "dynamicHeaders"
    if not dyn_dir.exists():
        raise FileNotFoundError(f"dynamicHeaders dir not found: {dyn_dir}")

    mapname_path = dspre_root / "data" / "fielddata" / "maptable" / "mapname.bin"
    map_names = parse_mapname_bin(mapname_path) if mapname_path.exists() else []

    dynamic_headers: Dict[int, DynamicHeader] = {}
    for entry in dyn_dir.iterdir():
        if not entry.is_file():
            continue
        try:
            hid = int(entry.name)
        except ValueError:
            continue
        dh = parse_dynamic_header(hid, entry)
        if dh:
            dynamic_headers[hid] = dh

    fieldnames, existing_rows = read_csv_rows(csv_path)
    existing_by_id: Dict[int, dict] = {}
    passthrough_rows: List[dict] = []

    for row in existing_rows:
        raw = (row.get("HEADER #") or "").strip()
        try:
            hid = int(raw)
        except ValueError:
            passthrough_rows.append(row)
            continue
        existing_by_id[hid] = row

    all_ids = sorted(set(existing_by_id.keys()) | set(dynamic_headers.keys()))
    updated_rows: List[dict] = []
    findings: List[ValidationFinding] = []
    changed_summary: List[Tuple[int, List[str]]] = []
    added_headers: List[int] = []

    for hid in all_ids:
        before = existing_by_id.get(hid)
        row = dict(before) if before else {k: "" for k in fieldnames}
        if not before:
            row["HEADER #"] = str(hid)
            added_headers.append(hid)

        dh = dynamic_headers.get(hid)
        if not dh:
            updated_rows.append(row)
            continue

        internal = row.get("Internal Name", "")
        if map_names and hid < len(map_names):
            internal = map_names[hid] or internal
        row["Internal Name"] = internal

        row["Matrix"] = safe_int_str(dh.matrix_id)
        row["Script File"] = safe_int_str(dh.script_file)
        row["Level Script File"] = safe_int_str(dh.level_script_file)
        row["Event File"] = safe_int_str(dh.event_file)
        row["Text Archive"] = safe_int_str(dh.text_archive)
        row["Wild File"] = safe_int_str(dh.wild_encounter_bank)
        row["Area Data"] = safe_int_str(dh.area_data_index)
        row["AreaIcon"] = dh.area_icon_label
        row["Music Day"] = safe_int_str(dh.music_day)
        row["Music Night"] = safe_int_str(dh.music_night)
        row["Weather"] = dh.weather_label
        row["Camera Angle"] = safe_int_str(dh.camera_angle)
        row["Move Model Bank"] = safe_int_str(dh.move_model_bank)
        row["MapSec"] = safe_int_str(dh.map_sec)
        row["WorldMapX"] = safe_int_str(dh.world_map_x)
        row["WorldMapY"] = safe_int_str(dh.world_map_y)
        row["FlyAllowed"] = bool_to_csv(dh.fly_allowed)
        row["EscapeRopeAllowed"] = bool_to_csv(dh.escape_rope_allowed)
        row["RunningAllowed"] = bool_to_csv(dh.running_allowed)
        row["BikeAllowed"] = bool_to_csv(dh.bike_allowed)
        row["FollowMode"] = dh.follow_mode_label
        row["BattleBackground"] = safe_int_str(dh.battle_background)
        row["MomCallIntroParam"] = safe_int_str(dh.mom_call_intro_param)
        row["IsKanto"] = bool_to_csv(dh.is_kanto)

        current_type = (row.get("Type") or "").strip()
        if not current_type or current_type.lower() == "tbd":
            row["Type"] = dh.map_type_label

        area_path = dspre_root / "unpacked" / "areaData" / f"{dh.area_data_index:04d}"
        area = parse_area_data(area_path)
        if area:
            row["Building File"] = safe_int_str(area.building_pack)
            row["Texture File"] = safe_int_str(area.texture_pack)
            row["Area_Unknown06"] = safe_int_str(area.unknown06)
            row["Area_Unknown08"] = safe_int_str(area.unknown08)

        if before:
            changed_cols = diff_rows(before, row, CSV_AUTHORITATIVE_COLUMNS + ["Type"])
            if changed_cols:
                changed_summary.append((hid, changed_cols))

        findings.extend(validate_row_files(dspre_root, hid, row))
        updated_rows.append(row)

    updated_rows.extend(passthrough_rows)

    def sort_key(r: dict) -> Tuple[int, int]:
        raw = (r.get("HEADER #") or "").strip()
        try:
            return (0, int(raw))
        except ValueError:
            return (1, 10**9)

    updated_rows.sort(key=sort_key)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"Header-Data-Main_{timestamp}.csv"

    if not dry_run:
        shutil.copy2(csv_path, backup_path)
        write_csv_rows(csv_path, fieldnames, updated_rows)

    # Notes + index
    notes_dir.mkdir(parents=True, exist_ok=True)
    index_lines: List[str] = [
        "# Header Index",
        "",
        f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- DSPRE root: `{dspre_root}`",
        f"- CSV: `{csv_path}`",
        "",
        "## Headers",
        "",
    ]

    def _num_or_none(value: object) -> Optional[int]:
        s = ("" if value is None else str(value)).strip()
        if not s.isdigit():
            return None
        return int(s)

    def _unpacked_ref(folder: str, value: object) -> str:
        n = _num_or_none(value)
        if n is None:
            return "(unset)"
        return str(dspre_root / "unpacked" / folder / f"{n:04d}")

    for row in updated_rows:
        raw = (row.get("HEADER #") or "").strip()
        if not raw.isdigit():
            continue
        hid = int(raw)
        internal = row.get("Internal Name", "")
        folder = header_dir_name(hid, internal)
        header_folder = notes_dir / folder
        readme_path = header_folder / "README.md"
        notes_path = header_folder / "notes.md"

        if not dry_run:
            header_folder.mkdir(parents=True, exist_ok=True)
            if not notes_path.exists():
                notes_path.write_text(
                    "\n".join(
                        [
                            "# Notes",
                            "",
                            "Add human notes here (design intent, event requirements, quirks, TODOs).",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )

            lines = [
                f"# Header {hid:04d} — {internal or 'UNKNOWN'}",
                "",
                "## Summary",
                f"- **Type**: `{(row.get('Type') or '').strip()}`",
                f"- **MapSec**: `{row.get('MapSec','')}`",
                f"- **WorldMap**: `({row.get('WorldMapX','')}, {row.get('WorldMapY','')})`",
                f"- **AreaIcon**: `{row.get('AreaIcon','')}`",
                "",
                "## DSPRE references (unpacked)",
                f"- **Matrix**: `{_unpacked_ref('matrices', row.get('Matrix'))}`",
                f"- **Script File**: `{_unpacked_ref('scripts', row.get('Script File'))}`",
                f"- **Level Script File**: `{_unpacked_ref('scripts', row.get('Level Script File'))}`",
                f"- **Event File**: `{_unpacked_ref('eventFiles', row.get('Event File'))}`",
                f"- **Text Archive**: `{_unpacked_ref('textArchives', row.get('Text Archive'))}`",
                f"- **Wild File**: `{_unpacked_ref('encounters', row.get('Wild File'))}`",
                f"- **Area Data**: `{_unpacked_ref('areaData', row.get('Area Data'))}`",
                "",
                "## Flags",
                f"- **FlyAllowed**: `{row.get('FlyAllowed','')}`",
                f"- **EscapeRopeAllowed**: `{row.get('EscapeRopeAllowed','')}`",
                f"- **RunningAllowed**: `{row.get('RunningAllowed','')}`",
                f"- **BikeAllowed**: `{row.get('BikeAllowed','')}`",
                f"- **FollowMode**: `{row.get('FollowMode','')}`",
                f"- **IsKanto**: `{row.get('IsKanto','')}`",
                "",
                "## Validation checklist",
                "- [ ] All referenced files exist in `unpacked/`",
                "- [ ] Header has correct scripts/events/text assigned for this map",
                "- [ ] Any special requirements documented in `notes.md`",
            ]
            readme_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        index_lines.append(f"- `{hid:04d}`: `{internal}` → `{folder}`")

    if not dry_run:
        (notes_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    # Report
    report_lines: List[str] = []
    report_lines.append(f"CSV: {csv_path}")
    report_lines.append(f"DSPRE: {dspre_root}")
    report_lines.append(f"Backed up to: {backup_path}" if not dry_run else "Backed up to: (dry-run)")
    report_lines.append(f"Headers in dynamicHeaders: {len(dynamic_headers)}")
    report_lines.append(f"Headers in CSV (numeric): {len(existing_by_id)}")
    report_lines.append(f"Headers added to CSV: {len(added_headers)}")
    report_lines.append(f"Rows changed: {len(changed_summary)}")
    report_lines.append(f"Validation missing-file findings: {len(findings)}")

    print("\n".join(report_lines))

    # Optional report files (mirrors trainer/encounter tool style)
    if reports_dir is not None and not dry_run:
        reports_dir.mkdir(parents=True, exist_ok=True)
        changes_path = reports_dir / f"header_changes_{timestamp}.csv"
        missing_path = reports_dir / f"header_missing_files_{timestamp}.csv"
        summary_path = reports_dir / f"header_summary_{timestamp}.txt"

        # changes CSV
        with changes_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["HeaderId", "ChangedColumns"])
            for hid, cols in changed_summary:
                w.writerow([hid, ";".join(cols)])

        # missing files CSV
        with missing_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["HeaderId", "Detail"])
            for fnd in findings:
                w.writerow([fnd.header_id, fnd.detail])

        summary_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return 0 if not findings else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Header data tooling for Pokemon Spectral Dream (stdlib-only).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    common.add_argument("--dspre-root", type=Path, default=None)
    common.add_argument("--csv", type=Path, default=None)
    common.add_argument("--notes-dir", type=Path, default=None)
    common.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    common.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    common.add_argument("--dry-run", action="store_true")

    upd = sub.add_parser("update", parents=[common], help="Update header CSV + per-header notes (backs up CSV).")
    upd.set_defaults(_cmd="update")

    val = sub.add_parser("validate", parents=[common], help="Validate header CSV references against DSPRE files.")
    val.set_defaults(_cmd="validate")

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    # Backwards-compatible: if no explicit subcommand, default to `update`.
    argv_list = list(argv) if argv is not None else None
    if argv_list is not None and argv_list and argv_list[0] not in {"update", "validate", "-h", "--help"}:
        argv_list = ["update"] + argv_list

    args = build_parser().parse_args(argv_list)
    cmd = getattr(args, "_cmd", None) or "update"

    repo_root: Path = args.repo_root
    dspre_root = args.dspre_root or (repo_root / "ROM" / "Pokemon-Spectral-Dream_DSPRE_contents")
    csv_path = args.csv or (repo_root / "Data" / "Header-Data" / "Header-Data-Main.csv")
    notes_dir = args.notes_dir or (repo_root / "Data" / "Header-Data" / "Headers")

    if cmd == "validate":
        # Validation-only: do not write anything regardless of --dry-run.
        return run_update(
            dspre_root=dspre_root,
            csv_path=csv_path,
            notes_dir=notes_dir,
            backup_dir=Path(args.backup_dir),
            dry_run=True,
            reports_dir=None,
        )

    return run_update(
        dspre_root=dspre_root,
        csv_path=csv_path,
        notes_dir=notes_dir,
        backup_dir=Path(args.backup_dir),
        dry_run=args.dry_run,
        reports_dir=Path(args.reports_dir) if args.reports_dir else None,
    )


if __name__ == "__main__":
    raise SystemExit(main())


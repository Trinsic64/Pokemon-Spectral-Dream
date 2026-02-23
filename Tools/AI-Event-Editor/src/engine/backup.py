"""Versioned, non-overwriting backup system for event data."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path


class BackupManager:
    """Creates timestamped, append-only backups of event data."""

    def __init__(self, events_dir: Path):
        self.events_dir = events_dir
        self.backups_dir = events_dir / "backups"
        self.backups_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(
        self,
        description: str = "",
        affected_files: list[str] | None = None,
        manifest_data: dict | None = None,
    ) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_desc = "".join(c if c.isalnum() or c in "_-" else "_" for c in description)
        if safe_desc:
            backup_name = f"{timestamp}_{safe_desc[:50]}"
        else:
            backup_name = timestamp

        backup_dir = self.backups_dir / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)

        raw_backup = backup_dir / "raw"
        csv_backup = backup_dir / "csvs"
        raw_backup.mkdir(exist_ok=True)
        csv_backup.mkdir(exist_ok=True)

        raw_dir = self.events_dir / "raw"
        file_hashes: dict[str, str] = {}

        if affected_files:
            for ef in affected_files:
                src = raw_dir / ef.zfill(4)
                if src.exists():
                    dst = raw_backup / ef.zfill(4)
                    shutil.copy2(src, dst)
                    file_hashes[ef] = self._hash_file(src)
        elif raw_dir.is_dir():
            for src in raw_dir.iterdir():
                if src.is_file():
                    shutil.copy2(src, raw_backup / src.name)
                    file_hashes[src.name] = self._hash_file(src)

        for csv_name in ["overworlds.csv", "warps.csv", "spawnables.csv",
                         "triggers.csv", "changelog.csv"]:
            src = self.events_dir / csv_name
            if src.exists():
                shutil.copy2(src, csv_backup / csv_name)

        meta = {
            "timestamp": datetime.now().isoformat(),
            "description": description,
            "affected_files": affected_files or list(file_hashes.keys()),
            "file_hashes": file_hashes,
            "file_count": len(file_hashes),
        }
        (backup_dir / "meta.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )

        if manifest_data:
            (backup_dir / "manifest.json").write_text(
                json.dumps(manifest_data, indent=2), encoding="utf-8"
            )

        return backup_dir

    def list_backups(self) -> list[dict]:
        backups = []
        if not self.backups_dir.is_dir():
            return backups

        for d in sorted(self.backups_dir.iterdir(), reverse=True):
            if not d.is_dir():
                continue
            meta_file = d / "meta.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                    meta["path"] = str(d)
                    meta["name"] = d.name
                    backups.append(meta)
                except json.JSONDecodeError:
                    backups.append({"name": d.name, "path": str(d)})
            else:
                backups.append({"name": d.name, "path": str(d)})

        return backups

    def restore_backup(self, backup_dir: Path,
                       files: list[str] | None = None) -> int:
        raw_backup = backup_dir / "raw"
        csv_backup = backup_dir / "csvs"
        restored = 0

        if raw_backup.is_dir():
            raw_target = self.events_dir / "raw"
            for src in raw_backup.iterdir():
                if files and src.name not in files:
                    continue
                shutil.copy2(src, raw_target / src.name)
                restored += 1

        if csv_backup.is_dir() and not files:
            for src in csv_backup.iterdir():
                shutil.copy2(src, self.events_dir / src.name)
                restored += 1

        return restored

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        h.update(path.read_bytes())
        return h.hexdigest()[:16]

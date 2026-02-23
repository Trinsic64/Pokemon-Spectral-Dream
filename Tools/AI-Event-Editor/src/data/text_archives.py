"""Parse text archives from DSPRE expanded format."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TextArchive:
    id: int
    key: int
    messages: list[str] = field(default_factory=list)
    path: Path | None = None

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def add_message(self, text: str) -> int:
        idx = len(self.messages)
        self.messages.append(text)
        return idx


class TextArchiveDatabase:
    def __init__(self):
        self.archives: dict[int, TextArchive] = {}
        self._dir: Path | None = None
        self._format: str = "txt"

    def load(self, archives_dir: Path) -> None:
        self._dir = archives_dir
        self.archives.clear()

        json_dir = archives_dir
        txt_dir = archives_dir

        for p in sorted(archives_dir.iterdir()):
            if p.suffix == ".json":
                self._format = "json"
                self._load_json(p)
            elif p.suffix == ".txt":
                self._format = "txt"
                self._load_txt(p)
            elif p.suffix == "" and p.is_file():
                try:
                    int(p.name)
                    self._load_txt_nosuffix(p)
                except ValueError:
                    pass

    def _load_json(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            archive_id = int(path.stem)
            key_val = data.get("key", 0)
            if isinstance(key_val, str):
                key_val = int(key_val, 16)
            msgs = []
            for msg in data.get("messages", []):
                text = msg.get("en_US", "")
                if isinstance(text, list):
                    text = "\n".join(text)
                msgs.append(text)
            self.archives[archive_id] = TextArchive(
                id=archive_id, key=key_val, messages=msgs, path=path,
            )
        except (json.JSONDecodeError, ValueError):
            pass

    def _load_txt(self, path: Path) -> None:
        try:
            archive_id = int(path.stem)
        except ValueError:
            return
        self._parse_txt_content(archive_id, path)

    def _load_txt_nosuffix(self, path: Path) -> None:
        try:
            archive_id = int(path.name)
        except ValueError:
            return
        self._parse_txt_content(archive_id, path)

    def _parse_txt_content(self, archive_id: int, path: Path) -> None:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        key = 0
        messages: list[str] = []

        key_match = re.match(r"#\s*Key:\s*(0x[0-9A-Fa-f]+)", lines[0] if lines else "")
        if key_match:
            key = int(key_match.group(1), 16)
            lines = lines[1:]

        for line in lines:
            if line.strip():
                messages.append(line)

        self.archives[archive_id] = TextArchive(
            id=archive_id, key=key, messages=messages, path=path,
        )

    def save_archive(self, archive_id: int) -> None:
        if archive_id not in self.archives or not self._dir:
            return
        archive = self.archives[archive_id]
        if self._format == "json" or (archive.path and archive.path.suffix == ".json"):
            self._save_json(archive)
        else:
            self._save_txt(archive)

    def _save_json(self, archive: TextArchive) -> None:
        path = archive.path or (self._dir / f"{archive.id:04d}.json")
        data = {
            "key": f"0x{archive.key:04X}",
            "messages": [
                {"id": f"msg_{archive.id:04d}_{i:05d}", "en_US": msg}
                for i, msg in enumerate(archive.messages)
            ],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _save_txt(self, archive: TextArchive) -> None:
        path = archive.path or (self._dir / f"{archive.id:04d}.txt")
        lines = [f"# Key: 0x{archive.key:04X}"]
        lines.extend(archive.messages)
        path.write_text("\n".join(lines), encoding="utf-8")

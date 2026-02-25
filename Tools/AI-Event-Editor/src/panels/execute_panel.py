"""Execute Panel: review, backup, and apply pending edits."""

from __future__ import annotations

import csv
import json
import threading
from datetime import datetime
from pathlib import Path

import customtkinter as ctk

from ..engine.serializer import serialize_from_csvs


class ExecutePanel(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build()

    def _build(self):
        title = ctk.CTkLabel(self, text="Execute Edits",
                             font=ctk.CTkFont(size=20, weight="bold"))
        title.pack(pady=(10, 5))

        self.hint_label = ctk.CTkLabel(
            self,
            text="Review pending edits, then create backup and apply.",
            font=ctk.CTkFont(size=12),
            text_color="#bdc3c7",
        )
        self.hint_label.pack(pady=(0, 5))

        # Pending count
        self.pending_label = ctk.CTkLabel(
            self, text="0 pending edits",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f39c12")
        self.pending_label.pack(pady=5)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=5)

        ctk.CTkButton(btn_row, text="Preview Manifest", width=150,
                      command=self._preview_manifest).pack(side="left", padx=5)
        ctk.CTkButton(btn_row, text="Clear All Edits", width=130,
                      fg_color="#e74c3c", hover_color="#c0392b",
                      command=self._clear_edits).pack(side="left", padx=5)

        # Description for backup
        desc_frame = ctk.CTkFrame(self, fg_color="transparent")
        desc_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(desc_frame, text="Backup description:").pack(
            side="left", padx=5)
        self.desc_var = ctk.StringVar(value="AI Event Editor batch")
        ctk.CTkEntry(desc_frame, textvariable=self.desc_var,
                     width=400).pack(side="left", padx=5, fill="x", expand=True)

        # Apply button
        self.apply_btn = ctk.CTkButton(
            self, text="Create Backup & Apply All Edits",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50, fg_color="#2ecc71", hover_color="#27ae60",
            command=self._apply_all)
        self.apply_btn.pack(pady=15, padx=40, fill="x")

        self.progress = ctk.CTkProgressBar(self, width=600)
        self.progress.pack(pady=5)
        self.progress.set(0)

        self.progress_label = ctk.CTkLabel(self, text="")
        self.progress_label.pack(pady=2)

        # Manifest / log viewer
        self.output_text = ctk.CTkTextbox(self, height=300)
        self.output_text.pack(fill="both", expand=True, padx=10, pady=5)

        # Backup list
        backup_frame = ctk.CTkFrame(self)
        backup_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(backup_frame, text="Backups:",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=10, pady=5)
        self.backup_list = ctk.CTkTextbox(backup_frame, height=100)
        self.backup_list.pack(fill="x", padx=10, pady=5)

    def refresh(self):
        count = len(self.app.pending_edits)
        color = "#2ecc71" if count > 0 else "#7f8c8d"
        self.pending_label.configure(
            text=f"{count} pending edit(s)", text_color=color)
        if count > 0:
            self.hint_label.configure(
                text="Pending edits detected. Preview manifest, then apply.",
                text_color="#2ecc71",
            )
        else:
            self.hint_label.configure(
                text="No edits yet. Add items/trainers/NPCs first, then return here.",
                text_color="#bdc3c7",
            )

        if self.app.backup_manager:
            backups = self.app.backup_manager.list_backups()
            self.backup_list.delete("0.0", "end")
            for b in backups[:10]:
                ts = b.get("timestamp", "")
                desc = b.get("description", "")
                files = b.get("file_count", "?")
                self.backup_list.insert("end",
                                        f"{b['name']}  |  {desc}  |  {files} files\n")

    def _preview_manifest(self):
        manifest = {
            "description": self.desc_var.get(),
            "timestamp": datetime.now().isoformat(),
            "edits": self.app.pending_edits,
            "latest_script_artifact": (
                {
                    "script_lines": self.app.latest_script_artifact.script_lines,
                    "movement_lines": self.app.latest_script_artifact.movement_lines,
                }
                if self.app.latest_script_artifact
                else None
            ),
        }
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", json.dumps(manifest, indent=2))

    def _clear_edits(self):
        self.app.clear_pending_edits()
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", "All pending edits cleared.")
        self.refresh()

    def _apply_all(self):
        if not self.app.pending_edits:
            self.output_text.delete("0.0", "end")
            self.output_text.insert("0.0", "No pending edits to apply.")
            return

        preflight = self.app.compat_validator.validate_pending_edits(self.app.pending_edits)
        if preflight.errors:
            self.output_text.delete("0.0", "end")
            self.output_text.insert(
                "0.0",
                "Preflight validation failed:\n- " + "\n- ".join(preflight.errors),
            )
            return

        if not self.app.project.analysis_path:
            self.output_text.delete("0.0", "end")
            self.output_text.insert("0.0", "Project not loaded!")
            return

        self.apply_btn.configure(state="disabled")
        self.progress_label.configure(text="Working...")

        def do_apply():
            try:
                result = self._execute_edits()
                self.after(0, lambda: self._on_apply_complete(result))
            except Exception as e:
                self.after(0, lambda: self._on_apply_complete(f"ERROR: {e}"))

        thread = threading.Thread(target=do_apply, daemon=True)
        thread.start()

    def _execute_edits(self) -> str:
        log: list[str] = []
        desc = self.desc_var.get()
        analysis = self.app.project.analysis_path
        events_dir = analysis / "events"

        # Determine affected event files
        affected = set()
        for edit in self.app.pending_edits:
            ef = edit.get("event_file", "")
            if ef:
                affected.add(ef)

        # 1. Create backup
        self.after(0, lambda: self.progress.set(0.1))
        self.after(0, lambda: self.progress_label.configure(text="Creating backup..."))

        if self.app.backup_manager:
            manifest_data = {
                "description": desc,
                "edits": self.app.pending_edits,
            }
            backup_dir = self.app.backup_manager.create_backup(
                description=desc,
                affected_files=list(affected),
                manifest_data=manifest_data,
            )
            log.append(f"Backup created: {backup_dir.name}")
            log.append("Rollback safety: restore this backup directory if apply fails.")

        # 2. Apply edits to CSVs
        self.after(0, lambda: self.progress.set(0.3))
        self.after(0, lambda: self.progress_label.configure(text="Applying edits to CSVs..."))

        csv_files = {
            "overworld": events_dir / "overworlds.csv",
            "warp": events_dir / "warps.csv",
            "spawnable": events_dir / "spawnables.csv",
            "trigger": events_dir / "triggers.csv",
        }

        csv_data: dict[str, tuple[list[dict], list[str]]] = {}
        for entity_type, path in csv_files.items():
            if path.exists():
                with path.open(encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    csv_data[entity_type] = (list(reader), list(reader.fieldnames or []))
            else:
                csv_data[entity_type] = ([], [])

        edit_count = 0
        for edit in self.app.pending_edits:
            action = edit.get("action", "")
            parts = action.split("_", 1)
            if len(parts) != 2:
                continue
            verb, entity = parts

            if entity not in csv_data:
                continue
            rows, fieldnames = csv_data[entity]
            ef = edit.get("event_file", "").zfill(4)

            if verb == "add":
                raw = edit.get("data", {})
                existing = [r for r in rows if r.get("event_file") == ef]
                new_idx = max((int(r.get("index", 0)) for r in existing), default=-1) + 1
                row_data = {"event_file": ef, "index": str(new_idx), "maps": ""}
                for fn in fieldnames:
                    row_data.setdefault(fn, raw.get(fn, ""))
                rows.append(row_data)
                edit_count += 1

            elif verb == "modify":
                idx = int(edit.get("index", 0))
                changes = edit.get("changes", {})
                targets = [r for r in rows
                           if r.get("event_file") == ef and int(r.get("index", -1)) == idx]
                for t in targets:
                    t.update({k: str(v) for k, v in changes.items()})
                    edit_count += 1

            elif verb == "remove":
                idx = int(edit.get("index", 0))
                rows[:] = [r for r in rows
                           if not (r.get("event_file") == ef
                                   and int(r.get("index", -1)) == idx)]
                edit_count += 1

        # Save CSVs
        for entity_type, path in csv_files.items():
            rows, fieldnames = csv_data[entity_type]
            if fieldnames:
                with path.open("w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(rows)

        log.append(f"Applied {edit_count} edit(s) to CSVs")

        # 3. Serialize affected event files
        self.after(0, lambda: self.progress.set(0.6))
        self.after(0, lambda: self.progress_label.configure(
            text="Serializing event files..."))

        edited_dir = events_dir / "edited"
        edited_dir.mkdir(exist_ok=True)

        for ef in sorted(affected):
            try:
                out = serialize_from_csvs(events_dir, ef, edited_dir)
                size = out.stat().st_size
                log.append(f"Serialized {ef}: {size} bytes -> {out}")
            except Exception as e:
                log.append(f"ERROR serializing {ef}: {e}")

        # 4. Save flags
        self.after(0, lambda: self.progress.set(0.9))
        self.app.project.flags.save()
        log.append("Flag registry saved")

        # 5. Clear pending edits
        self.app.pending_edits.clear()
        log.append(f"\nDone! {edit_count} edits applied to {len(affected)} event file(s).")

        self.after(0, lambda: self.progress.set(1.0))
        return "\n".join(log)

    def _on_apply_complete(self, result: str):
        self.apply_btn.configure(state="normal")
        self.progress_label.configure(text="Complete!")
        self.output_text.delete("0.0", "end")
        self.output_text.insert("0.0", result)
        self.refresh()
        self.app.stats_panel.refresh()
        self.app.set_status("Edits applied successfully!")

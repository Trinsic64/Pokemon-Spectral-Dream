"""Preflight validators for bridge and event edits."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data.loader import ProjectData
from ..model.sub_events import SubEventChain


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


class CompatibilityValidator:
    def __init__(self, project: ProjectData):
        self.project = project

    def validate_chain(self, chain: SubEventChain) -> ValidationReport:
        rep = ValidationReport()
        if not chain.events:
            rep.errors.append("Sub-event chain is empty.")
            return rep

        for i, ev in enumerate(chain.events):
            p = ev.params
            if ev.kind == "give_item":
                item_id = int(p.get("item_id", 0))
                if item_id not in self.project.items.items:
                    rep.errors.append(f"Event #{i}: unknown item id {item_id}.")
            if ev.kind == "give_pokemon":
                species_id = int(p.get("species_id", 0))
                if species_id not in self.project.species.entries:
                    rep.errors.append(f"Event #{i}: unknown species id {species_id}.")
            if ev.kind in ("set_flag", "check_flag"):
                flag_id = int(p.get("flag_id", 0))
                if flag_id not in self.project.flags.flags:
                    rep.errors.append(f"Event #{i}: unknown flag id {flag_id}.")
            if ev.kind in ("set_var", "check_var"):
                var_id = int(p.get("var_id", 0))
                if var_id not in self.project.variables.variables:
                    rep.errors.append(f"Event #{i}: unknown variable id {var_id}.")

        if self.project.script_commands.commands and self.project.script_commands.actions:
            pass
        else:
            rep.warnings.append("Script command/action databases are not loaded.")

        return rep

    def validate_pending_edits(self, edits: list[dict]) -> ValidationReport:
        rep = ValidationReport()
        for idx, edit in enumerate(edits):
            action = edit.get("action", "")
            ef = str(edit.get("event_file", "")).zfill(4)
            if not action:
                rep.errors.append(f"Edit #{idx} has empty action.")
            if len(ef) != 4 or not ef.isdigit():
                rep.errors.append(f"Edit #{idx} has invalid event_file '{ef}'.")
            data = edit.get("data", {})
            if action == "add_overworld":
                for key in ("x_map", "y_map", "script", "type"):
                    if key not in data:
                        rep.errors.append(f"Edit #{idx} missing '{key}' field.")
        return rep


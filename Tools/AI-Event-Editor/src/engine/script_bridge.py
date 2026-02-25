"""Deterministic bridge from sub-events to HGSS-style script lines."""

from __future__ import annotations

from dataclasses import dataclass

from ..model.sub_events import SubEventChain


@dataclass
class ScriptArtifact:
    script_lines: list[str]
    movement_lines: list[str]


class ScriptBridge:
    def build(self, chain: SubEventChain) -> ScriptArtifact:
        script: list[str] = ["LockAll", "FacePlayer"]
        movement: list[str] = []

        for ev in chain.events:
            kind = ev.kind
            p = ev.params
            if kind == "dialogue":
                msg_id = int(p.get("message_id", 0))
                script.extend(
                    [
                        f"Message {msg_id}",
                        "WaitButton",
                        "CloseMsgOnKeyPress",
                    ]
                )
            elif kind == "movement_path":
                for line in p.get("action_lines", []):
                    movement.append(str(line))
                script.extend(["ApplyMovement LAST_TALKED, _MOVE_PATH", "WaitMovement"])
            elif kind == "give_item":
                item_id = int(p.get("item_id", 0))
                qty = int(p.get("quantity", 1))
                script.append(f"GiveItem ITEM_{item_id} {qty} VAR_RESULT")
            elif kind == "give_pokemon":
                species_id = int(p.get("species_id", 0))
                level = int(p.get("level", 5))
                held_item = int(p.get("held_item", 0))
                script.append(f"GivePokemon SPECIES_{species_id} {level} ITEM_{held_item}")
            elif kind == "set_flag":
                script.append(f"SetFlag {int(p.get('flag_id', 0))}")
            elif kind == "set_var":
                script.append(f"SetVar {int(p.get('var_id', 0))} {int(p.get('value', 0))}")
            elif kind == "check_flag":
                script.append(f"CheckFlag {int(p.get('flag_id', 0))}")
            elif kind == "check_var":
                script.append(f"CheckVar {int(p.get('var_id', 0))} {int(p.get('value', 0))}")
            elif kind == "branch_label":
                script.append(f":{p.get('label', 'branch')}")
            elif kind == "end":
                script.append("End")

        if script[-1] != "End":
            script.extend(["ReleaseAll", "End"])
        return ScriptArtifact(script_lines=script, movement_lines=movement)


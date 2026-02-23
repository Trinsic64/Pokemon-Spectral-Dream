"""Parse and validate AI responses for NPC generation."""

from __future__ import annotations

import json
import re

from .client import NPCResult


def parse_response(raw_text: str) -> NPCResult:
    """Parse AI response text into a validated NPCResult."""
    result = NPCResult()

    json_match = re.search(r"\{[\s\S]*\}", raw_text)
    if not json_match:
        result.error = "No JSON object found in AI response"
        return result

    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        result.error = f"Invalid JSON: {e}"
        return result

    result.dialogue_lines = data.get("dialogue_lines", [])
    result.script_commands = data.get("script_commands", [])
    result.sprite_overlay = int(data.get("sprite_overlay", 337))
    result.movement_type = int(data.get("movement_type", 0))

    errors = validate_result(result)
    if errors:
        result.error = "; ".join(errors)
        return result

    result.success = True
    return result


def validate_result(result: NPCResult) -> list[str]:
    """Validate the parsed NPC result."""
    errors: list[str] = []

    if not result.dialogue_lines:
        errors.append("No dialogue lines generated")

    if len(result.dialogue_lines) > 20:
        errors.append(f"Too many dialogue lines ({len(result.dialogue_lines)}), max 20")

    if not result.script_commands:
        errors.append("No script commands generated")

    valid_commands = {
        "Message", "SetVar", "GiveItem", "CheckItem", "Jump",
        "End", "LockAll", "UnlockAll", "FacePlayer", "ReleaseAll",
        "WaitButton", "PlayFanfare", "WaitFanfare", "TextMsgOptions",
    }
    for cmd in result.script_commands:
        first_word = cmd.split()[0] if cmd.split() else ""
        if first_word not in valid_commands:
            errors.append(f"Unknown command: {first_word}")

    if result.sprite_overlay < 0 or result.sprite_overlay > 2000:
        errors.append(f"Invalid sprite overlay: {result.sprite_overlay}")

    return errors

"""AI API client for NPC dialogue generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class NPCResult:
    dialogue_lines: list[str] = field(default_factory=list)
    script_commands: list[str] = field(default_factory=list)
    sprite_overlay: int = 0
    movement_type: int = 0
    success: bool = False
    error: str = ""


class AIClient:
    """Handles API calls to Anthropic or OpenAI for NPC generation."""

    def __init__(self, provider: str = "anthropic", api_key: str = ""):
        self.provider = provider
        self.api_key = api_key
        self._client = None

    def configure(self, provider: str, api_key: str):
        self.provider = provider
        self.api_key = api_key
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_anthropic_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def _get_openai_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("openai package not installed. Run: pip install openai")
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        if self.provider == "anthropic":
            return self._call_anthropic(system_prompt, user_prompt)
        else:
            return self._call_openai(system_prompt, user_prompt)

    def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_anthropic_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        client = self._get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=2000,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content

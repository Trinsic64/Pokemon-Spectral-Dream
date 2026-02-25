"""Ability index from hg-engine abilities.inc."""

from __future__ import annotations

from .equ_db import EquDatabase


class AbilityDatabase(EquDatabase):
    def __init__(self):
        super().__init__(prefix="ABILITY")


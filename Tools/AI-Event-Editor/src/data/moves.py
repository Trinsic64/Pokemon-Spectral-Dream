"""Move index from hg-engine moves.inc."""

from __future__ import annotations

from .equ_db import EquDatabase


class MoveDatabase(EquDatabase):
    def __init__(self):
        super().__init__(prefix="MOVE")


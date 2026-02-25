"""Species index from hg-engine species.inc."""

from __future__ import annotations

from .equ_db import EquDatabase


class SpeciesDatabase(EquDatabase):
    def __init__(self):
        super().__init__(prefix="SPECIES")


"""
GameResources: lazy-loaded CSV maps for area names and achievement names.
"""

from __future__ import annotations

import pkgutil
from typing import ClassVar

from common.types import WowExpansion


class GameResources:
    """Lazy-loaded CSV resource maps for area and achievement names."""

    AREA: ClassVar[dict[int, str]] = {}
    ACHIEVEMENT: ClassVar[dict[int, str]] = {}

    @classmethod
    def _ensure_loaded(cls) -> None:
        if cls.AREA:
            return
        cls.AREA = cls._read_csv("pre_cata_areas.csv")
        cls.ACHIEVEMENT = cls._read_csv("achievements.csv")

    @classmethod
    def init_for_expansion(cls, expansion: WowExpansion) -> None:
        """
        Load area and achievement CSV data for the given expansion.

        Pre-Cataclysm expansions use pre-Cata area maps; Cataclysm and
        later use post-Cata area maps. Achievements are the same across
        all expansions.

        Args:
            expansion: Target WoW expansion to load resources for.
        """
        if expansion in (WowExpansion.VANILLA, WowExpansion.TBC, WowExpansion.WOTLK):
            cls.AREA = cls._read_csv("pre_cata_areas.csv")
        else:
            cls.AREA = cls._read_csv("post_cata_areas.csv")
        cls.ACHIEVEMENT = cls._read_csv("achievements.csv")

    @classmethod
    def _read_csv(cls, filename: str) -> dict[int, str]:
        result: dict[int, str] = {}
        data = pkgutil.get_data("data", filename)
        if data is None:
            return result
        text = data.decode("utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            parts = line.split(",", 1)
            if len(parts) == 2:
                try:
                    result[int(parts[0])] = parts[1]
                except ValueError:
                    continue
        return result

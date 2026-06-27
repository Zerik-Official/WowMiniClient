"""
GameResources: lazy-loaded CSV maps for area names and achievement names.
"""

from __future__ import annotations

import pkgutil
from typing import ClassVar

from common.types import WowExpansion


class GameResources:
    """Lazy-loaded dictionaries mapping IDs to display names."""

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
        Load area and achievement data. Area file depends on expansion.

        Args:
            expansion: Current game expansion.
        """
        if expansion in (WowExpansion.VANILLA, WowExpansion.TBC, WowExpansion.WOTLK):
            cls.AREA = cls._read_csv("pre_cata_areas.csv")
        else:
            cls.AREA = cls._read_csv("post_cata_areas.csv")
        cls.ACHIEVEMENT = cls._read_csv("achievements.csv")

    @classmethod
    def _read_csv(cls, filename: str) -> dict[int, str]:
        """
        Read a CSV file from the 'data' package directory.

        Args:
            filename: CSV file name (e.g. "pre_cata_areas.csv").

        Returns:
            Dict mapping integer ID to display name string.
        """
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

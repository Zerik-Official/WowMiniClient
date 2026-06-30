"""
WoW chat markup conversion: item links, colors, and raid icon markers.
"""

from __future__ import annotations

import re

_WOW_LINK_RE = re.compile(r"\|H(\w+):([^|]+)\|h\[([^\]]+)\]\|h\|r")
_WOW_COLOR_RE = re.compile(r"\|[cC][0-9a-fA-F]{8}")
_WOW_RESET_RE = re.compile(r"\|[rR]")
_WOW_H_RE = re.compile(r"\|[hH]")
_RAID_ICON_RE = re.compile(r"\{(\w+)\}", re.IGNORECASE)

_RAID_ICON_NAMES: dict[str, int] = {
    "star": 1, "rt1": 1, "estrella": 1,
    "circle": 2, "rt2": 2, "circulo": 2,
    "diamond": 3, "rt3": 3, "rombo": 3,
    "triangle": 4, "rt4": 4, "triangulo": 4,
    "moon": 5, "rt5": 5, "luna": 5,
    "square": 6, "rt6": 6, "cuadrado": 6,
    "cross": 7, "x": 7, "rt7": 7, "cruz": 7,
    "skull": 8, "rt8": 8, "calavera": 8, "calabera": 8,
}


def normalize_db_url(url: str | None) -> str | None:
    """
    Normalize an item database URL, adding protocol and stripping trailing slash.

    Args:
        url: Raw URL from config, may be None, missing scheme, or have trailing slash.

    Returns:
        Normalized URL with https:// scheme and no trailing slash, or None.
    """
    if not url:
        return None
    url = url.strip()
    if not url:
        return None
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url.rstrip("/")


def convert_wow_markup(text: str, item_db: str | None) -> str:
    """
    Convert WoW chat format strings into rich text with clickable links.

    Handles |Hitem|h, |Hspell|h, |Hquest|h, |Hachievement|h links and
    removes |cRRGGBBAA color codes, |r reset codes, and |h markers.

    Args:
        text: Raw WoW chat message with markup.
        item_db: Base URL for item/spell/quest lookups (e.g. \"https://comunidadnaer.com\").

    Returns:
        Clean text with links formatted as [[name]](url).
    """
    db_url = normalize_db_url(item_db)

    def _replace_link(match: re.Match) -> str:
        tp = match.group(1).lower()
        data = match.group(2)
        name = match.group(3)
        link_id = data.split(":")[0] if data else ""

        if db_url:
            if tp == "item":
                url = f"{db_url}/?item={link_id}"
            elif tp in ("trade", "spell", "enchant"):
                url = f"{db_url}/?spell={link_id}"
            elif tp == "quest":
                url = f"{db_url}/?quest={link_id}"
            elif tp == "achievement":
                url = f"{db_url}/?achievement={link_id}"
            else:
                return name
            return f"[[{name}]]({url})"
        return name

    text = _WOW_LINK_RE.sub(_replace_link, text)
    text = _WOW_COLOR_RE.sub("", text)
    text = _WOW_RESET_RE.sub("", text)
    text = _WOW_H_RE.sub("", text)
    return text.strip()


def replace_raid_icons(text: str, raid_icons: dict[int, str]) -> str:
    """
    Replace {name} raid target markers with configured emoji strings.

    Supports English (star, circle, ...), Spanish (estrella, circulo, ...),
    and short forms (rt1, rt2, ...), case-insensitive.

    Args:
        text: Message text potentially containing {marker} tokens.
        raid_icons: Mapping of icon index (1-8) to emoji string.

    Returns:
        Text with known markers replaced by emojis, unknown markers left intact.
    """
    if not raid_icons:
        return text

    def _replace(match: re.Match) -> str:
        name = match.group(1).lower()
        idx = _RAID_ICON_NAMES.get(name)
        if idx is None:
            return match.group(0)
        return raid_icons.get(idx, match.group(0))

    return _RAID_ICON_RE.sub(_replace, text)

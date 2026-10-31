"""
Generic template formatting and guild event argument definitions.
"""

from __future__ import annotations

_GUILD_EVENT_ARGS: dict[str, tuple[str, ...]] = {
    "promoted": ("user", "target", "rank"),
    "demoted": ("user", "target", "rank"),
    "joined": ("user",),
    "left": ("user",),
    "removed": ("user", "target"),
    "online": ("user",),
    "offline": ("user",),
    "motd": ("user", "message"),
}


def fmt(template: str, **kwargs: str | None) -> str:
    """
    Replace %key placeholders in a template with the given keyword values.

    Unused placeholders (kwargs with None value) are replaced with an empty string.

    Args:
        template: String containing %key placeholders.
        kwargs: Key-value pairs for replacement. Keys must match placeholder names.

    Returns:
        Formatted string with placeholders resolved.
    """
    result = template
    for key, val in kwargs.items():
        placeholder = f"%{key}"
        if val is not None:
            result = result.replace(placeholder, val)
        else:
            result = result.replace(placeholder, "")
    return result

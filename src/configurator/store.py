"""Reading, validating and writing wowchat.toml for the setup wizard."""

# Standard library
from __future__ import annotations
import os
import tempfile
import tomllib
from pathlib import Path
from typing import Any

# Third-party
import tomli_w

# Project imports
from common.config import load_config
from configurator.schema import (
    default_config,
    merge_managed,
    missing_required,
    normalize,
    with_defaults,
)


class ConfigValidationError(ValueError):
    """Raised when the wizard output cannot be loaded by the client."""


def load_raw(path: Path) -> dict[str, Any]:
    """
    Load the raw configuration from disk, or defaults when it does not exist.

    Args:
        path: Location of wowchat.toml.

    Returns:
        Raw configuration with every managed section filled in.
    """
    if not path.exists():
        return default_config()
    with path.open("rb") as file:
        return with_defaults(tomllib.load(file))


def _read_existing(path: Path) -> dict[str, Any]:
    """
    Read the configuration on disk without applying defaults.

    Args:
        path: Location of wowchat.toml.

    Returns:
        Raw configuration, or an empty dictionary when the file is missing.
    """
    if not path.exists():
        return {}
    with path.open("rb") as file:
        return tomllib.load(file)


def build(raw: dict[str, Any], path: Path) -> dict[str, Any]:
    """
    Normalize and validate wizard output, keeping unmanaged sections from disk.

    Args:
        raw: Configuration produced by the console or the web form.
        path: Location of wowchat.toml, used to preserve unmanaged sections.

    Returns:
        Final configuration that the client can load.

    Raises:
        ConfigValidationError: If required fields are missing or parsing fails.
    """
    try:
        data = merge_managed(_read_existing(path), normalize(raw))
    except (TypeError, ValueError) as exc:
        raise ConfigValidationError(f"Invalid value: {exc}") from exc

    missing = missing_required(data, dict(os.environ))
    if missing:
        raise ConfigValidationError(f"Missing required fields: {', '.join(missing)}")

    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "wowchat.toml"
        probe.write_bytes(tomli_w.dumps(data).encode("utf-8"))
        try:
            load_config(probe)
        except (KeyError, TypeError, ValueError) as exc:
            raise ConfigValidationError(str(exc)) from exc
    return data


def save(raw: dict[str, Any], path: Path) -> Path:
    """
    Validate the configuration and write it to disk.

    Args:
        raw: Configuration produced by the console or the web form.
        path: Destination of wowchat.toml.

    Returns:
        The path that was written.

    Raises:
        ConfigValidationError: If the configuration is not valid.
    """
    data = build(raw, path)
    path.write_text(tomli_w.dumps(data), encoding="utf-8")
    return path

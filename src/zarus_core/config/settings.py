"""Settings helpers for loading package configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .reader import ConfigurationReader


def load_settings(path: str | Path = ConfigurationReader.FILE_NAME) -> dict[str, Any]:
    """Load settings dictionary from JSON configuration file path."""
    return ConfigurationReader.read_config_file(str(path))

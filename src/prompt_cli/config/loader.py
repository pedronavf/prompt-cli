"""Configuration loader with support for drop-in directories."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from prompt_cli.config.schema import Config

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "prompt" / "config.yaml"
DEFAULT_DROPIN_DIR = Path.home() / ".config" / "prompt" / "conf.d"


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list):
            # For lists, extend rather than replace
            result[key] = result[key] + value
        else:
            result[key] = value

    return result


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning empty dict if not found."""
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
        return data if data else {}


def load_dropin_directory(dropin_dir: Path) -> dict[str, Any]:
    """Load and merge all YAML files from drop-in directory."""
    if not dropin_dir.exists():
        return {}

    result: dict[str, Any] = {}
    yaml_files = sorted(dropin_dir.glob("*.yaml")) + sorted(dropin_dir.glob("*.yml"))

    for yaml_file in yaml_files:
        data = load_yaml_file(yaml_file)
        result = deep_merge(result, data)

    return result


def load_config(
    config_path: Path | str | None = None,
    dropin_dir: Path | str | None = None,
) -> Config:
    """Load configuration from file and drop-in directory.

    Args:
        config_path: Path to main config file (default: ~/.config/prompt/config.yaml)
        dropin_dir: Path to drop-in directory (default: ~/.config/prompt/conf.d/)

    Returns:
        Merged configuration object
    """
    # Resolve paths
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH
    elif isinstance(config_path, str):
        config_path = Path(config_path)

    if dropin_dir is None:
        dropin_dir = DEFAULT_DROPIN_DIR
    elif isinstance(dropin_dir, str):
        dropin_dir = Path(dropin_dir)

    # Load main config
    main_config = load_yaml_file(config_path)

    # Load and merge drop-in configs
    dropin_config = load_dropin_directory(dropin_dir)
    merged_data = deep_merge(main_config, dropin_config)

    # Parse into Config model
    return Config(**merged_data)


def load_config_from_string(yaml_string: str) -> Config:
    """Load configuration from a YAML string (useful for testing)."""
    data = yaml.safe_load(yaml_string)
    return Config(**(data if data else {}))

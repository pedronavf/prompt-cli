"""Pytest configuration and fixtures."""

import pytest

from prompt_cli.config.loader import load_config_from_string
from prompt_cli.config.schema import Config


@pytest.fixture
def sample_config() -> Config:
    """Sample configuration for testing."""
    yaml_content = """
config:
  color: true
  default_validator:
    type: file

categories:
  Includes:
    colors: ["blue", "bright cyan"]
  Libraries:
    colors: ["magenta"]
  Default:
    colors: ["white"]

themes:
  default:
    default: "white"
    categories:
      Includes: "blue"
      Libraries: "magenta"

flags:
  - category: Includes
    regexps:
      - "-(I|isystem)(.*)"
    validator:
      type: directory
  - category: Libraries
    regexps:
      - "-(L)(.*)"
      - "-(l)(.+)"
    validator:
      type: directory

programs:
  gcc:
    aliases:
      - g++
      - "glob:*-gcc"
    flags:
      - category: Architecture
        regexps:
          - "-(march|mtune)=(.*)"

keybindings:
  normal:
    ctrl-a: move-line-start
    ctrl-e: move-line-end
    ctrl-q: quit -p

aliases:
  q: quit
  qp: quit -p
"""
    return load_config_from_string(yaml_content)


@pytest.fixture
def empty_config() -> Config:
    """Empty configuration for testing."""
    return Config()

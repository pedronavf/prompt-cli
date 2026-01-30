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


@pytest.fixture
def named_groups_config() -> Config:
    """Configuration with named capture groups for testing."""
    yaml_content = """
config:
  color: true

categories:
  Includes:
    colors:
      flag: blue
      path: bright cyan
  Libraries:
    colors:
      flag: magenta
      path: bright magenta
  Output:
    colors:
      flag: green
      file: bright green
  Default:
    colors:
      "0": white

flags:
  - category: Includes
    regexps:
      - "(?P<flag>-I|-isystem)(?P<path>.*)"
  - category: Libraries
    regexps:
      - "(?P<flag>-L)(?P<path>.*)"
      - "(?P<flag>-l)(?P<name>.+)"
  - category: Output
    regexps:
      - "(?P<flag>-o)(?P<file>.*)"
"""
    return load_config_from_string(yaml_content)


@pytest.fixture
def capture_groups_config() -> Config:
    """Configuration with capture_groups array (no named regexp groups)."""
    yaml_content = """
config:
  color: true

categories:
  Sanitizers:
    colors:
      flag: red
      name: yellow
      value: cyan
  Default:
    colors:
      "0": white

flags:
  - category: Sanitizers
    regexps:
      - "(-f)(sanitize=)(.*)"
    capture_groups:
      - flag
      - name
      - value
"""
    return load_config_from_string(yaml_content)

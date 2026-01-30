"""Tests for the config module."""

import tempfile
from pathlib import Path

from prompt_cli.config.loader import (
    deep_merge,
    load_config,
    load_config_from_string,
)
from prompt_cli.config.schema import (
    Config,
    parse_validator,
)


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}

        result = deep_merge(base, override)

        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        override = {"a": {"y": 5, "z": 6}}

        result = deep_merge(base, override)

        assert result == {"a": {"x": 1, "y": 5, "z": 6}, "b": 3}

    def test_merge_lists(self):
        """Test merging lists (extend behavior)."""
        base = {"items": [1, 2]}
        override = {"items": [3, 4]}

        result = deep_merge(base, override)

        assert result == {"items": [1, 2, 3, 4]}


class TestLoadConfigFromString:
    """Tests for load_config_from_string function."""

    def test_load_minimal_config(self):
        """Test loading minimal configuration."""
        yaml = """
config:
  color: true
"""
        config = load_config_from_string(yaml)

        assert config.config.color is True

    def test_load_with_categories(self):
        """Test loading configuration with categories."""
        yaml = """
categories:
  Includes:
    colors: ["blue"]
  Libraries:
    colors: ["magenta"]
"""
        config = load_config_from_string(yaml)

        assert "includes" in config.categories
        # List colors are converted to dict with numeric keys
        assert config.categories["includes"].colors == {"0": "blue"}

    def test_load_with_named_colors(self):
        """Test loading configuration with named color groups."""
        yaml = """
categories:
  Includes:
    colors:
      flag: blue
      path: cyan
"""
        config = load_config_from_string(yaml)

        assert "includes" in config.categories
        assert config.categories["includes"].colors == {"flag": "blue", "path": "cyan"}

    def test_load_with_flags(self):
        """Test loading configuration with flags."""
        yaml = """
flags:
  - category: Includes
    regexps:
      - "-(I)(.*)"
"""
        config = load_config_from_string(yaml)

        assert len(config.flags) == 1
        assert config.flags[0].category == "Includes"

    def test_load_with_capture_groups(self):
        """Test loading flags with capture_groups for naming."""
        yaml = """
flags:
  - category: Sanitizers
    regexps:
      - "(-f)(sanitize=)(.*)"
    capture_groups:
      - flag
      - name
      - value
"""
        config = load_config_from_string(yaml)

        assert len(config.flags) == 1
        assert config.flags[0].capture_groups == ["flag", "name", "value"]

    def test_load_with_programs(self):
        """Test loading configuration with programs."""
        yaml = """
programs:
  gcc:
    aliases:
      - g++
    flags:
      - category: Debug
        regexps:
          - "-(g)(.*)"
"""
        config = load_config_from_string(yaml)

        assert "gcc" in config.programs
        assert "g++" in config.programs["gcc"].aliases


class TestConfig:
    """Tests for Config class."""

    def test_get_program_exact_match(self, sample_config):
        """Test getting program by exact name."""
        program = sample_config.get_program("gcc")

        assert program is not None
        assert program.name == "gcc"

    def test_get_program_alias_match(self, sample_config):
        """Test getting program by alias."""
        program = sample_config.get_program("g++")

        assert program is not None
        assert program.name == "gcc"

    def test_get_program_glob_match(self, sample_config):
        """Test getting program by glob pattern."""
        program = sample_config.get_program("arm-linux-gnueabi-gcc")

        assert program is not None
        assert program.name == "gcc"

    def test_get_program_no_match(self, sample_config):
        """Test getting program with no match."""
        program = sample_config.get_program("unknown-compiler")

        assert program is None

    def test_get_flags_for_program(self, sample_config):
        """Test getting flags for a program."""
        flags = sample_config.get_flags_for_program("gcc")

        # Should include global flags + gcc-specific flags
        categories = {f.category for f in flags}
        assert "Includes" in categories
        assert "Libraries" in categories
        assert "Architecture" in categories

    def test_get_theme_default(self, sample_config):
        """Test getting default theme."""
        theme = sample_config.get_theme()

        assert theme.name == "default"

    def test_get_theme_by_name(self, sample_config):
        """Test getting theme by name."""
        theme = sample_config.get_theme("default")

        assert theme.name == "default"


class TestParseValidator:
    """Tests for parse_validator function."""

    def test_parse_file_validator(self):
        """Test parsing file validator config."""
        config = {"type": "file", "extensions": [".c", ".h"]}
        validator = parse_validator(config)

        assert validator is not None
        assert validator.type == "file"
        assert validator.extensions == [".c", ".h"]

    def test_parse_choice_validator(self):
        """Test parsing choice validator config."""
        config = {"type": "choice", "options": ["a", "b", "c"]}
        validator = parse_validator(config)

        assert validator is not None
        assert validator.type == "choice"
        assert validator.options == ["a", "b", "c"]

    def test_parse_none_validator(self):
        """Test parsing None validator config."""
        validator = parse_validator(None)

        assert validator is None


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file returns empty config."""
        config = load_config(config_path="/nonexistent/path/config.yaml")

        # Should return empty/default config, not raise
        assert isinstance(config, Config)

    def test_load_with_dropin_directory(self):
        """Test loading with drop-in directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create main config
            main_config = Path(tmpdir) / "config.yaml"
            main_config.write_text("""
categories:
  Includes:
    colors: ["blue"]
""")

            # Create drop-in config
            dropin_dir = Path(tmpdir) / "conf.d"
            dropin_dir.mkdir()
            (dropin_dir / "extra.yaml").write_text("""
categories:
  Libraries:
    colors: ["magenta"]
""")

            config = load_config(config_path=main_config, dropin_dir=dropin_dir)

            assert "includes" in config.categories
            assert "libraries" in config.categories

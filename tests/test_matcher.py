"""Tests for the matcher module."""


from prompt_cli.core.matcher import Matcher, expand_category_map
from prompt_cli.core.tokenizer import tokenize


class TestMatcher:
    """Tests for Matcher class."""

    def test_match_include_flag(self, sample_config):
        """Test matching include flags."""
        matcher = Matcher(sample_config)
        tokens = tokenize("-I/tmp/foo")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Includes"
        assert len(result.groups) >= 1

    def test_match_library_flag(self, sample_config):
        """Test matching library flags."""
        matcher = Matcher(sample_config)
        tokens = tokenize("-L/usr/lib")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Libraries"

    def test_match_library_link_flag(self, sample_config):
        """Test matching -l flag."""
        matcher = Matcher(sample_config)
        tokens = tokenize("-lpthread")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Libraries"

    def test_no_match_defaults(self, sample_config):
        """Test that unmatched tokens get Default category."""
        matcher = Matcher(sample_config)
        tokens = tokenize("main.c")

        result = matcher.match_token(tokens[0])

        assert not result.matched
        assert result.category == "Default"
        assert result.is_default

    def test_match_tokens_with_executable(self, sample_config):
        """Test matching multiple tokens."""
        matcher = Matcher(sample_config)
        tokens = tokenize("gcc -I/tmp/foo main.c")

        results = matcher.match_tokens(tokens)

        assert len(results) == 3
        assert results[0].category == "Executable"  # gcc
        assert results[1].category == "Includes"  # -I/tmp/foo
        assert results[2].category == "Default"  # main.c

    def test_executable_with_preset(self, sample_config):
        """Test that first token is Executable even when executable is preset."""
        matcher = Matcher(sample_config, executable="gcc")
        tokens = tokenize("gcc -I/tmp/foo main.c")

        results = matcher.match_tokens(tokens)

        assert len(results) == 3
        assert results[0].category == "Executable"  # gcc should still be Executable
        assert results[1].category == "Includes"

    def test_program_specific_flags(self, sample_config):
        """Test program-specific flag matching."""
        matcher = Matcher(sample_config, executable="gcc")
        tokens = tokenize("-march=x86_64")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Architecture"

    def test_capture_groups(self, sample_config):
        """Test capture group extraction."""
        matcher = Matcher(sample_config)
        tokens = tokenize("-I/tmp/foo")

        result = matcher.match_token(tokens[0])

        assert len(result.groups) >= 1
        # Check that groups capture the right parts

    def test_find_duplicates(self, sample_config):
        """Test finding duplicate flags."""
        matcher = Matcher(sample_config)
        tokens = tokenize("gcc -I/tmp/foo -I/usr/include -L/lib")

        results = matcher.match_tokens(tokens)
        duplicates = matcher.find_duplicates(results)

        assert "Includes" in duplicates
        assert len(duplicates["Includes"]) == 2  # Two -I flags

    def test_get_equivalent_indices(self, sample_config):
        """Test getting equivalent parameter indices."""
        matcher = Matcher(sample_config)
        tokens = tokenize("gcc -I/tmp -o test -I/usr")

        results = matcher.match_tokens(tokens)
        equivalents = matcher.get_equivalent_indices(results, 1)  # First -I

        assert 1 in equivalents
        assert 4 in equivalents  # Second -I


class TestExpandCategoryMap:
    """Tests for expand_category_map function."""

    def test_expand_single_category(self, sample_config):
        """Test expanding a single category."""
        result = expand_category_map(sample_config, "Includes")

        assert result == ["Includes"]

    def test_expand_unknown_category(self, sample_config):
        """Test expanding an unknown category."""
        result = expand_category_map(sample_config, "Unknown")

        assert result == ["Unknown"]


class TestNamedCaptureGroups:
    """Tests for named capture group support."""

    def test_named_groups_extracted(self, named_groups_config):
        """Test that named groups are extracted correctly."""
        matcher = Matcher(named_groups_config)
        tokens = tokenize("-I/tmp/foo")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Includes"
        # Should have named groups
        assert len(result.groups) == 2
        flag_group = result.get_group("flag")
        path_group = result.get_group("path")
        assert flag_group is not None
        assert flag_group.value == "-I"
        assert path_group is not None
        assert path_group.value == "/tmp/foo"

    def test_get_group_value(self, named_groups_config):
        """Test get_group_value helper method."""
        matcher = Matcher(named_groups_config)
        tokens = tokenize("-L/usr/lib")

        result = matcher.match_token(tokens[0])

        assert result.get_group_value("flag") == "-L"
        assert result.get_group_value("path") == "/usr/lib"
        assert result.get_group_value("nonexistent", "default") == "default"

    def test_named_groups_dict(self, named_groups_config):
        """Test named_groups property."""
        matcher = Matcher(named_groups_config)
        tokens = tokenize("-lm")

        result = matcher.match_token(tokens[0])

        assert result.named_groups == {"flag": "-l", "name": "m"}

    def test_isystem_flag(self, named_groups_config):
        """Test -isystem flag with named groups."""
        matcher = Matcher(named_groups_config)
        tokens = tokenize("-isystem/usr/include")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.get_group_value("flag") == "-isystem"
        assert result.get_group_value("path") == "/usr/include"

    def test_output_flag(self, named_groups_config):
        """Test -o flag with named groups."""
        matcher = Matcher(named_groups_config)
        tokens = tokenize("-otest")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Output"
        assert result.get_group_value("flag") == "-o"
        assert result.get_group_value("file") == "test"

    def test_groups_preserve_positions(self, named_groups_config):
        """Test that group positions are correct."""
        matcher = Matcher(named_groups_config)
        tokens = tokenize("-I/tmp/foo")

        result = matcher.match_token(tokens[0])

        flag_group = result.get_group("flag")
        path_group = result.get_group("path")
        assert flag_group.start == 0
        assert flag_group.end == 2  # "-I"
        assert path_group.start == 2
        assert path_group.end == 10  # "/tmp/foo"


class TestCaptureGroupsFromConfig:
    """Tests for capture_groups array naming (without (?P<name>...) syntax)."""

    def test_capture_groups_names_applied(self, capture_groups_config):
        """Test that capture_groups from config are used to name groups."""
        matcher = Matcher(capture_groups_config)
        tokens = tokenize("-fsanitize=address")

        result = matcher.match_token(tokens[0])

        assert result.matched
        assert result.category == "Sanitizers"
        # Groups should be named from capture_groups config
        assert result.get_group("flag") is not None
        assert result.get_group("flag").value == "-f"
        assert result.get_group("name") is not None
        assert result.get_group("name").value == "sanitize="
        assert result.get_group("value") is not None
        assert result.get_group("value").value == "address"

    def test_capture_groups_dict(self, capture_groups_config):
        """Test named_groups property with capture_groups config."""
        matcher = Matcher(capture_groups_config)
        tokens = tokenize("-fsanitize=undefined")

        result = matcher.match_token(tokens[0])

        assert result.named_groups == {
            "flag": "-f",
            "name": "sanitize=",
            "value": "undefined",
        }

    def test_mixed_named_and_config_groups(self):
        """Test that regexp named groups take precedence over config."""
        from prompt_cli.config.loader import load_config_from_string

        # Config where regexp has one named group but capture_groups provides names for others
        yaml = """
flags:
  - category: Test
    regexps:
      - "(?P<flag>-f)(sanitize=)(.*)"
    capture_groups:
      - should_be_ignored
      - name
      - value
"""
        config = load_config_from_string(yaml)
        matcher = Matcher(config)
        tokens = tokenize("-fsanitize=leak")

        result = matcher.match_token(tokens[0])

        # "flag" comes from regexp, "name" and "value" from capture_groups
        assert result.get_group("flag").value == "-f"
        assert result.get_group("name").value == "sanitize="
        assert result.get_group("value").value == "leak"



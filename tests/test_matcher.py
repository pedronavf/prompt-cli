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

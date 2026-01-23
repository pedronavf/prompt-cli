"""Tests for the programs module."""

import pytest

from prompt_cli.core.programs import (
    detect_program,
    find_compiler,
    get_program_names,
    _match_builtin,
    _match_config,
    _is_launcher,
)
from prompt_cli.core.tokenizer import Token, QuoteType


class TestMatchBuiltin:
    """Tests for built-in program matching."""

    def test_exact_gcc(self):
        """Test exact match for gcc."""
        assert _match_builtin("gcc") == "gcc"

    def test_exact_gpp(self):
        """Test exact match for g++."""
        assert _match_builtin("g++") == "gcc"

    def test_exact_clang(self):
        """Test exact match for clang."""
        assert _match_builtin("clang") == "clang"

    def test_suffix_gcc(self):
        """Test suffix match for cross-compiler gcc."""
        assert _match_builtin("arm-linux-gnueabi-gcc") == "gcc"
        assert _match_builtin("aarch64-linux-gnu-gcc") == "gcc"
        assert _match_builtin("x86_64-w64-mingw32-g++") == "gcc"

    def test_suffix_clang(self):
        """Test suffix match for cross-compiler clang."""
        assert _match_builtin("arm-linux-gnueabi-clang") == "clang"

    def test_prefix_gcc(self):
        """Test prefix match for versioned gcc."""
        assert _match_builtin("gcc-12") == "gcc"
        assert _match_builtin("g++-11") == "gcc"

    def test_prefix_clang(self):
        """Test prefix match for versioned clang."""
        assert _match_builtin("clang-15") == "clang"
        assert _match_builtin("clang++-14") == "clang"

    def test_other_programs(self):
        """Test other built-in programs."""
        assert _match_builtin("rustc") == "rustc"
        assert _match_builtin("cargo") == "cargo"
        assert _match_builtin("go") == "go"
        assert _match_builtin("python3") == "python"
        assert _match_builtin("make") == "make"
        assert _match_builtin("cmake") == "cmake"

    def test_unknown_program(self):
        """Test unknown program returns None."""
        assert _match_builtin("unknown-compiler") is None
        assert _match_builtin("my-custom-tool") is None


class TestMatchConfig:
    """Tests for config-based program matching."""

    def test_exact_name_match(self, sample_config):
        """Test exact name match from config."""
        result = _match_config("gcc", sample_config)
        assert result == "gcc"

    def test_literal_alias_match(self, sample_config):
        """Test literal alias match."""
        result = _match_config("g++", sample_config)
        assert result == "gcc"

    def test_glob_alias_match(self, sample_config):
        """Test glob pattern alias match."""
        result = _match_config("arm-linux-gcc", sample_config)
        # The sample_config has "glob:*-gcc" alias
        assert result == "gcc"

    def test_unknown_program(self, sample_config):
        """Test unknown program returns None."""
        result = _match_config("unknown-compiler", sample_config)
        assert result is None


class TestDetectProgram:
    """Tests for detect_program function."""

    def test_detect_gcc(self, sample_config):
        """Test detecting gcc."""
        result = detect_program("gcc", sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.matched_name == "gcc"
        assert result.source == "builtin"

    def test_detect_cross_compiler(self, sample_config):
        """Test detecting cross-compiler."""
        result = detect_program("/usr/bin/arm-linux-gnueabi-gcc", sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.matched_name == "arm-linux-gnueabi-gcc"
        assert result.source == "builtin"

    def test_detect_with_path(self, sample_config):
        """Test detecting with full path."""
        result = detect_program("/usr/bin/clang", sample_config)

        assert result is not None
        assert result.canonical_name == "clang"
        assert result.matched_name == "clang"

    def test_detect_unknown_returns_basename(self, sample_config):
        """Test unknown program returns basename."""
        result = detect_program("/path/to/my-custom-tool", sample_config)

        assert result is not None
        assert result.canonical_name == "my-custom-tool"
        assert result.source == "unknown"

    def test_detect_without_config(self):
        """Test detection without config uses builtin only."""
        result = detect_program("gcc", None)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.source == "builtin"


class TestGetProgramNames:
    """Tests for get_program_names function."""

    def test_includes_builtin_names(self):
        """Test that built-in program names are included."""
        names = get_program_names(None)

        assert "gcc" in names
        assert "clang" in names
        assert "make" in names
        assert "python" in names

    def test_includes_config_names(self, sample_config):
        """Test that config program names are included."""
        names = get_program_names(sample_config)

        # Built-in
        assert "gcc" in names
        # From sample_config
        assert "g++" in names  # literal alias

    def test_sorted_output(self, sample_config):
        """Test that output is sorted."""
        names = get_program_names(sample_config)

        assert names == sorted(names)


class TestIsLauncher:
    """Tests for launcher detection."""

    def test_ccache_is_launcher(self):
        """Test ccache is detected as launcher."""
        result = _is_launcher("ccache")
        assert result is not None
        assert result[0] == "ccache"

    def test_distcc_is_launcher(self):
        """Test distcc is detected as launcher."""
        result = _is_launcher("distcc")
        assert result is not None
        assert result[0] == "distcc"

    def test_sccache_is_launcher(self):
        """Test sccache is detected as launcher."""
        result = _is_launcher("sccache")
        assert result is not None
        assert result[0] == "sccache"

    def test_gcc_is_not_launcher(self):
        """Test gcc is not detected as launcher."""
        result = _is_launcher("gcc")
        assert result is None

    def test_case_insensitive(self):
        """Test launcher detection is case insensitive."""
        result = _is_launcher("CCACHE")
        assert result is not None
        assert result[0] == "ccache"


class TestFindCompiler:
    """Tests for find_compiler function."""

    def _make_tokens(self, values: list[str]) -> list[Token]:
        """Helper to create tokens from string values."""
        tokens = []
        pos = 0
        for value in values:
            tokens.append(Token(value=value, start=pos, end=pos + len(value), quote_type=QuoteType.NONE, raw=value))
            pos += len(value) + 1
        return tokens

    def test_simple_gcc(self, sample_config):
        """Test finding gcc as first token."""
        tokens = self._make_tokens(["gcc", "-O2", "foo.c"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.token_index == 0
        assert result.launcher is None

    def test_gcc_with_path(self, sample_config):
        """Test finding gcc with full path."""
        tokens = self._make_tokens(["/usr/bin/gcc", "-O2", "foo.c"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.token_index == 0

    def test_ccache_gcc(self, sample_config):
        """Test finding gcc after ccache launcher."""
        tokens = self._make_tokens(["ccache", "gcc", "-O2", "foo.c"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.token_index == 1
        assert result.launcher is not None
        assert result.launcher.name == "ccache"
        assert result.launcher.token_index == 0

    def test_ccache_with_path(self, sample_config):
        """Test finding gcc after ccache with paths."""
        tokens = self._make_tokens(["/usr/bin/ccache", "/usr/bin/gcc", "-O2"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.token_index == 1
        assert result.launcher is not None

    def test_cross_compiler_with_ccache(self, sample_config):
        """Test finding cross-compiler after ccache."""
        tokens = self._make_tokens(["ccache", "arm-linux-gnueabihf-gcc", "-O2"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.matched_name == "arm-linux-gnueabihf-gcc"
        assert result.token_index == 1

    def test_distcc_gcc(self, sample_config):
        """Test finding gcc after distcc launcher."""
        tokens = self._make_tokens(["distcc", "gcc", "-O2", "foo.c"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "gcc"
        assert result.token_index == 1
        assert result.launcher.name == "distcc"

    def test_empty_tokens(self, sample_config):
        """Test with empty token list."""
        result = find_compiler([], sample_config)
        assert result is None

    def test_unknown_program(self, sample_config):
        """Test with unknown program."""
        tokens = self._make_tokens(["my-custom-tool", "-a", "-b"])
        result = find_compiler(tokens, sample_config)

        assert result is not None
        assert result.canonical_name == "my-custom-tool"
        assert result.source == "unknown"
        assert result.token_index == 0

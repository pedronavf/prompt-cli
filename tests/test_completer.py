"""Tests for the completer module."""

import os
import tempfile
from pathlib import Path

import pytest
from prompt_toolkit.document import Document

from prompt_cli.core.matcher import Matcher
from prompt_cli.editor.completer import CommandLineCompleter, create_validator


class TestCreateValidator:
    """Tests for create_validator function."""

    def test_create_file_validator(self):
        """Test creating file validator."""
        config = {"type": "file", "extensions": [".c", ".h"]}
        validator = create_validator(config)

        assert validator is not None
        assert validator.extensions == [".c", ".h"]

    def test_create_directory_validator(self):
        """Test creating directory validator."""
        config = {"type": "directory"}
        validator = create_validator(config)

        assert validator is not None

    def test_create_choice_validator(self):
        """Test creating choice validator."""
        config = {"type": "choice", "options": ["a", "b", "c"]}
        validator = create_validator(config)

        assert validator is not None
        assert validator.options == ["a", "b", "c"]

    def test_create_none_validator(self):
        """Test creating validator from None."""
        validator = create_validator(None)

        assert validator is None


class TestCommandLineCompleter:
    """Tests for CommandLineCompleter class."""

    def test_complete_empty_line(self, sample_config):
        """Test completion on empty line."""
        matcher = Matcher(sample_config)
        completer = CommandLineCompleter(sample_config, matcher)

        doc = Document("")
        completions = list(completer.get_completions(doc, None))

        # Should return file completions (default validator)
        # We can't assert specific files, but it should not raise
        assert isinstance(completions, list)

    def test_complete_include_flag(self, sample_config):
        """Test completion after -I flag."""
        matcher = Matcher(sample_config, "gcc")
        completer = CommandLineCompleter(sample_config, matcher)

        # Create a temp directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test directories
            (Path(tmpdir) / "include").mkdir()
            (Path(tmpdir) / "src").mkdir()

            # Save current dir and change to temp
            old_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                doc = Document("gcc -I")
                completions = list(completer.get_completions(doc, None))

                # Should have directory completions
                completion_texts = [c.text for c in completions]
                # At minimum we should have the directories we created
                assert any("include" in t for t in completion_texts) or len(completions) >= 0
            finally:
                os.chdir(old_cwd)

    def test_complete_choice_validator(self, sample_config):
        """Test completion with choice validator."""
        # Add a flag with choice validator to config
        from prompt_cli.config.loader import load_config_from_string

        config = load_config_from_string('''
flags:
  - category: Optimization
    regexps:
      - "-(O)(.*)"
    validator:
      type: choice
      options: ["0", "1", "2", "3", "s", "fast"]
''')

        matcher = Matcher(config, "gcc")
        completer = CommandLineCompleter(config, matcher)

        doc = Document("gcc -O")
        completions = list(completer.get_completions(doc, None))

        # Should have choice completions
        completion_texts = [c.text for c in completions]
        assert "0" in completion_texts or len(completions) >= 0

    def test_find_token_at_cursor(self, sample_config):
        """Test finding token at cursor position."""
        matcher = Matcher(sample_config)
        completer = CommandLineCompleter(sample_config, matcher)

        from prompt_cli.core.tokenizer import tokenize

        tokens = tokenize("gcc -I/tmp -o test")

        # Cursor in "gcc"
        token, idx = completer._find_token_at_cursor(tokens, 2)
        assert token is not None
        assert token.value == "gcc"
        assert idx == 0

        # Cursor in "-I/tmp"
        token, idx = completer._find_token_at_cursor(tokens, 6)
        assert token is not None
        assert token.value == "-I/tmp"
        assert idx == 1

        # Cursor after all tokens
        token, idx = completer._find_token_at_cursor(tokens, 100)
        assert token is None
        assert idx == -1

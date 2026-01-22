"""Tests for the commands module."""

import pytest

from prompt_cli.editor.commands import (
    CommandRegistry,
    commands,
    parse_command_string,
)


class TestParseCommandString:
    """Tests for parse_command_string function."""

    def test_simple_command(self):
        """Test parsing simple command."""
        name, args = parse_command_string("quit")

        assert name == "quit"
        assert args == []

    def test_command_with_args(self):
        """Test parsing command with arguments."""
        name, args = parse_command_string("quit -p -y")

        assert name == "quit"
        assert args == ["-p", "-y"]

    def test_command_with_quoted_arg(self):
        """Test parsing command with quoted argument."""
        name, args = parse_command_string('lights-off "my category"')

        assert name == "lights-off"
        assert args == ["my category"]

    def test_empty_string(self):
        """Test parsing empty string."""
        name, args = parse_command_string("")

        assert name == ""
        assert args == []


class TestCommandRegistry:
    """Tests for CommandRegistry class."""

    def test_register_and_get(self):
        """Test registering and getting a command."""
        registry = CommandRegistry()

        @registry.register("test-command")
        def test_command(editor, args):
            pass

        assert registry.get("test-command") is not None

    def test_abbreviation_matching(self):
        """Test command abbreviation matching."""
        registry = CommandRegistry()

        @registry.register("copy-file")
        def copy_file(editor, args):
            pass

        @registry.register("copy-line")
        def copy_line(editor, args):
            pass

        # Unique abbreviation
        assert registry.get("c-f") is copy_file
        assert registry.get("c-l") is copy_line

        # Full name
        assert registry.get("copy-file") is copy_file

    def test_ambiguous_abbreviation(self):
        """Test that ambiguous abbreviations raise error."""
        registry = CommandRegistry()

        @registry.register("copy-file")
        def copy_file(editor, args):
            pass

        @registry.register("copy-folder")
        def copy_folder(editor, args):
            pass

        # "c-f" matches both copy-file and copy-folder
        with pytest.raises(ValueError, match="Ambiguous"):
            registry.get("c-f")

    def test_list_commands(self):
        """Test listing registered commands."""
        registry = CommandRegistry()

        @registry.register("a-command")
        def a_command(editor, args):
            pass

        @registry.register("b-command")
        def b_command(editor, args):
            pass

        cmds = registry.list_commands()

        assert "a-command" in cmds
        assert "b-command" in cmds
        assert cmds == sorted(cmds)  # Sorted


class TestBuiltinCommands:
    """Tests for builtin commands in the global registry."""

    def test_quit_registered(self):
        """Test that quit command is registered."""
        assert commands.get("quit") is not None

    def test_move_commands_registered(self):
        """Test that movement commands are registered."""
        assert commands.get("move-char-left") is not None
        assert commands.get("move-char-right") is not None
        assert commands.get("move-word-left") is not None
        assert commands.get("move-word-right") is not None
        assert commands.get("move-line-start") is not None
        assert commands.get("move-line-end") is not None

    def test_delete_commands_registered(self):
        """Test that delete commands are registered."""
        assert commands.get("delete-char") is not None
        assert commands.get("delete-word-left") is not None
        assert commands.get("delete-param") is not None

    def test_duplicates_commands_registered(self):
        """Test that duplicates mode commands are registered."""
        assert commands.get("show-duplicates") is not None
        assert commands.get("duplicate-next") is not None
        assert commands.get("duplicates-keep") is not None
        assert commands.get("duplicates-exit") is not None

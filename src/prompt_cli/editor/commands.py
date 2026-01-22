"""Bindable commands for the editor."""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_cli.editor.prompt import CommandLineEditor


@dataclass
class CommandResult:
    """Result of executing a command."""

    success: bool = True
    message: str = ""
    exit_editor: bool = False
    print_result: bool = False
    reset_before_print: bool = False


class CommandRegistry:
    """Registry of bindable commands."""

    def __init__(self) -> None:
        self._commands: dict[str, Callable[..., CommandResult]] = {}
        self._command_words: dict[str, set[str]] = {}  # For abbreviation matching

    def register(self, name: str) -> Callable[[Callable[..., CommandResult]], Callable[..., CommandResult]]:
        """Decorator to register a command."""
        def decorator(func: Callable[..., CommandResult]) -> Callable[..., CommandResult]:
            self._commands[name] = func
            # Index words for abbreviation matching
            words = name.split("-")
            self._command_words[name] = set(words)
            return func
        return decorator

    def get(self, name: str) -> Callable[..., CommandResult] | None:
        """Get a command by name or abbreviation."""
        # Exact match first
        if name in self._commands:
            return self._commands[name]

        # Try abbreviation matching
        matches = self._match_abbreviation(name)
        if len(matches) == 1:
            return self._commands[matches[0]]
        elif len(matches) > 1:
            raise ValueError(f"Ambiguous command '{name}': matches {matches}")

        return None

    def _match_abbreviation(self, abbrev: str) -> list[str]:
        """Match command abbreviation to full names."""
        abbrev_parts = abbrev.split("-")
        matches: list[str] = []

        for cmd_name in self._commands:
            cmd_parts = cmd_name.split("-")

            if len(abbrev_parts) > len(cmd_parts):
                continue

            # Check if each abbreviation part matches the start of command part
            match = True
            for i, abbrev_part in enumerate(abbrev_parts):
                if i >= len(cmd_parts) or not cmd_parts[i].startswith(abbrev_part):
                    match = False
                    break

            if match:
                matches.append(cmd_name)

        return matches

    def list_commands(self) -> list[str]:
        """List all registered command names."""
        return sorted(self._commands.keys())

    def execute(
        self, name: str, editor: CommandLineEditor, args: list[str] | None = None
    ) -> CommandResult:
        """Execute a command by name.

        Args:
            name: Command name or abbreviation
            editor: The editor instance
            args: Command arguments

        Returns:
            CommandResult
        """
        command = self.get(name)
        if command is None:
            return CommandResult(success=False, message=f"Unknown command: {name}")

        try:
            return command(editor, args or [])
        except Exception as e:
            return CommandResult(success=False, message=str(e))


# Global command registry
commands = CommandRegistry()


def parse_command_string(cmd_string: str) -> tuple[str, list[str]]:
    """Parse a command string into name and arguments.

    Args:
        cmd_string: Command string like "quit -p -y"

    Returns:
        Tuple of (command_name, arguments)
    """
    parts = shlex.split(cmd_string)
    if not parts:
        return "", []
    return parts[0], parts[1:]


# Navigation commands

@commands.register("move-char-left")
def move_char_left(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor one character left."""
    buffer = editor.buffer
    if buffer.cursor_position > 0:
        buffer.cursor_position -= 1
    return CommandResult()


@commands.register("move-char-right")
def move_char_right(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor one character right."""
    buffer = editor.buffer
    if buffer.cursor_position < len(buffer.text):
        buffer.cursor_position += 1
    return CommandResult()


@commands.register("move-word-left")
def move_word_left(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor one word left."""
    buffer = editor.buffer
    text = buffer.text
    pos = buffer.cursor_position

    # Skip whitespace
    while pos > 0 and text[pos - 1] in " \t":
        pos -= 1

    # Skip word characters
    while pos > 0 and text[pos - 1] not in " \t":
        pos -= 1

    buffer.cursor_position = pos
    return CommandResult()


@commands.register("move-word-right")
def move_word_right(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor one word right."""
    buffer = editor.buffer
    text = buffer.text
    pos = buffer.cursor_position
    length = len(text)

    # Skip current word characters
    while pos < length and text[pos] not in " \t":
        pos += 1

    # Skip whitespace
    while pos < length and text[pos] in " \t":
        pos += 1

    buffer.cursor_position = pos
    return CommandResult()


@commands.register("move-line-start")
def move_line_start(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor to start of line."""
    editor.buffer.cursor_position = 0
    return CommandResult()


@commands.register("move-line-end")
def move_line_end(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor to end of line."""
    editor.buffer.cursor_position = len(editor.buffer.text)
    return CommandResult()


@commands.register("move-param-next")
def move_param_next(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor to next parameter."""
    tokens = editor.get_tokens()
    pos = editor.buffer.cursor_position

    for token in tokens:
        if token.start > pos:
            editor.buffer.cursor_position = token.start
            return CommandResult()

    return CommandResult()


@commands.register("move-param-prev")
def move_param_prev(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor to previous parameter."""
    tokens = editor.get_tokens()
    pos = editor.buffer.cursor_position

    for token in reversed(tokens):
        if token.end <= pos:
            editor.buffer.cursor_position = token.start
            return CommandResult()

    return CommandResult()


@commands.register("move-param-equivalent")
def move_param_equivalent(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move cursor to next equivalent parameter (same category)."""
    # TODO: Implement using matcher
    return CommandResult()


# Deletion commands

@commands.register("delete-char")
def delete_char(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete character at cursor."""
    buffer = editor.buffer
    if buffer.cursor_position < len(buffer.text):
        buffer.delete()
    return CommandResult()


@commands.register("delete-char-left")
def delete_char_left(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete character before cursor."""
    buffer = editor.buffer
    if buffer.cursor_position > 0:
        buffer.delete_before_cursor()
    return CommandResult()


@commands.register("delete-word-left")
def delete_word_left(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete word before cursor."""
    buffer = editor.buffer
    text = buffer.text
    pos = buffer.cursor_position
    start_pos = pos

    # Skip whitespace
    while pos > 0 and text[pos - 1] in " \t":
        pos -= 1

    # Skip word characters
    while pos > 0 and text[pos - 1] not in " \t":
        pos -= 1

    # Delete from pos to start_pos
    if pos < start_pos:
        buffer.cursor_position = pos
        buffer.delete(count=start_pos - pos)

    return CommandResult()


@commands.register("delete-word-right")
def delete_word_right(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete word after cursor."""
    buffer = editor.buffer
    text = buffer.text
    pos = buffer.cursor_position
    length = len(text)
    end_pos = pos

    # Skip current word characters
    while end_pos < length and text[end_pos] not in " \t":
        end_pos += 1

    # Skip whitespace
    while end_pos < length and text[end_pos] in " \t":
        end_pos += 1

    # Delete from pos to end_pos
    if end_pos > pos:
        buffer.delete(count=end_pos - pos)

    return CommandResult()


@commands.register("delete-param")
def delete_param(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete current parameter."""
    tokens = editor.get_tokens()
    pos = editor.buffer.cursor_position

    for token in tokens:
        if token.start <= pos < token.end:
            # Found the token containing cursor
            editor.buffer.cursor_position = token.start
            # Delete token and trailing whitespace
            delete_len = token.end - token.start
            text = editor.buffer.text
            while token.start + delete_len < len(text) and text[token.start + delete_len] in " \t":
                delete_len += 1
            editor.buffer.delete(count=delete_len)
            return CommandResult()

    return CommandResult()


@commands.register("delete-to-end")
def delete_to_end(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete from cursor to end of line."""
    buffer = editor.buffer
    count = len(buffer.text) - buffer.cursor_position
    if count > 0:
        buffer.delete(count=count)
    return CommandResult()


@commands.register("delete-to-start")
def delete_to_start(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete from cursor to start of line."""
    buffer = editor.buffer
    count = buffer.cursor_position
    if count > 0:
        buffer.cursor_position = 0
        buffer.delete(count=count)
    return CommandResult()


# Editing commands

@commands.register("undo")
def undo(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Undo last change."""
    editor.buffer.undo()
    return CommandResult()


@commands.register("copy")
def copy(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Copy selection to clipboard."""
    # TODO: Implement selection handling
    return CommandResult()


@commands.register("cut")
def cut(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Cut selection to clipboard."""
    # TODO: Implement selection handling
    return CommandResult()


@commands.register("paste")
def paste(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Paste from clipboard."""
    editor.buffer.paste_clipboard_data(editor.app.clipboard.get_data())
    return CommandResult()


@commands.register("editor")
def open_editor(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Open external editor."""
    external_editor = os.environ.get("EDITOR", "vi")
    text = editor.buffer.text

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(text)
        temp_path = f.name

    try:
        subprocess.run([external_editor, temp_path], check=True)
        with open(temp_path) as f:
            new_text = f.read().strip()
        editor.buffer.text = new_text
    except subprocess.CalledProcessError:
        pass
    finally:
        os.unlink(temp_path)

    return CommandResult()


# Display commands

@commands.register("lights-off")
def lights_off(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Toggle lights-off mode."""
    category = args[0] if args else None
    editor.lexer.toggle_lights_off(category)
    return CommandResult()


@commands.register("show-duplicates")
def show_duplicates(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Enter duplicates mode."""
    editor.enter_duplicates_mode()
    return CommandResult()


# Exit commands

@commands.register("quit")
def quit_editor(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Quit the editor."""
    print_result = "-p" in args
    reset_first = "-r" in args
    _confirm = "-y" not in args  # TODO: Add confirmation if True and there are changes

    return CommandResult(
        exit_editor=True,
        print_result=print_result,
        reset_before_print=reset_first,
    )


# Duplicates mode commands

@commands.register("duplicate-prev")
def duplicate_prev(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move to previous duplicate in current group."""
    if editor.duplicates_mode:
        editor.duplicates_mode.move_prev()
    return CommandResult()


@commands.register("duplicate-next")
def duplicate_next(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move to next duplicate in current group."""
    if editor.duplicates_mode:
        editor.duplicates_mode.move_next()
    return CommandResult()


@commands.register("duplicate-previous-group")
def duplicate_previous_group(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move to previous duplicate group."""
    if editor.duplicates_mode:
        editor.duplicates_mode.prev_group()
    return CommandResult()


@commands.register("duplicate-next-group")
def duplicate_next_group(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move to next duplicate group."""
    if editor.duplicates_mode:
        editor.duplicates_mode.next_group()
    return CommandResult()


@commands.register("duplicate-select")
def duplicate_select(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Select current duplicate group."""
    if editor.duplicates_mode:
        editor.duplicates_mode.select_group()
    return CommandResult()


@commands.register("duplicate-deselect")
def duplicate_deselect(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Deselect current duplicate group."""
    if editor.duplicates_mode:
        editor.duplicates_mode.deselect_group()
    return CommandResult()


@commands.register("duplicate-all")
def duplicate_all(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Select all duplicate groups."""
    if editor.duplicates_mode:
        editor.duplicates_mode.select_all()
    return CommandResult()


@commands.register("duplicate-none")
def duplicate_none(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Deselect all duplicate groups."""
    if editor.duplicates_mode:
        editor.duplicates_mode.deselect_all()
    return CommandResult()


@commands.register("duplicates-keep")
def duplicates_keep(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Keep current duplicate, delete others in selected groups."""
    if editor.duplicates_mode:
        editor.duplicates_mode.keep_current()
    return CommandResult()


@commands.register("duplicates-delete")
def duplicates_delete(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Delete current duplicate."""
    if editor.duplicates_mode:
        editor.duplicates_mode.delete_current()
    return CommandResult()


@commands.register("duplicates-first")
def duplicates_first(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Keep first duplicate in selected groups."""
    if editor.duplicates_mode:
        editor.duplicates_mode.keep_first()
    return CommandResult()


@commands.register("duplicates-exit")
def duplicates_exit(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Exit duplicates mode."""
    editor.exit_duplicates_mode()
    return CommandResult()


# Flag operations

@commands.register("flags-join")
def flags_join(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Join selected flags together."""
    # TODO: Implement
    return CommandResult()


@commands.register("flags-move")
def flags_move(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Move selected flags left or right."""
    # TODO: Implement
    return CommandResult()


@commands.register("flags-sort")
def flags_sort(editor: CommandLineEditor, args: list[str]) -> CommandResult:
    """Sort selected flags."""
    # TODO: Implement
    return CommandResult()

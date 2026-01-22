"""Key binding management for the editor."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

from prompt_cli.editor.commands import commands, parse_command_string

if TYPE_CHECKING:
    from prompt_cli.config.schema import Config
    from prompt_cli.editor.prompt import CommandLineEditor


# Mapping of key names to prompt_toolkit Keys
KEY_MAPPING: dict[str, str | Keys] = {
    # Control keys
    "ctrl-a": Keys.ControlA,
    "ctrl-b": Keys.ControlB,
    "ctrl-c": Keys.ControlC,
    "ctrl-d": Keys.ControlD,
    "ctrl-e": Keys.ControlE,
    "ctrl-f": Keys.ControlF,
    "ctrl-g": Keys.ControlG,
    "ctrl-h": Keys.ControlH,
    "ctrl-i": Keys.ControlI,
    "ctrl-j": Keys.ControlJ,
    "ctrl-k": Keys.ControlK,
    "ctrl-l": Keys.ControlL,
    "ctrl-m": Keys.ControlM,
    "ctrl-n": Keys.ControlN,
    "ctrl-o": Keys.ControlO,
    "ctrl-p": Keys.ControlP,
    "ctrl-q": Keys.ControlQ,
    "ctrl-r": Keys.ControlR,
    "ctrl-s": Keys.ControlS,
    "ctrl-t": Keys.ControlT,
    "ctrl-u": Keys.ControlU,
    "ctrl-v": Keys.ControlV,
    "ctrl-w": Keys.ControlW,
    "ctrl-x": Keys.ControlX,
    "ctrl-y": Keys.ControlY,
    "ctrl-z": Keys.ControlZ,
    "ctrl-_": Keys.ControlUnderscore,
    "ctrl-\\": Keys.ControlBackslash,
    "ctrl-]": Keys.ControlSquareClose,
    "ctrl-^": Keys.ControlCircumflex,
    # Alt keys (escape sequences)
    "alt-a": (Keys.Escape, "a"),
    "alt-b": (Keys.Escape, "b"),
    "alt-c": (Keys.Escape, "c"),
    "alt-d": (Keys.Escape, "d"),
    "alt-e": (Keys.Escape, "e"),
    "alt-f": (Keys.Escape, "f"),
    "alt-g": (Keys.Escape, "g"),
    "alt-h": (Keys.Escape, "h"),
    "alt-i": (Keys.Escape, "i"),
    "alt-j": (Keys.Escape, "j"),
    "alt-k": (Keys.Escape, "k"),
    "alt-l": (Keys.Escape, "l"),
    "alt-m": (Keys.Escape, "m"),
    "alt-n": (Keys.Escape, "n"),
    "alt-o": (Keys.Escape, "o"),
    "alt-p": (Keys.Escape, "p"),
    "alt-q": (Keys.Escape, "q"),
    "alt-r": (Keys.Escape, "r"),
    "alt-s": (Keys.Escape, "s"),
    "alt-t": (Keys.Escape, "t"),
    "alt-u": (Keys.Escape, "u"),
    "alt-v": (Keys.Escape, "v"),
    "alt-w": (Keys.Escape, "w"),
    "alt-x": (Keys.Escape, "x"),
    "alt-y": (Keys.Escape, "y"),
    "alt-z": (Keys.Escape, "z"),
    "alt-backspace": (Keys.Escape, Keys.ControlH),
    # Special keys
    "enter": Keys.ControlM,
    "return": Keys.ControlM,
    "tab": Keys.ControlI,
    "backspace": Keys.ControlH,
    "delete": Keys.Delete,
    "escape": Keys.Escape,
    "up": Keys.Up,
    "down": Keys.Down,
    "left": Keys.Left,
    "right": Keys.Right,
    "home": Keys.Home,
    "end": Keys.End,
    "pageup": Keys.PageUp,
    "pagedown": Keys.PageDown,
    "insert": Keys.Insert,
    "space": " ",
    # Function keys
    "f1": Keys.F1,
    "f2": Keys.F2,
    "f3": Keys.F3,
    "f4": Keys.F4,
    "f5": Keys.F5,
    "f6": Keys.F6,
    "f7": Keys.F7,
    "f8": Keys.F8,
    "f9": Keys.F9,
    "f10": Keys.F10,
    "f11": Keys.F11,
    "f12": Keys.F12,
}


def parse_key_spec(key_spec: str) -> str | Keys | tuple[str | Keys, ...]:
    """Parse a key specification string to prompt_toolkit key.

    Args:
        key_spec: Key specification like "ctrl-a", "alt-b", "enter"

    Returns:
        prompt_toolkit key specification
    """
    key_lower = key_spec.lower()

    # Check direct mapping
    if key_lower in KEY_MAPPING:
        return KEY_MAPPING[key_lower]

    # Handle ctrl-shift combinations
    if key_lower.startswith("ctrl-shift-"):
        char = key_lower[11:]
        if len(char) == 1:
            # ctrl-shift-x is often the same as ctrl-X (uppercase)
            return getattr(Keys, f"Control{char.upper()}", key_spec)

    # Handle single character keys
    if len(key_spec) == 1:
        return key_spec

    return key_spec


class KeyBindingManager:
    """Manages key bindings for different modes."""

    def __init__(self, config: Config, editor: CommandLineEditor) -> None:
        """Initialize key binding manager.

        Args:
            config: Configuration with keybindings
            editor: The editor instance
        """
        self.config = config
        self.editor = editor
        self._bindings: dict[str, KeyBindings] = {}

        # Create bindings for each mode
        self._create_mode_bindings("normal")
        self._create_mode_bindings("duplicates")
        self._create_mode_bindings("configure")

    def _create_mode_bindings(self, mode: str) -> None:
        """Create key bindings for a mode."""
        kb = KeyBindings()
        self._bindings[mode] = kb

        # Get keybindings from config
        mode_bindings = self.config.keybindings.get(mode, {})

        for key_spec, command_str in mode_bindings.items():
            self._bind_key(kb, key_spec, command_str)

    def _bind_key(self, kb: KeyBindings, key_spec: str, command_str: str) -> None:
        """Bind a key to a command.

        Args:
            kb: KeyBindings object
            key_spec: Key specification
            command_str: Command string (possibly with args)
        """
        key = parse_key_spec(key_spec)

        # Resolve command alias
        command_str = self._resolve_alias(command_str)

        # Parse command and args
        cmd_name, cmd_args = parse_command_string(command_str)

        # Create the handler
        def make_handler(name: str, args: list[str]) -> Callable:
            def handler(event) -> None:  # type: ignore
                result = commands.execute(name, self.editor, args)
                if result.exit_editor:
                    self.editor.should_exit = True
                    self.editor.exit_print = result.print_result
                    self.editor.exit_reset = result.reset_before_print
                    event.app.exit()

            return handler

        # Handle different key types
        if isinstance(key, tuple):
            # Multi-key sequence (like alt-x)
            kb.add(*key)(make_handler(cmd_name, cmd_args))
        else:
            kb.add(key)(make_handler(cmd_name, cmd_args))

    def _resolve_alias(self, command_str: str) -> str:
        """Resolve command alias to full command."""
        parts = command_str.split(None, 1)
        if not parts:
            return command_str

        cmd_name = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        # Check aliases
        if cmd_name in self.config.aliases:
            resolved = self.config.aliases[cmd_name]
            if rest:
                return f"{resolved} {rest}"
            return resolved

        return command_str

    def get_bindings(self, mode: str) -> KeyBindings:
        """Get key bindings for a mode.

        Args:
            mode: Mode name

        Returns:
            KeyBindings object
        """
        return self._bindings.get(mode, KeyBindings())

    def merge_bindings(self, *modes: str) -> KeyBindings:
        """Merge key bindings from multiple modes.

        Args:
            modes: Mode names to merge

        Returns:
            Merged KeyBindings object
        """
        merged = KeyBindings()

        for mode in modes:
            if mode in self._bindings:
                merged = merged.merge(self._bindings[mode])

        return merged

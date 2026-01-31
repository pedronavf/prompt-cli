"""Main prompt editor using prompt_toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.clipboard import InMemoryClipboard
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.styles import Style

from prompt_cli.config.loader import load_config
from prompt_cli.config.schema import Config
from prompt_cli.core.matcher import MatchResult
from prompt_cli.core.tokenizer import Token, tokenize
from prompt_cli.editor.completer import CommandLineCompleter
from prompt_cli.editor.keybindings import KeyBindingManager
from prompt_cli.editor.lexer import CommandLineLexer
from prompt_cli.editor.modes.duplicates import DuplicatesMode

if TYPE_CHECKING:
    pass


class CommandLineEditor:
    """Interactive command line editor with syntax highlighting."""

    def __init__(
        self,
        command_line: str,
        config: Config | None = None,
        theme: str | None = None,
    ) -> None:
        """Initialize the editor.

        Args:
            command_line: The command line to edit
            config: Configuration object (loads default if None)
            theme: Theme name to use
        """
        self.config = config or load_config()
        self.theme = self.config.get_theme(theme)

        # Parse initial command line
        self._initial_text = command_line
        tokens = tokenize(command_line)
        self._executable = tokens[0].value if tokens else None

        # Create lexer (pass self for duplicates mode awareness)
        self.lexer = CommandLineLexer(
            config=self.config,
            theme=self.theme,
            executable=self._executable,
            editor=self,
        )

        # Create completer
        self.completer = CommandLineCompleter(
            config=self.config,
            matcher=self.lexer.matcher,
        )

        # Create buffer with completer
        self.buffer = Buffer(
            document=Document(command_line),
            multiline=False,
            name="command",
            completer=self.completer,
            complete_while_typing=False,  # Only complete on Tab
        )

        # Create key binding manager
        self._kb_manager: KeyBindingManager | None = None

        # Mode state
        self._mode = "normal"
        self.duplicates_mode: DuplicatesMode | None = None

        # Exit state
        self.should_exit = False
        self.exit_print = False
        self.exit_reset = False

        # Application (created in run())
        self.app: Application | None = None

    def _create_keybindings(self) -> KeyBindings:
        """Create key bindings for the editor."""
        self._kb_manager = KeyBindingManager(self.config, self)

        # Start with normal mode bindings
        return self._kb_manager.get_bindings(self._mode)

    def _create_style(self) -> Style:
        """Create prompt_toolkit style from theme."""
        style_dict = self.lexer.get_style_dict()
        return Style.from_dict(style_dict)

    def _create_layout(self) -> Layout:
        """Create the editor layout."""
        control = BufferControl(
            buffer=self.buffer,
            lexer=self.lexer,
        )
        window = Window(content=control)
        return Layout(window)

    def run(self) -> str:
        """Run the editor and return the edited command line.

        Returns:
            The edited command line
        """
        # Create application
        self.app = Application(
            layout=self._create_layout(),
            key_bindings=self._create_keybindings(),
            style=self._create_style(),
            clipboard=InMemoryClipboard(),
            full_screen=False,
            mouse_support=False,
        )

        # Run the application
        self.app.run()

        # Get result based on exit state
        if self.exit_reset:
            return self._initial_text
        return self.buffer.text

    def get_tokens(self) -> list[Token]:
        """Get current tokens from buffer."""
        return tokenize(self.buffer.text)

    def get_match_results(self) -> list[MatchResult]:
        """Get match results for current tokens."""
        tokens = self.get_tokens()
        return self.lexer.matcher.match_tokens(tokens)

    def enter_duplicates_mode(self) -> None:
        """Enter duplicates mode."""
        results = self.get_match_results()
        duplicates = self.lexer.matcher.find_duplicates(results)

        if not duplicates:
            return  # No duplicates to show

        self.duplicates_mode = DuplicatesMode(self, duplicates)
        self._mode = "duplicates"
        self._update_keybindings()

    def exit_duplicates_mode(self) -> None:
        """Exit duplicates mode."""
        self.duplicates_mode = None
        self._mode = "normal"
        self._update_keybindings()

    def _update_keybindings(self) -> None:
        """Update key bindings for current mode."""
        if self.app and self._kb_manager:
            new_bindings = self._kb_manager.get_bindings(self._mode)
            self.app.key_bindings = new_bindings


def edit_command_line(
    command_line: str,
    config: Config | None = None,
    theme: str | None = None,
) -> str:
    """Edit a command line interactively.

    Args:
        command_line: The command line to edit
        config: Configuration object
        theme: Theme name

    Returns:
        The edited command line
    """
    editor = CommandLineEditor(command_line, config, theme)
    return editor.run()

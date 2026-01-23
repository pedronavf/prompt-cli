"""Command line completer using validators."""

from __future__ import annotations

import os
from collections.abc import Iterable
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from prompt_cli.core.matcher import Matcher, MatchResult
from prompt_cli.core.tokenizer import Token, tokenize
from prompt_cli.validators.base import Validator
from prompt_cli.validators.choice import ChoiceValidator, MultipleChoiceValidator
from prompt_cli.validators.custom import CustomValidator
from prompt_cli.validators.file import DirectoryValidator, FileValidator
from prompt_cli.validators.warnings import WarningsValidator

if TYPE_CHECKING:
    from prompt_cli.config.schema import Config


def create_validator(config: dict | None) -> Validator | None:
    """Create a validator instance from configuration."""
    if config is None:
        return None

    validator_type = config.get("type", "file")

    match validator_type:
        case "file":
            return FileValidator(config)
        case "directory":
            return DirectoryValidator(config)
        case "choice":
            return ChoiceValidator(config)
        case "multiple-choice":
            return MultipleChoiceValidator(config)
        case "warnings":
            return WarningsValidator(config)
        case "custom":
            return CustomValidator(config)
        case _:
            return None


class CommandLineCompleter(Completer):
    """Completer for command line flags using validators."""

    def __init__(self, config: Config, matcher: Matcher) -> None:
        """Initialize completer.

        Args:
            config: Configuration object
            matcher: Matcher for determining flag categories
        """
        self.config = config
        self.matcher = matcher
        self._default_validator = self._create_default_validator()

    def _create_default_validator(self) -> Validator | None:
        """Create the default validator from config."""
        default_config = self.config.config.default_validator
        if default_config:
            return create_validator(default_config)
        # Default to file validator if nothing configured
        return FileValidator({"type": "file"})

    def get_completions(
        self, document: Document, complete_event
    ) -> Iterable[Completion]:
        """Get completions for the current cursor position.

        Args:
            document: The document being edited
            complete_event: The completion event

        Yields:
            Completion objects
        """
        text = document.text
        cursor_pos = document.cursor_position

        # Tokenize the command line
        tokens = tokenize(text)

        if not tokens:
            # Empty line - complete with files (default)
            yield from self._complete_with_validator(
                self._default_validator, "", cursor_pos
            )
            return

        # Find which token the cursor is in or after
        current_token, token_index = self._find_token_at_cursor(tokens, cursor_pos)

        if current_token is None:
            # Cursor is after all tokens (in whitespace)
            # Complete with default validator (usually files)
            # Get the partial text after the last token
            if tokens:
                last_end = tokens[-1].end
                partial = text[last_end:cursor_pos].strip()
            else:
                partial = ""

            yield from self._complete_with_validator(
                self._default_validator, partial, cursor_pos - len(partial)
            )
            return

        # Get the match result for this token
        if token_index == 0:
            # First token is executable - complete with PATH executables
            yield from self._complete_executables(current_token.value, current_token.start)
            return

        result = self.matcher.match_token(current_token)

        # Get validator for this flag
        validator = self._get_validator_for_result(result)

        if validator is None:
            validator = self._default_validator

        # Determine what part of the token to complete
        partial, start_pos = self._get_completion_context(current_token, result, cursor_pos)

        yield from self._complete_with_validator(validator, partial, start_pos)

    def _find_token_at_cursor(
        self, tokens: list[Token], cursor_pos: int
    ) -> tuple[Token | None, int]:
        """Find the token at or before the cursor position.

        Returns:
            Tuple of (token, index) or (None, -1) if cursor is after all tokens
        """
        for i, token in enumerate(tokens):
            # Cursor is within this token
            if token.start <= cursor_pos <= token.end:
                return token, i

            # Cursor is between this token and the next
            if token.end < cursor_pos:
                if i + 1 < len(tokens) and tokens[i + 1].start > cursor_pos:
                    # In whitespace between tokens - return None to trigger default
                    return None, -1

        # Cursor is after all tokens
        return None, -1

    def _get_validator_for_result(self, result: MatchResult) -> Validator | None:
        """Get the validator for a match result."""
        if result.flag and result.flag.validator:
            return create_validator(result.flag.validator)
        return None

    def _get_completion_context(
        self, token: Token, result: MatchResult, cursor_pos: int
    ) -> tuple[str, int]:
        """Determine what part of the token to complete.

        For flags like -I/tmp/foo, we want to complete the /tmp/foo part.

        Returns:
            Tuple of (partial_text, start_position)
        """
        # If we have capture groups, find which one the cursor is in
        if result.groups and len(result.groups) > 1:
            # The last group is typically the value
            last_group = result.groups[-1]
            value_start = token.start + last_group.start
            value_end = token.start + last_group.end

            if value_start <= cursor_pos <= value_end:
                # Cursor is in the value part
                partial = token.value[last_group.start:cursor_pos - token.start]
                return partial, value_start

        # Default: complete from token start
        partial = token.value[:cursor_pos - token.start]
        return partial, token.start

    def _complete_with_validator(
        self, validator: Validator | None, partial: str, start_pos: int
    ) -> Iterable[Completion]:
        """Generate completions using a validator.

        Args:
            validator: The validator to use
            partial: Partial text to complete
            start_pos: Start position of the completion

        Yields:
            Completion objects
        """
        if validator is None:
            return

        context = {"cwd": os.getcwd()}
        result = validator.get_completions(partial, context)

        for completion in result.completions:
            # Calculate how much text to replace
            display = completion
            # If completion starts with partial, show just the new part
            if completion.lower().startswith(partial.lower()):
                text = completion
            else:
                text = completion

            yield Completion(
                text=text,
                start_position=-len(partial),
                display=display,
            )

    def _complete_executables(
        self, partial: str, start_pos: int
    ) -> Iterable[Completion]:
        """Complete executable names from PATH.

        Args:
            partial: Partial executable name
            start_pos: Start position

        Yields:
            Completion objects for executables
        """
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        seen: set[str] = set()

        for path_dir in path_dirs:
            if not os.path.isdir(path_dir):
                continue

            try:
                for entry in os.scandir(path_dir):
                    if not entry.is_file():
                        continue

                    name = entry.name
                    if name in seen:
                        continue

                    if partial and not name.lower().startswith(partial.lower()):
                        continue

                    # Check if executable
                    if os.access(entry.path, os.X_OK):
                        seen.add(name)
                        yield Completion(
                            text=name,
                            start_position=-len(partial),
                            display=name,
                        )
            except OSError:
                continue

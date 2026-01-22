"""Command line tokenizer with quote-aware parsing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class QuoteType(Enum):
    """Type of quoting for a token."""

    NONE = auto()
    SINGLE = auto()
    DOUBLE = auto()


@dataclass
class Token:
    """A token from the command line.

    Attributes:
        value: The token value (without quotes if quoted)
        start: Start position in original string
        end: End position in original string (exclusive)
        quote_type: Type of quoting used
        raw: The raw token including quotes
    """

    value: str
    start: int
    end: int
    quote_type: QuoteType = QuoteType.NONE
    raw: str = ""

    def __post_init__(self) -> None:
        if not self.raw:
            self.raw = self.value

    @property
    def is_quoted(self) -> bool:
        """Check if token was quoted."""
        return self.quote_type != QuoteType.NONE

    @property
    def length(self) -> int:
        """Length of the token in the original string."""
        return self.end - self.start


class Tokenizer:
    """Tokenizer for command lines with quote handling."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.length = len(text)

    def tokenize(self) -> list[Token]:
        """Tokenize the command line into tokens."""
        tokens: list[Token] = []

        while self.pos < self.length:
            # Skip whitespace
            self._skip_whitespace()
            if self.pos >= self.length:
                break

            # Parse next token
            token = self._parse_token()
            if token:
                tokens.append(token)

        return tokens

    def _skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while self.pos < self.length and self.text[self.pos] in " \t":
            self.pos += 1

    def _parse_token(self) -> Token | None:
        """Parse a single token."""
        if self.pos >= self.length:
            return None

        start = self.pos
        char = self.text[self.pos]

        # Handle quoted strings
        if char in "\"'":
            return self._parse_quoted(start, char)

        # Handle unquoted token (may contain embedded quotes)
        return self._parse_unquoted(start)

    def _parse_quoted(self, start: int, quote_char: str) -> Token:
        """Parse a quoted string."""
        self.pos += 1  # Skip opening quote
        value_parts: list[str] = []

        while self.pos < self.length:
            char = self.text[self.pos]

            if char == "\\":
                # Handle escape sequences
                if self.pos + 1 < self.length:
                    next_char = self.text[self.pos + 1]
                    if next_char in (quote_char, "\\"):
                        value_parts.append(next_char)
                        self.pos += 2
                        continue
                value_parts.append(char)
                self.pos += 1
            elif char == quote_char:
                # End of quoted string
                self.pos += 1
                break
            else:
                value_parts.append(char)
                self.pos += 1

        value = "".join(value_parts)
        raw = self.text[start : self.pos]
        quote_type = QuoteType.DOUBLE if quote_char == '"' else QuoteType.SINGLE

        return Token(
            value=value,
            start=start,
            end=self.pos,
            quote_type=quote_type,
            raw=raw,
        )

    def _parse_unquoted(self, start: int) -> Token:
        """Parse an unquoted token (may contain embedded quoted sections)."""
        value_parts: list[str] = []
        has_embedded_quote = False

        while self.pos < self.length:
            char = self.text[self.pos]

            if char in " \t":
                # End of token at whitespace
                break

            if char == "\\":
                # Handle escape sequences
                if self.pos + 1 < self.length:
                    next_char = self.text[self.pos + 1]
                    if next_char in " \t\\'\"":
                        value_parts.append(next_char)
                        self.pos += 2
                        continue
                value_parts.append(char)
                self.pos += 1

            elif char in "\"'":
                # Handle embedded quoted section (e.g., -fname="value")
                has_embedded_quote = True
                quote_char = char
                self.pos += 1  # Skip opening quote

                while self.pos < self.length:
                    inner_char = self.text[self.pos]
                    if inner_char == "\\":
                        if self.pos + 1 < self.length:
                            next_char = self.text[self.pos + 1]
                            if next_char in (quote_char, "\\"):
                                value_parts.append(next_char)
                                self.pos += 2
                                continue
                        value_parts.append(inner_char)
                        self.pos += 1
                    elif inner_char == quote_char:
                        self.pos += 1  # Skip closing quote
                        break
                    else:
                        value_parts.append(inner_char)
                        self.pos += 1
            else:
                value_parts.append(char)
                self.pos += 1

        value = "".join(value_parts)
        raw = self.text[start : self.pos]

        # Determine quote type based on content
        quote_type = QuoteType.NONE
        if has_embedded_quote:
            # Check which quote type was used
            if '"' in raw:
                quote_type = QuoteType.DOUBLE
            elif "'" in raw:
                quote_type = QuoteType.SINGLE

        return Token(
            value=value,
            start=start,
            end=self.pos,
            quote_type=quote_type,
            raw=raw,
        )


def tokenize(text: str) -> list[Token]:
    """Tokenize a command line string.

    Args:
        text: The command line string to tokenize

    Returns:
        List of Token objects

    Examples:
        >>> tokens = tokenize('gcc -I/tmp/foo -o test main.c')
        >>> [t.value for t in tokens]
        ['gcc', '-I/tmp/foo', '-o', 'test', 'main.c']

        >>> tokens = tokenize('gcc -DNAME="hello world" main.c')
        >>> [t.value for t in tokens]
        ['gcc', '-DNAME=hello world', 'main.c']
    """
    return Tokenizer(text).tokenize()


def detokenize(tokens: list[Token]) -> str:
    """Convert tokens back to a command line string.

    Uses the raw representation of each token to preserve original quoting.

    Args:
        tokens: List of Token objects

    Returns:
        Command line string
    """
    return " ".join(token.raw for token in tokens)


def rebuild_command(tokens: list[Token]) -> str:
    """Rebuild command line from tokens, applying minimal quoting.

    Args:
        tokens: List of Token objects

    Returns:
        Command line string with proper quoting
    """
    parts: list[str] = []

    for token in tokens:
        if needs_quoting(token.value):
            # Quote the value
            if '"' not in token.value:
                parts.append(f'"{token.value}"')
            elif "'" not in token.value:
                parts.append(f"'{token.value}'")
            else:
                # Escape double quotes
                escaped = token.value.replace("\\", "\\\\").replace('"', '\\"')
                parts.append(f'"{escaped}"')
        else:
            parts.append(token.value)

    return " ".join(parts)


def needs_quoting(value: str) -> bool:
    """Check if a value needs quoting."""
    if not value:
        return True
    special_chars = set(" \t\n\r\"'\\$`!|&;()<>")
    return any(c in special_chars for c in value)

"""Core functionality: tokenizer, matcher, and color engine."""

from prompt_cli.core.color import ColorParser, combine_colors, parse_color
from prompt_cli.core.matcher import Matcher, MatchResult
from prompt_cli.core.tokenizer import Token, tokenize

__all__ = [
    "Token",
    "tokenize",
    "Matcher",
    "MatchResult",
    "ColorParser",
    "parse_color",
    "combine_colors",
]

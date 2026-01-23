"""Regex-based token matching and category assignment."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from prompt_cli.core.programs import ProgramMatch, detect_program

if TYPE_CHECKING:
    from prompt_cli.config.schema import Config, Flag
    from prompt_cli.core.tokenizer import Token


@dataclass
class CaptureGroup:
    """A captured group from a regex match."""

    value: str
    start: int  # Relative to token start
    end: int  # Relative to token start
    group_index: int


@dataclass
class MatchResult:
    """Result of matching a token against flag patterns."""

    token: Token
    category: str
    flag: Flag | None = None
    groups: list[CaptureGroup] = field(default_factory=list)
    matched: bool = False

    @property
    def is_default(self) -> bool:
        """Check if this token fell through to default category."""
        return self.category.lower() == "default"


class Matcher:
    """Matches tokens against flag patterns and assigns categories."""

    def __init__(self, config: Config, executable: str | None = None) -> None:
        """Initialize matcher with configuration.

        Args:
            config: The configuration object
            executable: The executable name (first token) for program-specific matching
        """
        self.config = config
        self.executable = executable

        # Detect program using two-tier matching
        self.program_match: ProgramMatch | None = None
        if executable:
            self.program_match = detect_program(executable, config)

        self._compiled_patterns: dict[str, list[tuple[re.Pattern[str], Flag]]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns from flags."""
        # Use canonical program name if detected
        program_name = ""
        if self.program_match:
            program_name = self.program_match.canonical_name
        flags = self.config.get_flags_for_program(program_name)

        for flag in flags:
            category = flag.category.lower()
            if category not in self._compiled_patterns:
                self._compiled_patterns[category] = []

            for pattern_str in flag.regexps:
                try:
                    pattern = re.compile(f"^{pattern_str}$")
                    self._compiled_patterns[category].append((pattern, flag))
                except re.error as e:
                    # Log warning but continue
                    print(f"Warning: Invalid regex pattern '{pattern_str}': {e}")

    def match_token(self, token: Token) -> MatchResult:
        """Match a single token against all patterns.

        Args:
            token: The token to match

        Returns:
            MatchResult with category and captured groups
        """
        for _category, patterns in self._compiled_patterns.items():
            for pattern, flag in patterns:
                match = pattern.match(token.value)
                if match:
                    groups = self._extract_groups(match, token)
                    return MatchResult(
                        token=token,
                        category=flag.category,  # Use original case from flag
                        flag=flag,
                        groups=groups,
                        matched=True,
                    )

        # No match - use default category
        return MatchResult(
            token=token,
            category="Default",
            flag=None,
            groups=[
                CaptureGroup(
                    value=token.value,
                    start=0,
                    end=len(token.value),
                    group_index=0,
                )
            ],
            matched=False,
        )

    def _extract_groups(self, match: re.Match[str], token: Token) -> list[CaptureGroup]:
        """Extract capture groups from a regex match."""
        groups: list[CaptureGroup] = []

        # Group 0 is the entire match
        for i, group_value in enumerate(match.groups(), start=1):
            if group_value is not None:
                start = match.start(i)
                end = match.end(i)
                groups.append(
                    CaptureGroup(
                        value=group_value,
                        start=start,
                        end=end,
                        group_index=i,
                    )
                )

        # If no capture groups, treat the whole match as group 0
        if not groups:
            groups.append(
                CaptureGroup(
                    value=token.value,
                    start=0,
                    end=len(token.value),
                    group_index=0,
                )
            )

        return groups

    def match_tokens(self, tokens: list[Token]) -> list[MatchResult]:
        """Match all tokens.

        Args:
            tokens: List of tokens to match

        Returns:
            List of MatchResult objects
        """
        results: list[MatchResult] = []

        for i, token in enumerate(tokens):
            if i == 0:
                # First token is the executable - special category
                results.append(
                    MatchResult(
                        token=token,
                        category="Executable",
                        flag=None,
                        groups=[
                            CaptureGroup(
                                value=token.value,
                                start=0,
                                end=len(token.value),
                                group_index=0,
                            )
                        ],
                        matched=True,
                    )
                )
            else:
                results.append(self.match_token(token))

        return results

    def get_category_for_token(self, token: Token) -> str:
        """Get just the category name for a token."""
        return self.match_token(token).category

    def find_duplicates(self, results: list[MatchResult]) -> dict[str, list[int]]:
        """Find duplicate flags in match results.

        Args:
            results: List of match results

        Returns:
            Dict mapping category to list of indices with duplicates
        """
        category_indices: dict[str, list[int]] = {}

        for i, result in enumerate(results):
            if result.matched and result.flag:
                category = result.category
                if category not in category_indices:
                    category_indices[category] = []
                category_indices[category].append(i)

        # Filter to only categories with duplicates
        return {cat: indices for cat, indices in category_indices.items() if len(indices) > 1}

    def get_equivalent_indices(
        self, results: list[MatchResult], current_index: int
    ) -> list[int]:
        """Get indices of tokens in the same category as the current token.

        Args:
            results: List of match results
            current_index: Index of current token

        Returns:
            List of indices (including current_index) in same category
        """
        if current_index < 0 or current_index >= len(results):
            return []

        current_category = results[current_index].category
        return [
            i
            for i, result in enumerate(results)
            if result.category == current_category
        ]


def expand_category_map(
    config: Config, category: str, level: int | None = None
) -> list[str]:
    """Expand a category or category map to its constituent categories.

    Args:
        config: The configuration object
        category: Category or category map name
        level: Expansion level (None = fully expand, 0 = no expansion)

    Returns:
        List of category names
    """
    category_lower = category.lower()

    # Check if it's a category map
    if category_lower in config.category_maps:
        if level == 0:
            return [category]

        cat_map = config.category_maps[category_lower]
        result: list[str] = []

        for cat in cat_map.categories:
            # Recursively expand
            new_level = level - 1 if level is not None else None
            result.extend(expand_category_map(config, cat, new_level))

        return result

    # It's a regular category
    return [category]

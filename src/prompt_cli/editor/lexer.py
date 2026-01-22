"""Custom lexer for command line syntax highlighting."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer

from prompt_cli.core.color import ColorParser, get_colors_for_groups
from prompt_cli.core.matcher import Matcher, MatchResult
from prompt_cli.core.tokenizer import tokenize

if TYPE_CHECKING:
    from prompt_cli.config.schema import Config, Theme


class CommandLineLexer(Lexer):
    """Lexer for command line syntax highlighting based on configuration."""

    def __init__(
        self,
        config: Config,
        theme: Theme | None = None,
        executable: str | None = None,
    ) -> None:
        """Initialize the lexer.

        Args:
            config: Configuration object
            theme: Theme to use for colors
            executable: Executable name for program-specific matching
        """
        self.config = config
        self.theme = theme or config.get_theme()
        self.executable = executable
        self.matcher = Matcher(config, executable)
        self.color_parser = ColorParser()

        # Lights-off mode state
        self.lights_off = False
        self.lights_off_category: str | None = None

        # Build style dict for prompt_toolkit
        self._styles = self._build_styles()

    def _build_styles(self) -> dict[str, str]:
        """Build prompt_toolkit style dictionary from theme."""
        styles: dict[str, str] = {}

        # Add category styles
        for category_name, color_spec in self.theme.categories.items():
            style_class = self._category_to_class(category_name)
            parsed = self.color_parser.parse(color_spec)
            styles[style_class] = parsed.to_prompt_toolkit_style()

        # Add default style
        if self.theme.default:
            parsed = self.color_parser.parse(self.theme.default)
            styles["class:default"] = parsed.to_prompt_toolkit_style()

        return styles

    def _category_to_class(self, category: str) -> str:
        """Convert category name to style class name."""
        # Replace special characters and normalize
        class_name = category.lower().replace(":", "-").replace(" ", "-")
        return f"class:{class_name}"

    def get_style_dict(self) -> dict[str, str]:
        """Get the style dictionary for prompt_toolkit."""
        return self._styles

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        """Lex a document and return a function that returns styled text for each line.

        Args:
            document: The document to lex

        Returns:
            Function that takes a line number and returns styled text tuples
        """
        # Tokenize and match the entire document
        text = document.text
        tokens = tokenize(text)

        # Set executable from first token if not set
        if not self.executable and tokens:
            self.matcher = Matcher(self.config, tokens[0].value)

        # Match all tokens
        results = self.matcher.match_tokens(tokens)

        # Build styled text for each token
        styled_tokens = self._style_results(results, text)

        def get_line(line_number: int) -> StyleAndTextTuples:
            """Get styled text for a specific line."""
            # For single-line input, return all styled tokens
            if line_number == 0:
                return styled_tokens
            return []

        return get_line

    def _style_results(
        self, results: list[MatchResult], original_text: str
    ) -> StyleAndTextTuples:
        """Convert match results to styled text tuples."""
        styled: StyleAndTextTuples = []
        last_end = 0

        for result in results:
            token = result.token

            # Add any whitespace before this token
            if token.start > last_end:
                whitespace = original_text[last_end : token.start]
                styled.append(("", whitespace))

            # Get style for this token's category
            category = result.category

            # Check lights-off mode
            if self.lights_off:
                if self.lights_off_category:
                    # Only highlight matching category
                    if category.lower() != self.lights_off_category.lower():
                        category = "ui:lights-off-dim"
                else:
                    # Dim everything except current token
                    pass  # TODO: implement cursor position tracking

            # Style the token based on capture groups
            if result.groups:
                # Get colors for this category
                cat_lower = category.lower()
                if cat_lower in self.config.categories:
                    cat_colors = self.config.categories[cat_lower].colors
                else:
                    cat_colors = [self.theme.categories.get(category, self.theme.default)]

                colors = get_colors_for_groups(cat_colors, len(result.groups))

                # Build styled text for each group
                token_styled = self._style_groups(token.value, result.groups, colors, category)
                styled.extend(token_styled)
            else:
                # No groups, style entire token
                style_class = self._category_to_class(category)
                styled.append((style_class, token.raw))

            last_end = token.end

        # Add any trailing text
        if last_end < len(original_text):
            styled.append(("", original_text[last_end:]))

        return styled

    def _style_groups(
        self,
        token_value: str,
        groups: list,
        colors: list,
        category: str,
    ) -> StyleAndTextTuples:
        """Style a token based on capture groups."""
        styled: StyleAndTextTuples = []

        # Sort groups by start position
        sorted_groups = sorted(groups, key=lambda g: g.start)

        last_pos = 0
        for i, group in enumerate(sorted_groups):
            # Add any text before this group
            if group.start > last_pos:
                prefix = token_value[last_pos : group.start]
                style_class = self._category_to_class(category)
                styled.append((style_class, prefix))

            # Style the group
            color = colors[min(i, len(colors) - 1)]
            style_str = color.to_prompt_toolkit_style()
            styled.append((style_str, group.value))

            last_pos = group.end

        # Add any text after the last group
        if last_pos < len(token_value):
            suffix = token_value[last_pos:]
            style_class = self._category_to_class(category)
            styled.append((style_class, suffix))

        return styled

    def set_lights_off(self, enabled: bool, category: str | None = None) -> None:
        """Set lights-off mode.

        Args:
            enabled: Whether to enable lights-off mode
            category: Category to highlight (None for current token's category)
        """
        self.lights_off = enabled
        self.lights_off_category = category

    def toggle_lights_off(self, category: str | None = None) -> None:
        """Toggle lights-off mode."""
        if self.lights_off and self.lights_off_category == category:
            self.lights_off = False
            self.lights_off_category = None
        else:
            self.lights_off = True
            self.lights_off_category = category

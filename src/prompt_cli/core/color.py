"""ANSI color parsing and manipulation."""

from __future__ import annotations

from dataclasses import dataclass

# Standard ANSI color names
COLORS = {
    "black": 0,
    "red": 1,
    "green": 2,
    "yellow": 3,
    "blue": 4,
    "magenta": 5,
    "cyan": 6,
    "white": 7,
}

# Bright color variants
BRIGHT_COLORS = {
    "bright black": 8,
    "bright red": 9,
    "bright green": 10,
    "bright yellow": 11,
    "bright blue": 12,
    "bright magenta": 13,
    "bright cyan": 14,
    "bright white": 15,
    # Aliases
    "gray": 8,
    "grey": 8,
}

# Text attributes
ATTRIBUTES = {
    "bold": 1,
    "dim": 2,
    "italic": 3,
    "underline": 4,
    "blink": 5,
    "reverse": 7,
    "inverse": 7,
    "hidden": 8,
    "strikethrough": 9,
}


@dataclass
class ParsedColor:
    """Parsed color specification.

    Attributes:
        fg: Foreground color (color name, number, or None)
        bg: Background color (color name, number, or None)
        bold: Bold attribute
        dim: Dim attribute
        italic: Italic attribute
        underline: Underline attribute
        blink: Blink attribute
        reverse: Reverse/inverse attribute
        hidden: Hidden attribute
        strikethrough: Strikethrough attribute
        combine: Whether this is a combining color (+prefix)
    """

    fg: str | int | None = None
    bg: str | int | None = None
    bold: bool | None = None
    dim: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    blink: bool | None = None
    reverse: bool | None = None
    hidden: bool | None = None
    strikethrough: bool | None = None
    combine: bool = False

    def to_ansi(self) -> str:
        """Convert to ANSI escape sequence."""
        codes: list[int] = []

        # Reset first if not combining
        if not self.combine:
            codes.append(0)

        # Attributes
        if self.bold:
            codes.append(1)
        if self.dim:
            codes.append(2)
        if self.italic:
            codes.append(3)
        if self.underline:
            codes.append(4)
        if self.blink:
            codes.append(5)
        if self.reverse:
            codes.append(7)
        if self.hidden:
            codes.append(8)
        if self.strikethrough:
            codes.append(9)

        # Foreground color
        if self.fg is not None:
            fg_code = self._color_to_code(self.fg, foreground=True)
            if fg_code is not None:
                codes.append(fg_code)

        # Background color
        if self.bg is not None:
            bg_code = self._color_to_code(self.bg, foreground=False)
            if bg_code is not None:
                codes.append(bg_code)

        if not codes:
            return ""

        return f"\033[{';'.join(str(c) for c in codes)}m"

    def _color_to_code(self, color: str | int, foreground: bool) -> int | None:
        """Convert color to ANSI code."""
        base = 30 if foreground else 40

        if isinstance(color, int):
            if 0 <= color <= 7:
                return base + color
            elif 8 <= color <= 15:
                return (90 if foreground else 100) + (color - 8)
            else:
                # 256 color - need different format
                return None  # TODO: implement 256 color support

        color_lower = color.lower()

        if color_lower in COLORS:
            return base + COLORS[color_lower]

        if color_lower in BRIGHT_COLORS:
            bright_base = 90 if foreground else 100
            color_num = BRIGHT_COLORS[color_lower]
            if color_num >= 8:
                return bright_base + (color_num - 8)
            return base + color_num

        # Check for "bright <color>" format
        if color_lower.startswith("bright "):
            base_color = color_lower[7:]
            if base_color in COLORS:
                bright_base = 90 if foreground else 100
                return bright_base + COLORS[base_color]

        return None

    def to_prompt_toolkit_style(self) -> str:
        """Convert to prompt_toolkit style string."""
        parts: list[str] = []

        if self.bold:
            parts.append("bold")
        if self.dim:
            parts.append("dim") if hasattr(self, "_dim_supported") else None
        if self.italic:
            parts.append("italic")
        if self.underline:
            parts.append("underline")
        if self.blink:
            parts.append("blink")
        if self.reverse:
            parts.append("reverse")
        if self.hidden:
            parts.append("hidden")
        if self.strikethrough:
            parts.append("strike")

        if self.fg is not None:
            fg_name = self._normalize_color_name(self.fg)
            if fg_name:
                parts.append(fg_name)

        if self.bg is not None:
            bg_name = self._normalize_color_name(self.bg)
            if bg_name:
                parts.append(f"bg:{bg_name}")

        return " ".join(parts)

    def _normalize_color_name(self, color: str | int) -> str:
        """Normalize color to prompt_toolkit format."""
        if isinstance(color, int):
            if 0 <= color <= 15:
                # Map to ansi color names
                names = [
                    "ansiblack", "ansired", "ansigreen", "ansiyellow",
                    "ansiblue", "ansimagenta", "ansicyan", "ansiwhite",
                    "ansibrightblack", "ansibrightred", "ansibrightgreen", "ansibrightyellow",
                    "ansibrightblue", "ansibrightmagenta", "ansibrightcyan", "ansibrightwhite",
                ]
                return names[color]
            return f"#{color:02x}{color:02x}{color:02x}"

        color_lower = color.lower().replace(" ", "")

        # Map to prompt_toolkit names
        color_map = {
            "black": "ansiblack",
            "red": "ansired",
            "green": "ansigreen",
            "yellow": "ansiyellow",
            "blue": "ansiblue",
            "magenta": "ansimagenta",
            "cyan": "ansicyan",
            "white": "ansiwhite",
            "brightblack": "ansibrightblack",
            "brightred": "ansibrightred",
            "brightgreen": "ansibrightgreen",
            "brightyellow": "ansibrightyellow",
            "brightblue": "ansibrightblue",
            "brightmagenta": "ansibrightmagenta",
            "brightcyan": "ansibrightcyan",
            "brightwhite": "ansibrightwhite",
            "gray": "ansibrightblack",
            "grey": "ansibrightblack",
        }

        return color_map.get(color_lower, color_lower)


class ColorParser:
    """Parser for color specification strings."""

    def parse(self, color_spec: str) -> ParsedColor:
        """Parse a color specification string.

        Args:
            color_spec: Color string like "bold red on white"

        Returns:
            ParsedColor object

        Examples:
            >>> parser = ColorParser()
            >>> color = parser.parse("bold red on white")
            >>> color.fg
            'red'
            >>> color.bg
            'white'
            >>> color.bold
            True
        """
        if not color_spec:
            return ParsedColor()

        # Check for combine prefix
        combine = color_spec.startswith("+")
        if combine:
            color_spec = color_spec[1:].strip()

        result = ParsedColor(combine=combine)
        parts = color_spec.lower().split()

        i = 0
        while i < len(parts):
            part = parts[i]

            # Check for attributes
            if part in ATTRIBUTES:
                setattr(result, part if part != "inverse" else "reverse", True)
                i += 1
                continue

            # Check for "on" keyword (background)
            if part == "on" and i + 1 < len(parts):
                # Next part(s) are background color
                bg_parts: list[str] = []
                i += 1
                while i < len(parts) and parts[i] not in ATTRIBUTES and parts[i] != "on":
                    bg_parts.append(parts[i])
                    i += 1
                result.bg = " ".join(bg_parts)
                continue

            # Check for "bright" prefix
            if part == "bright" and i + 1 < len(parts):
                next_part = parts[i + 1]
                if next_part in COLORS or next_part in ("black", "white"):
                    if result.fg is None:
                        result.fg = f"bright {next_part}"
                    i += 2
                    continue

            # Must be a color name (foreground)
            if part in COLORS or part in BRIGHT_COLORS:
                if result.fg is None:
                    result.fg = part
            elif part.startswith("#") or part.isdigit():
                # Hex or numeric color
                if result.fg is None:
                    result.fg = part

            i += 1

        return result


def parse_color(color_spec: str) -> ParsedColor:
    """Parse a color specification string.

    Args:
        color_spec: Color string like "bold red on white"

    Returns:
        ParsedColor object
    """
    return ColorParser().parse(color_spec)


def combine_colors(base: ParsedColor, overlay: ParsedColor) -> ParsedColor:
    """Combine two colors, with overlay taking precedence for set attributes.

    If overlay has combine=True, only attributes that are explicitly set in
    overlay will be applied to base.

    Args:
        base: Base color
        overlay: Color to overlay

    Returns:
        Combined color
    """
    result = ParsedColor(
        fg=overlay.fg if overlay.fg is not None else base.fg,
        bg=overlay.bg if overlay.bg is not None else base.bg,
        bold=overlay.bold if overlay.bold is not None else base.bold,
        dim=overlay.dim if overlay.dim is not None else base.dim,
        italic=overlay.italic if overlay.italic is not None else base.italic,
        underline=overlay.underline if overlay.underline is not None else base.underline,
        blink=overlay.blink if overlay.blink is not None else base.blink,
        reverse=overlay.reverse if overlay.reverse is not None else base.reverse,
        hidden=overlay.hidden if overlay.hidden is not None else base.hidden,
        strikethrough=overlay.strikethrough if overlay.strikethrough is not None else base.strikethrough,
        combine=False,
    )
    return result


def get_colors_for_groups(
    category_colors: list[str], num_groups: int
) -> list[ParsedColor]:
    """Get colors for each capture group.

    If there are fewer colors than groups, the last color is repeated.

    Args:
        category_colors: List of color specifications from category
        num_groups: Number of capture groups

    Returns:
        List of ParsedColor objects, one per group
    """
    parser = ColorParser()

    if not category_colors:
        # Default to white
        default_color = parser.parse("white")
        return [default_color] * num_groups

    parsed_colors = [parser.parse(c) for c in category_colors]

    result: list[ParsedColor] = []
    for i in range(num_groups):
        if i < len(parsed_colors):
            result.append(parsed_colors[i])
        else:
            # Repeat last color
            result.append(parsed_colors[-1])

    return result

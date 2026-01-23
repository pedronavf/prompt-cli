"""Program detection and matching."""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_cli.config.schema import Config


# Built-in patterns for common compilers/tools
# Maps canonical name -> list of (pattern_type, pattern)
BUILTIN_PROGRAMS: dict[str, list[tuple[str, str]]] = {
    "gcc": [
        ("suffix", "-gcc"),
        ("suffix", "-g++"),
        ("exact", "gcc"),
        ("exact", "g++"),
        ("exact", "cc"),
        ("exact", "c++"),
        # gcc-12, g++-11, etc.
        ("prefix", "gcc-"),
        ("prefix", "g++-"),
    ],
    "clang": [
        ("suffix", "-clang"),
        ("suffix", "-clang++"),
        ("exact", "clang"),
        ("exact", "clang++"),
        ("prefix", "clang-"),
        ("prefix", "clang++-"),
    ],
    "rustc": [
        ("exact", "rustc"),
    ],
    "cargo": [
        ("exact", "cargo"),
    ],
    "go": [
        ("exact", "go"),
    ],
    "python": [
        ("exact", "python"),
        ("exact", "python3"),
        ("prefix", "python3."),
        ("exact", "python2"),
    ],
    "make": [
        ("exact", "make"),
        ("exact", "gmake"),
        ("exact", "bmake"),
    ],
    "cmake": [
        ("exact", "cmake"),
    ],
    "ninja": [
        ("exact", "ninja"),
    ],
    "ld": [
        ("suffix", "-ld"),
        ("exact", "ld"),
        ("exact", "ld.lld"),
        ("exact", "ld.gold"),
        ("exact", "ld.bfd"),
    ],
    "ar": [
        ("suffix", "-ar"),
        ("exact", "ar"),
        ("exact", "llvm-ar"),
    ],
    "as": [
        ("suffix", "-as"),
        ("exact", "as"),
    ],
}


@dataclass
class ProgramMatch:
    """Result of program matching."""

    canonical_name: str  # e.g., "gcc"
    matched_name: str  # e.g., "arm-linux-gnueabi-gcc"
    source: str  # "builtin" or "config"


def _match_builtin(basename: str) -> str | None:
    """Try to match against built-in program patterns.

    Args:
        basename: The executable basename (e.g., "arm-linux-gnueabi-gcc")

    Returns:
        Canonical program name or None if no match
    """
    basename_lower = basename.lower()

    for program_name, patterns in BUILTIN_PROGRAMS.items():
        for pattern_type, pattern in patterns:
            if pattern_type == "exact":
                if basename_lower == pattern.lower():
                    return program_name
            elif pattern_type == "prefix":
                if basename_lower.startswith(pattern.lower()):
                    return program_name
            elif pattern_type == "suffix":
                if basename_lower.endswith(pattern.lower()):
                    return program_name

    return None


def _match_config(basename: str, config: Config) -> str | None:
    """Try to match against config-defined program patterns.

    Args:
        basename: The executable basename
        config: Configuration object

    Returns:
        Program name from config or None if no match
    """
    for _program_name, program in config.programs.items():
        # Check exact name match
        if program.name.lower() == basename.lower():
            return program.name

        # Check aliases
        for alias in program.aliases:
            if alias.startswith("glob:"):
                pattern = alias[5:]
                if fnmatch.fnmatch(basename.lower(), pattern.lower()):
                    return program.name
            elif alias.startswith("regexp:"):
                pattern = alias[7:]
                try:
                    if re.match(pattern, basename, re.IGNORECASE):
                        return program.name
                except re.error:
                    continue
            else:
                # Literal alias
                if alias.lower() == basename.lower():
                    return program.name

    return None


def detect_program(executable: str, config: Config | None = None) -> ProgramMatch | None:
    """Detect the program from an executable path.

    Uses a two-tier approach:
    1. Try built-in fast matching for common compilers
    2. Fall back to config-defined regexp matching

    Args:
        executable: The executable path or name (e.g., "/usr/bin/arm-linux-gnueabi-gcc")
        config: Optional configuration object for custom program matching

    Returns:
        ProgramMatch with canonical name, or None if unknown
    """
    # Extract basename
    basename = os.path.basename(executable)

    # Tier 1: Try built-in matchers (fast)
    builtin_match = _match_builtin(basename)
    if builtin_match:
        return ProgramMatch(
            canonical_name=builtin_match,
            matched_name=basename,
            source="builtin",
        )

    # Tier 2: Try config-defined patterns
    if config:
        config_match = _match_config(basename, config)
        if config_match:
            return ProgramMatch(
                canonical_name=config_match,
                matched_name=basename,
                source="config",
            )

    # No match - return the basename as-is
    return ProgramMatch(
        canonical_name=basename,
        matched_name=basename,
        source="unknown",
    )


def get_program_names(config: Config | None = None) -> list[str]:
    """Get list of known program names for completion.

    Args:
        config: Optional configuration object

    Returns:
        List of program names (built-in + config-defined)
    """
    names: set[str] = set()

    # Add built-in program names
    names.update(BUILTIN_PROGRAMS.keys())

    # Add config-defined programs
    if config:
        for program in config.programs.values():
            names.add(program.name)
            # Add literal aliases
            for alias in program.aliases:
                if not alias.startswith(("glob:", "regexp:")):
                    names.add(alias)

    return sorted(names)

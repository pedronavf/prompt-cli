"""Program detection and matching."""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_cli.config.schema import Config
    from prompt_cli.core.tokenizer import Token


# Known compiler launchers/wrappers
# These programs wrap compilers and may have their own arguments before the actual compiler
BUILTIN_LAUNCHERS: dict[str, list[str]] = {
    # ccache: compiler cache, next non-flag token is compiler
    "ccache": [],
    # distcc: distributed compilation
    "distcc": [],
    # sccache: shared compilation cache (Mozilla)
    "sccache": [],
    # icecc/icecream: distributed compilation
    "icecc": [],
    # colorgcc: colorized gcc output
    "colorgcc": [],
    # scan-build: clang static analyzer wrapper
    "scan-build": ["-o", "--use-analyzer", "-enable-checker", "-disable-checker"],
    # bear: build ear - generates compilation database
    "bear": ["-o", "--output", "-a", "--append"],
    # time: measure execution time
    "time": ["-f", "-o", "--format", "--output"],
    # env: run with modified environment
    "env": [],
    # nice/ionice: priority adjustment
    "nice": ["-n", "--adjustment"],
    "ionice": ["-c", "-n", "-p"],
}

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
class LauncherInfo:
    """Information about a detected launcher."""

    name: str  # e.g., "ccache"
    token_index: int  # Index of launcher token
    args_end_index: int  # Index after last launcher argument


@dataclass
class ProgramMatch:
    """Result of program matching."""

    canonical_name: str  # e.g., "gcc"
    matched_name: str  # e.g., "arm-linux-gnueabi-gcc"
    source: str  # "builtin", "config", or "unknown"
    token_index: int = 0  # Index of the compiler token
    launcher: LauncherInfo | None = None  # Launcher if present


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


def _is_launcher(basename: str, config: Config | None = None) -> tuple[str, list[str]] | None:
    """Check if basename is a known launcher.

    Args:
        basename: The executable basename
        config: Optional config for user-defined launchers

    Returns:
        Tuple of (launcher_name, flags_with_args) or None
    """
    basename_lower = basename.lower()

    # Check built-in launchers
    for launcher, flags_with_args in BUILTIN_LAUNCHERS.items():
        if basename_lower == launcher.lower():
            return launcher, flags_with_args

    # Check config-defined launchers
    if config and hasattr(config, "launchers"):
        for launcher_name, launcher_def in config.launchers.items():
            if basename_lower == launcher_name.lower():
                return launcher_name, getattr(launcher_def, "flags_with_args", [])
            # Check aliases
            for alias in getattr(launcher_def, "aliases", []):
                if basename_lower == alias.lower():
                    return launcher_name, getattr(launcher_def, "flags_with_args", [])

    return None


def find_compiler(
    tokens: list[Token], config: Config | None = None
) -> ProgramMatch | None:
    """Find the actual compiler in a command line, handling launchers.

    Scans through tokens to find the compiler, skipping any launchers
    (like ccache, distcc) and their arguments.

    Examples:
        "gcc -O2 foo.c" -> gcc at index 0
        "ccache gcc -O2 foo.c" -> gcc at index 1, launcher=ccache
        "/usr/bin/ccache /usr/bin/arm-linux-gnueabihf-gcc -O2" -> gcc at index 1

    Args:
        tokens: List of command line tokens
        config: Optional configuration object

    Returns:
        ProgramMatch with compiler info and token index, or None if empty
    """
    if not tokens:
        return None

    i = 0
    launcher_info: LauncherInfo | None = None

    while i < len(tokens):
        token = tokens[i]
        basename = os.path.basename(token.value)

        # Check if this is a launcher
        launcher_check = _is_launcher(basename, config)
        if launcher_check:
            launcher_name, flags_with_args = launcher_check
            launcher_start = i
            i += 1

            # Skip launcher arguments
            while i < len(tokens):
                arg_token = tokens[i]
                # If it looks like a flag, check if launcher owns it
                if arg_token.value.startswith("-"):
                    # Check if this flag takes an argument
                    flag_takes_arg = False
                    for flag in flags_with_args:
                        if arg_token.value == flag or arg_token.value.startswith(flag + "="):
                            flag_takes_arg = True
                            break

                    if flag_takes_arg and "=" not in arg_token.value:
                        # Skip the flag and its argument
                        i += 2
                    else:
                        # Skip just the flag
                        i += 1
                else:
                    # Not a flag - this should be the compiler
                    break

            launcher_info = LauncherInfo(
                name=launcher_name,
                token_index=launcher_start,
                args_end_index=i,
            )
            continue

        # Not a launcher - try to detect as a program
        program_match = detect_program(token.value, config)
        if program_match:
            program_match.token_index = i
            program_match.launcher = launcher_info
            return program_match

        # If we get here and haven't found a compiler, return unknown
        return ProgramMatch(
            canonical_name=basename,
            matched_name=basename,
            source="unknown",
            token_index=i,
            launcher=launcher_info,
        )

    # No compiler found (only launcher with no compiler after it)
    return None


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

"""File and directory validators."""

from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Any

from prompt_cli.validators.base import Validator, ValidatorResult


class FileValidator(Validator):
    """Validator for file selection."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.extensions: list[str] = config.get("extensions", [])
        self.multiple: bool = config.get("multiple", False)
        self.separator: str = config.get("separator", ",")
        self.sort: str = config.get("sort", "name")
        self.include: list[str] = config.get("include", [])
        self.exclude: list[str] = config.get("exclude", [])
        self.startup_directory: str = config.get("startup_directory", ".")
        self.change: bool = config.get("change", True)

    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get file completions."""
        cwd = context.get("cwd", os.getcwd())

        # Handle multiple values
        if self.multiple and self.separator in current_value:
            parts = current_value.rsplit(self.separator, 1)
            prefix = parts[0] + self.separator
            search_value = parts[1]
        else:
            prefix = ""
            search_value = current_value

        # Determine search directory and pattern
        if os.path.sep in search_value or "/" in search_value:
            search_dir = os.path.dirname(search_value)
            pattern = os.path.basename(search_value)
            if not os.path.isabs(search_dir):
                search_dir = os.path.join(cwd, search_dir)
        else:
            search_dir = cwd
            pattern = search_value

        # Get matching files
        completions: list[str] = []
        try:
            for entry in os.scandir(search_dir):
                name = entry.name

                # Skip hidden files unless pattern starts with .
                if name.startswith(".") and not pattern.startswith("."):
                    continue

                # Match pattern
                if pattern and not name.lower().startswith(pattern.lower()):
                    continue

                # Check extensions
                if self.extensions and entry.is_file():
                    ext = os.path.splitext(name)[1]
                    if ext not in self.extensions and ext.lower() not in self.extensions:
                        continue

                # Check include/exclude patterns
                if not self._matches_filters(name):
                    continue

                # Build completion
                if entry.is_dir():
                    completion = name + os.path.sep
                else:
                    completion = name

                # Add directory prefix if searching in subdirectory
                if os.path.sep in search_value or "/" in search_value:
                    dir_prefix = os.path.dirname(search_value)
                    if dir_prefix:
                        completion = os.path.join(dir_prefix, completion)

                completions.append(prefix + completion)

        except OSError:
            pass

        # Sort completions
        completions = self._sort_completions(completions, search_dir)

        return ValidatorResult(completions=completions)

    def _matches_filters(self, name: str) -> bool:
        """Check if name matches include/exclude filters."""
        # Check exclude patterns
        for pattern in self.exclude:
            if fnmatch.fnmatch(name, pattern):
                return False

        # Check include patterns (if any specified)
        if self.include:
            for pattern in self.include:
                if fnmatch.fnmatch(name, pattern):
                    return True
            return False

        return True

    def _sort_completions(self, completions: list[str], search_dir: str) -> list[str]:
        """Sort completions based on sort setting."""
        if self.sort == "name":
            return sorted(completions, key=str.lower)
        elif self.sort == "date":
            def get_mtime(path: str) -> float:
                try:
                    full_path = os.path.join(search_dir, os.path.basename(path.rstrip(os.path.sep)))
                    return os.path.getmtime(full_path)
                except OSError:
                    return 0
            return sorted(completions, key=get_mtime, reverse=True)
        elif self.sort == "size":
            def get_size(path: str) -> int:
                try:
                    full_path = os.path.join(search_dir, os.path.basename(path.rstrip(os.path.sep)))
                    return os.path.getsize(full_path)
                except OSError:
                    return 0
            return sorted(completions, key=get_size, reverse=True)
        return completions

    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate file path."""
        cwd = context.get("cwd", os.getcwd())

        # Handle multiple values
        if self.multiple:
            values = value.split(self.separator)
        else:
            values = [value]

        for v in values:
            v = v.strip()
            if not v:
                continue

            path = Path(v)
            if not path.is_absolute():
                path = Path(cwd) / path

            if not path.exists():
                return ValidatorResult(valid=False, message=f"File not found: {v}")

            if self.extensions and path.is_file():
                ext = path.suffix
                if ext not in self.extensions and ext.lower() not in self.extensions:
                    return ValidatorResult(
                        valid=False,
                        message=f"Invalid extension: {ext} (expected: {', '.join(self.extensions)})",
                    )

        return ValidatorResult(valid=True)


class DirectoryValidator(FileValidator):
    """Validator for directory selection."""

    def __init__(self, config: dict[str, Any]) -> None:
        # Remove extensions for directory validator
        config = dict(config)
        config.pop("extensions", None)
        super().__init__(config)
        self.extensions = []

    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get directory completions."""
        result = super().get_completions(current_value, context)

        # Filter to only directories
        completions = [c for c in result.completions if c.endswith(os.path.sep)]

        return ValidatorResult(completions=completions)

    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate directory path."""
        cwd = context.get("cwd", os.getcwd())

        path = Path(value)
        if not path.is_absolute():
            path = Path(cwd) / path

        if not path.exists():
            return ValidatorResult(valid=False, message=f"Directory not found: {value}")

        if not path.is_dir():
            return ValidatorResult(valid=False, message=f"Not a directory: {value}")

        return ValidatorResult(valid=True)

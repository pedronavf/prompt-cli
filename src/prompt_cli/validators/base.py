"""Base validator class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidatorResult:
    """Result from validator completion/validation."""

    completions: list[str] = field(default_factory=list)
    valid: bool = True
    message: str = ""
    selected_index: int = 0


class Validator(ABC):
    """Base class for validators."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize validator with configuration.

        Args:
            config: Validator configuration dictionary
        """
        self.config = config

    @abstractmethod
    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get completions for the current value.

        Args:
            current_value: Current value being completed
            context: Additional context (current directory, etc.)

        Returns:
            ValidatorResult with completions
        """
        ...

    @abstractmethod
    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate a value.

        Args:
            value: Value to validate
            context: Additional context

        Returns:
            ValidatorResult indicating validity
        """
        ...

    def cycle_next(self, current_value: str, context: dict[str, Any]) -> str:
        """Get the next value in a cycle.

        Args:
            current_value: Current value
            context: Additional context

        Returns:
            Next value in cycle
        """
        result = self.get_completions(current_value, context)
        if not result.completions:
            return current_value

        # Find current value in completions
        try:
            idx = result.completions.index(current_value)
            next_idx = (idx + 1) % len(result.completions)
        except ValueError:
            next_idx = 0

        return result.completions[next_idx]

    def cycle_prev(self, current_value: str, context: dict[str, Any]) -> str:
        """Get the previous value in a cycle.

        Args:
            current_value: Current value
            context: Additional context

        Returns:
            Previous value in cycle
        """
        result = self.get_completions(current_value, context)
        if not result.completions:
            return current_value

        # Find current value in completions
        try:
            idx = result.completions.index(current_value)
            prev_idx = (idx - 1) % len(result.completions)
        except ValueError:
            prev_idx = len(result.completions) - 1

        return result.completions[prev_idx]

"""Warnings toggle validator."""

from __future__ import annotations

from typing import Any

from prompt_cli.validators.base import Validator, ValidatorResult


class WarningsValidator(Validator):
    """Validator for warning flags with toggle support."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.prefix: str = config.get("prefix", "no-")

    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get warning completions.

        This would typically use a database of known warnings for the compiler.
        For now, returns the toggled version as the only completion.
        """
        toggled = self.toggle(current_value)
        return ValidatorResult(completions=[toggled])

    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate warning value.

        Warnings are generally valid as long as they're non-empty.
        The compiler will validate if the warning is actually known.
        """
        if not value:
            return ValidatorResult(valid=False, message="Warning name required")
        return ValidatorResult(valid=True)

    def toggle(self, warning: str) -> str:
        """Toggle warning between enabled and disabled.

        Args:
            warning: Warning name (e.g., "unused-variable" or "no-unused-variable")

        Returns:
            Toggled warning name
        """
        if warning.startswith(self.prefix):
            # Remove prefix (disable -> enable)
            return warning[len(self.prefix):]
        else:
            # Add prefix (enable -> disable)
            return self.prefix + warning

    def is_disabled(self, warning: str) -> bool:
        """Check if warning is disabled (has the prefix)."""
        return warning.startswith(self.prefix)

    def get_base_name(self, warning: str) -> str:
        """Get the base warning name without prefix."""
        if warning.startswith(self.prefix):
            return warning[len(self.prefix):]
        return warning

    def cycle_next(self, current_value: str, context: dict[str, Any]) -> str:
        """Cycle toggles between enabled and disabled."""
        return self.toggle(current_value)

    def cycle_prev(self, current_value: str, context: dict[str, Any]) -> str:
        """Cycle toggles between enabled and disabled."""
        return self.toggle(current_value)

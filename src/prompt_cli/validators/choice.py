"""Choice and multiple-choice validators."""

from __future__ import annotations

from typing import Any

from prompt_cli.validators.base import Validator, ValidatorResult


class ChoiceValidator(Validator):
    """Validator for single choice from options."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.options: list[str] = config.get("options", [])

    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get choice completions."""
        # Filter options by current value prefix
        if current_value:
            completions = [
                opt for opt in self.options
                if opt.lower().startswith(current_value.lower())
            ]
        else:
            completions = list(self.options)

        return ValidatorResult(completions=completions)

    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate choice value."""
        if value in self.options:
            return ValidatorResult(valid=True)

        # Case-insensitive match
        for opt in self.options:
            if opt.lower() == value.lower():
                return ValidatorResult(valid=True)

        return ValidatorResult(
            valid=False,
            message=f"Invalid choice: {value} (expected: {', '.join(self.options)})",
        )


class MultipleChoiceValidator(Validator):
    """Validator for multiple choices with constraints."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.options: list[str] = config.get("options", [])
        self.delimiter: str = config.get("delimiter", ",")
        self.minimum: int = config.get("minimum", 0)
        self.maximum: int = config.get("maximum", 999)

        # Parse option constraints
        self._parse_constraints()

    def _parse_constraints(self) -> None:
        """Parse option constraints ($prefix, suffix$, $both$)."""
        self.clean_options: list[str] = []
        self.must_be_first: set[str] = set()
        self.must_be_last: set[str] = set()
        self.must_be_only: set[str] = set()

        for opt in self.options:
            clean = opt
            is_first = opt.startswith("$")
            is_last = opt.endswith("$")

            if is_first:
                clean = clean[1:]
            if is_last:
                clean = clean[:-1]

            self.clean_options.append(clean)

            if is_first and is_last:
                self.must_be_only.add(clean)
            elif is_first:
                self.must_be_first.add(clean)
            elif is_last:
                self.must_be_last.add(clean)

    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get available completions based on current value and constraints."""
        # Parse current selections
        if current_value:
            current_parts = [p.strip() for p in current_value.split(self.delimiter)]
        else:
            current_parts = []

        # Determine available options
        available: list[str] = []
        has_selections = bool(current_parts) and current_parts[0]

        for opt in self.clean_options:
            # Skip already selected
            if opt in current_parts:
                continue

            # Check constraints
            if has_selections:
                # Can't add if must_be_first and there are already selections
                if opt in self.must_be_first:
                    continue

                # Can't add if must_be_only
                if opt in self.must_be_only:
                    continue

                # Can't add if last selection has must_be_last
                if current_parts:
                    last = current_parts[-1]
                    if last in self.must_be_last:
                        continue

            # Check maximum
            if len(current_parts) >= self.maximum:
                continue

            available.append(opt)

        return ValidatorResult(completions=available)

    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate multiple choice value."""
        if not value:
            if self.minimum > 0:
                return ValidatorResult(
                    valid=False,
                    message=f"At least {self.minimum} selection(s) required",
                )
            return ValidatorResult(valid=True)

        parts = [p.strip() for p in value.split(self.delimiter)]

        # Check count
        if len(parts) < self.minimum:
            return ValidatorResult(
                valid=False,
                message=f"At least {self.minimum} selection(s) required",
            )

        if len(parts) > self.maximum:
            return ValidatorResult(
                valid=False,
                message=f"At most {self.maximum} selection(s) allowed",
            )

        # Validate each part
        for part in parts:
            if part not in self.clean_options:
                return ValidatorResult(
                    valid=False,
                    message=f"Invalid option: {part}",
                )

        # Check constraints
        for i, part in enumerate(parts):
            if part in self.must_be_only and len(parts) > 1:
                return ValidatorResult(
                    valid=False,
                    message=f"'{part}' must be the only selection",
                )

            if part in self.must_be_first and i > 0:
                return ValidatorResult(
                    valid=False,
                    message=f"'{part}' must be first",
                )

            if part in self.must_be_last and i < len(parts) - 1:
                return ValidatorResult(
                    valid=False,
                    message=f"'{part}' must be last",
                )

        return ValidatorResult(valid=True)

    def cycle_next(self, current_value: str, context: dict[str, Any]) -> str:
        """Cycle to next available option."""
        result = self.get_completions(current_value, context)

        if not result.completions:
            return current_value

        # Add first available option
        if current_value:
            return f"{current_value}{self.delimiter}{result.completions[0]}"
        return result.completions[0]

    def toggle_option(self, current_value: str, option: str) -> str:
        """Toggle an option in the selection."""
        if not current_value:
            return option

        parts = [p.strip() for p in current_value.split(self.delimiter)]

        if option in parts:
            # Remove option
            parts.remove(option)
        else:
            # Add option
            parts.append(option)

        return self.delimiter.join(parts)

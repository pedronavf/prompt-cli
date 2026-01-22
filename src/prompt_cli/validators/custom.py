"""Custom external command validator."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from prompt_cli.validators.base import Validator, ValidatorResult


class CustomValidator(Validator):
    """Validator that uses an external command for completions."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self.command: str = config.get("command", "")
        self.timeout: float = config.get("timeout", 5.0)

    def get_completions(self, current_value: str, context: dict[str, Any]) -> ValidatorResult:
        """Get completions from external command.

        The command receives:
        - Current value as first argument
        - Current working directory as second argument
        - Additional context as environment variables (PROMPT_*)

        The command should output one completion per line.
        """
        if not self.command:
            return ValidatorResult(completions=[])

        cwd = context.get("cwd", os.getcwd())

        # Build environment with context
        env = os.environ.copy()
        env["PROMPT_VALUE"] = current_value
        env["PROMPT_CWD"] = cwd

        for key, value in context.items():
            if isinstance(value, str):
                env[f"PROMPT_{key.upper()}"] = value

        try:
            result = subprocess.run(
                [self.command, current_value, cwd],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                cwd=cwd,
            )

            if result.returncode != 0:
                return ValidatorResult(
                    completions=[],
                    valid=False,
                    message=result.stderr.strip() if result.stderr else "Command failed",
                )

            # Parse output - one completion per line
            completions = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip()
            ]

            return ValidatorResult(completions=completions)

        except subprocess.TimeoutExpired:
            return ValidatorResult(
                completions=[],
                valid=False,
                message=f"Command timed out after {self.timeout}s",
            )
        except FileNotFoundError:
            return ValidatorResult(
                completions=[],
                valid=False,
                message=f"Command not found: {self.command}",
            )
        except Exception as e:
            return ValidatorResult(
                completions=[],
                valid=False,
                message=str(e),
            )

    def validate(self, value: str, context: dict[str, Any]) -> ValidatorResult:
        """Validate using external command.

        For custom validators, we assume the value is valid if it's in
        the completions, or always valid if the command doesn't provide
        validation.
        """
        # Get completions and check if value is in them
        result = self.get_completions(value, context)

        if result.completions and value not in result.completions:
            return ValidatorResult(
                valid=False,
                message=f"Invalid value: {value}",
            )

        return ValidatorResult(valid=True)

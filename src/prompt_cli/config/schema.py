"""Pydantic models for configuration schema."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Color(BaseModel):
    """A color specification string like 'bold red on white'."""

    value: str

    @classmethod
    def from_str(cls, value: str) -> Color:
        return cls(value=value)

    def __str__(self) -> str:
        return self.value


class FlagHelp(BaseModel):
    """Help information for a flag."""

    flag: str = Field(description="Flag syntax, e.g., '-I directory'")
    description: str = Field(description="Short description with optional markup")
    help: str = Field(default="", description="Long help text with markup")


class ValidatorConfig(BaseModel):
    """Base validator configuration."""

    type: str = Field(description="Validator type: file, directory, choice, etc.")


class FileValidator(ValidatorConfig):
    """File/directory validator configuration."""

    type: Literal["file", "directory"] = "file"
    extensions: list[str] = Field(default_factory=list)
    multiple: bool = False
    separator: str = ","
    sort: str = "name"
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    startup_directory: str = "."
    change: bool = True


class ChoiceValidator(ValidatorConfig):
    """Choice validator for cycling through options."""

    type: Literal["choice"] = "choice"
    options: list[str] = Field(default_factory=list)


class MultipleChoiceValidator(ValidatorConfig):
    """Multiple choice validator with constraints."""

    type: Literal["multiple-choice"] = "multiple-choice"
    options: list[str] = Field(default_factory=list)
    delimiter: str = ","
    minimum: int = 0
    maximum: int = Field(default=999)


class WarningsValidator(ValidatorConfig):
    """Warnings toggle validator."""

    type: Literal["warnings"] = "warnings"
    prefix: str = "no-"


class CustomValidator(ValidatorConfig):
    """Custom external command validator."""

    type: Literal["custom"] = "custom"
    command: str = Field(description="Path to external command")


Validator = FileValidator | ChoiceValidator | MultipleChoiceValidator | WarningsValidator | CustomValidator


def parse_validator(data: dict[str, Any] | None) -> Validator | None:
    """Parse validator configuration from dict."""
    if data is None:
        return None

    validator_type = data.get("type", "file")
    match validator_type:
        case "file" | "directory":
            return FileValidator(**data)
        case "choice":
            return ChoiceValidator(**data)
        case "multiple-choice":
            return MultipleChoiceValidator(**data)
        case "warnings":
            return WarningsValidator(**data)
        case "custom":
            return CustomValidator(**data)
        case _:
            raise ValueError(f"Unknown validator type: {validator_type}")


class Flag(BaseModel):
    """Flag definition with regex patterns and category."""

    category: str = Field(description="Category name, e.g., 'Includes'")
    regexps: list[str] = Field(default_factory=list, description="Regex patterns with capture groups")
    capture_groups: list[str] = Field(
        default_factory=list,
        description="Names for capture groups (e.g., ['flag', 'name', 'value']). "
        "Used when regexp groups aren't named with (?P<name>...) syntax.",
    )
    validator: dict[str, Any] | None = Field(default=None, description="Validator configuration")
    help: list[FlagHelp] = Field(default_factory=list, description="Help entries for this flag")

    def get_validator(self) -> Validator | None:
        """Parse and return the validator configuration."""
        return parse_validator(self.validator)


class Category(BaseModel):
    """Category definition with colors for capture groups.

    Colors can be specified as:
    - A dict mapping group names to colors: {"flag": "red", "value": "cyan"}
    - A list for backward compatibility: ["red", "cyan"] (applied to groups in order)
    """

    name: str = Field(default="", description="Category name")
    colors: dict[str, str] = Field(
        default_factory=dict,
        description="Map of capture group name to color (e.g., {'flag': 'red', 'value': 'cyan'})",
    )

    @field_validator("colors", mode="before")
    @classmethod
    def parse_colors(cls, v: dict[str, str] | list[str] | None) -> dict[str, str]:
        """Parse colors from list or dict format."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        if isinstance(v, list):
            # Convert list to dict with numeric keys for backward compatibility
            # ["red", "cyan"] -> {"0": "red", "1": "cyan"}
            return {str(i): color for i, color in enumerate(v)}
        return {}


class CategoryMap(BaseModel):
    """Hierarchical category grouping."""

    name: str = Field(description="Group name, e.g., 'Compiler'")
    categories: list[str] = Field(default_factory=list, description="List of category or group names")


class ThemeCategory(BaseModel):
    """Theme color for a specific category."""

    category: str
    color: str


class Theme(BaseModel):
    """Theme definition with colors for categories."""

    name: str = Field(description="Theme name, e.g., 'oblivion'")
    default: str = Field(default="white", description="Default color for unmatched text")
    categories: dict[str, str] = Field(
        default_factory=dict, description="Category name to color mapping"
    )


class ProgramConfig(BaseModel):
    """Program-specific configuration."""

    default_validator: dict[str, Any] | None = Field(default=None)


class Program(BaseModel):
    """Program definition with aliases and flags."""

    name: str = Field(description="Program name, e.g., 'gcc'")
    aliases: list[str] = Field(
        default_factory=list,
        description="Aliases: literal names, 'glob:pattern', or 'regexp:pattern'",
    )
    flags: list[Flag] = Field(default_factory=list, description="Program-specific flags")
    config: ProgramConfig | None = Field(default=None, description="Program-specific config")


class KeyBindings(BaseModel):
    """Key bindings for a mode."""

    bindings: dict[str, str] = Field(default_factory=dict)


class GlobalConfig(BaseModel):
    """Global configuration options."""

    color: bool = Field(default=True, description="Enable/disable colors")
    default_validator: dict[str, Any] | None = Field(default=None)


class Config(BaseModel):
    """Top-level configuration."""

    config: GlobalConfig = Field(default_factory=GlobalConfig)
    categories: dict[str, Category] = Field(default_factory=dict)
    category_maps: dict[str, CategoryMap] = Field(default_factory=dict)
    themes: dict[str, Theme] = Field(default_factory=dict)
    flags: list[Flag] = Field(default_factory=list, description="Global flags")
    programs: dict[str, Program] = Field(default_factory=dict)
    keybindings: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="Mode name to keybindings mapping"
    )
    aliases: dict[str, str] = Field(
        default_factory=dict, description="Command aliases"
    )

    @field_validator("categories", mode="before")
    @classmethod
    def parse_categories(cls, v: dict[str, Any]) -> dict[str, Category]:
        """Parse category definitions."""
        result = {}
        for name, data in v.items():
            if isinstance(data, dict):
                result[name.lower()] = Category(name=name, **data)
            else:
                result[name.lower()] = Category(name=name, colors=[data] if isinstance(data, str) else data)
        return result

    @field_validator("category_maps", mode="before")
    @classmethod
    def parse_category_maps(cls, v: dict[str, Any]) -> dict[str, CategoryMap]:
        """Parse category map definitions."""
        result = {}
        for name, data in v.items():
            if isinstance(data, list):
                result[name.lower()] = CategoryMap(name=name, categories=data)
            elif isinstance(data, dict):
                result[name.lower()] = CategoryMap(name=name, **data)
        return result

    @field_validator("themes", mode="before")
    @classmethod
    def parse_themes(cls, v: dict[str, Any]) -> dict[str, Theme]:
        """Parse theme definitions."""
        result = {}
        for name, data in v.items():
            if isinstance(data, dict):
                result[name.lower()] = Theme(name=name, **data)
        return result

    @field_validator("programs", mode="before")
    @classmethod
    def parse_programs(cls, v: dict[str, Any]) -> dict[str, Program]:
        """Parse program definitions."""
        result = {}
        for name, data in v.items():
            if isinstance(data, dict):
                result[name.lower()] = Program(name=name, **data)
        return result

    def get_program(self, executable: str) -> Program | None:
        """Find program config matching the executable name."""
        import fnmatch
        import re

        exe_name = executable.split("/")[-1]  # Get basename

        for program in self.programs.values():
            # Check exact name match
            if program.name.lower() == exe_name.lower():
                return program

            # Check aliases
            for alias in program.aliases:
                if alias.startswith("glob:"):
                    pattern = alias[5:]
                    if fnmatch.fnmatch(exe_name, pattern):
                        return program
                elif alias.startswith("regexp:"):
                    pattern = alias[7:]
                    if re.match(pattern, exe_name):
                        return program
                elif alias.lower() == exe_name.lower():
                    return program

        return None

    def get_flags_for_program(self, executable: str) -> list[Flag]:
        """Get all flags for a program (global + program-specific)."""
        flags = list(self.flags)  # Start with global flags
        program = self.get_program(executable)
        if program:
            flags.extend(program.flags)
        return flags

    def get_theme(self, name: str | None = None) -> Theme:
        """Get theme by name, or default theme."""
        if name and name.lower() in self.themes:
            return self.themes[name.lower()]
        if "default" in self.themes:
            return self.themes["default"]
        # Return a minimal default theme
        return Theme(name="default", default="white", categories={})

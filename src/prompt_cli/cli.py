"""Command-line interface for prompt-cli."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prompt_cli.config.loader import load_config
from prompt_cli.editor.prompt import edit_command_line


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Arguments to parse (defaults to sys.argv[1:])

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        prog="prompt",
        description="Interactive command line editor with syntax highlighting",
        epilog="Example: prompt -- gcc -I/tmp/foo -o test main.c",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        metavar="FILE",
        help="Configuration file path (default: ~/.config/prompt/config.yaml)",
    )

    parser.add_argument(
        "--config-dir",
        type=Path,
        metavar="DIR",
        help="Drop-in configuration directory (default: ~/.config/prompt/conf.d/)",
    )

    parser.add_argument(
        "--theme",
        "-t",
        metavar="NAME",
        help="Theme to use",
    )

    parser.add_argument(
        "--granularity",
        "-g",
        type=int,
        metavar="LEVEL",
        help="Category map expansion level (0=none, default=full)",
    )

    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colors",
    )

    parser.add_argument(
        "--print",
        "-p",
        action="store_true",
        dest="print_result",
        help="Print the result to stdout on exit",
    )

    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version="%(prog)s 0.1.0",
    )

    parser.add_argument(
        "command",
        nargs="*",
        help="Command line to edit (use -- to separate from options)",
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point.

    Args:
        args: Command-line arguments

    Returns:
        Exit code
    """
    parsed = parse_args(args)

    # Build command line from arguments
    command_line = " ".join(parsed.command)

    if not command_line:
        print("Error: No command line provided", file=sys.stderr)
        print("Usage: prompt [options] -- <command line>", file=sys.stderr)
        return 1

    # Load configuration
    try:
        config = load_config(
            config_path=parsed.config,
            dropin_dir=parsed.config_dir,
        )
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    # Override config options
    if parsed.no_color:
        config.config.color = False

    # Run editor
    try:
        result = edit_command_line(
            command_line=command_line,
            config=config,
            theme=parsed.theme,
        )

        # Print result if requested
        if parsed.print_result:
            print(result)

        return 0

    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

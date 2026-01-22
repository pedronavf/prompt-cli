# prompt-cli

Interactive command line editor with syntax highlighting for compiler and build tool commands.

## Features

- **Syntax highlighting** - Color-coded display of command line flags based on regex patterns
- **Category-based coloring** - Group flags into categories (Includes, Libraries, Warnings, etc.)
- **Quote-aware parsing** - Properly handles quoted strings and embedded quotes
- **Duplicates mode** - Identify and manage duplicate flags
- **Lights-off mode** - Focus on specific flag categories by dimming others
- **Configurable key bindings** - Customize all keyboard shortcuts
- **Extensible validators** - File, directory, choice, and custom validators for autocompletion
- **Program-specific configs** - Different highlighting rules per compiler (GCC, Clang, etc.)

## Installation

```bash
pip install prompt-cli
```

## Usage

```bash
# Edit a GCC command line
prompt -- gcc -I/tmp/foo -L/lib -o test main.c

# With a specific config file
prompt --config ~/.config/prompt/gcc.yaml -- gcc -Wall -O2 main.c

# Print result on exit
prompt -p -- clang++ -std=c++20 -O3 main.cpp
```

## Key Bindings (default)

| Key | Action |
|-----|--------|
| Ctrl-A | Move to line start |
| Ctrl-E | Move to line end |
| Ctrl-W | Delete word |
| Alt-Backspace | Delete parameter |
| Ctrl-L | Toggle lights-off mode |
| Ctrl-Shift-D | Enter duplicates mode |
| Ctrl-Q | Quit and print |
| Enter | Quit and print |
| Escape | Quit without printing |

## Configuration

Configuration is stored in YAML format at `~/.config/prompt/config.yaml`.

Additional configs can be dropped in `~/.config/prompt/conf.d/`.

### Example Configuration

```yaml
categories:
  Includes:
    colors: ["blue", "bright cyan"]
  Libraries:
    colors: ["magenta"]

flags:
  - category: Includes
    regexps:
      - "-(I|isystem)(.*)"
    validator:
      type: directory

themes:
  default:
    default: "white"
    categories:
      Includes: "blue"
      Libraries: "magenta"

keybindings:
  normal:
    ctrl-a: move-line-start
    ctrl-q: quit -p
```

See `sample_configs/gcc.yaml` for a complete example.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src tests
mypy src
```

## License

MIT

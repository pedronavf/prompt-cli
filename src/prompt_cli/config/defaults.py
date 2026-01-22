"""Default configuration values."""

DEFAULT_CONFIG_YAML = """
config:
  color: true
  default_validator:
    type: file

categories:
  Includes:
    colors: ["blue", "bright cyan"]
  Libraries:
    colors: ["magenta", "bright magenta"]
  Outputs:
    colors: ["green", "bright green"]
  Warnings:
    colors: ["yellow"]
  Optimization:
    colors: ["cyan"]
  Debug:
    colors: ["red"]
  Architecture:
    colors: ["bright blue"]
  Default:
    colors: ["white"]

category_maps:
  Compiler:
    - Includes
    - Libraries
    - Outputs
    - Warnings
    - Optimization
    - Debug
    - Architecture

themes:
  default:
    default: "white"
    categories:
      Includes: "blue"
      Libraries: "magenta"
      Outputs: "green"
      Warnings: "yellow"
      Optimization: "cyan"
      Debug: "red"
      Architecture: "bright blue"
      Default: "white"
      "ui:cursor": "reverse"
      "ui:selection": "bold underline"
      "ui:duplicates": "bold red"
      "ui:duplicates-hidden": "dim"
      "ui:duplicates-selected": "bold yellow"
      "ui:duplicates-current": "bold reverse"

flags:
  - category: Includes
    regexps:
      - "-(I|isystem|idirafter|iprefix|iwithprefix|iwithprefixbefore)\\s*(.*)"
      - "--(include-with-prefix|include-with-prefix-before|include-with-prefix-after)\\s*(.*)"
    validator:
      type: directory
    help:
      - flag: "-I directory"
        description: "Add directory to include search path"
      - flag: "-isystem directory"
        description: "Add directory to system include search path"

  - category: Libraries
    regexps:
      - "-(L|library-path)\\s*(.*)"
      - "-(l)(.+)"
    validator:
      type: directory
    help:
      - flag: "-L directory"
        description: "Add directory to library search path"
      - flag: "-l name"
        description: "Link with library"

  - category: Outputs
    regexps:
      - "-(o)\\s*(.*)"
    validator:
      type: file
      extensions: [".o", ".out", ".exe", ""]
    help:
      - flag: "-o file"
        description: "Output file name"

  - category: Warnings
    regexps:
      - "-(W)(no-)?(.+)"
    validator:
      type: warnings
    help:
      - flag: "-Wwarning"
        description: "Enable warning"
      - flag: "-Wno-warning"
        description: "Disable warning"

  - category: Optimization
    regexps:
      - "-(O)(\\d|s|g|fast)?"
    validator:
      type: choice
      options: ["0", "1", "2", "3", "s", "g", "fast"]
    help:
      - flag: "-O level"
        description: "Optimization level"

  - category: Debug
    regexps:
      - "-(g)(\\d)?"
    validator:
      type: choice
      options: ["", "1", "2", "3"]
    help:
      - flag: "-g"
        description: "Generate debug information"

keybindings:
  normal:
    ctrl-a: move-line-start
    ctrl-e: move-line-end
    ctrl-b: move-char-left
    ctrl-f: move-char-right
    alt-b: move-word-left
    alt-f: move-word-right
    ctrl-p: move-up
    ctrl-n: move-down
    ctrl-d: delete-char
    ctrl-h: delete-char-left
    ctrl-w: delete-word-left
    alt-d: delete-word-right
    ctrl-k: delete-to-end
    ctrl-u: delete-to-start
    alt-backspace: delete-param
    ctrl-_: undo
    ctrl-y: paste
    ctrl-l: lights-off
    ctrl-shift-d: show-duplicates
    ctrl-q: "quit -p"
    ctrl-c: "quit -y"
    escape: "quit"
    enter: "quit -p"

  duplicates:
    left: duplicate-prev
    right: duplicate-next
    up: duplicate-previous-group
    down: duplicate-next-group
    space: duplicate-select
    a: duplicate-all
    n: duplicate-none
    k: duplicates-keep
    d: duplicates-delete
    f: duplicates-first
    escape: duplicates-exit
    enter: duplicates-exit
    q: duplicates-exit

aliases:
  q: quit
  qp: "quit -p"
  lo: lights-off
  dup: show-duplicates
"""

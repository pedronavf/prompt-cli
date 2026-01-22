"""Tests for the tokenizer module."""


from prompt_cli.core.tokenizer import (
    QuoteType,
    Token,
    detokenize,
    needs_quoting,
    rebuild_command,
    tokenize,
)


class TestTokenize:
    """Tests for tokenize function."""

    def test_simple_tokens(self):
        """Test tokenizing simple space-separated values."""
        tokens = tokenize("gcc -o test main.c")

        assert len(tokens) == 4
        assert tokens[0].value == "gcc"
        assert tokens[1].value == "-o"
        assert tokens[2].value == "test"
        assert tokens[3].value == "main.c"

    def test_flag_with_value(self):
        """Test tokenizing flag with attached value."""
        tokens = tokenize("gcc -I/tmp/foo")

        assert len(tokens) == 2
        assert tokens[0].value == "gcc"
        assert tokens[1].value == "-I/tmp/foo"

    def test_double_quoted_string(self):
        """Test tokenizing double-quoted string."""
        tokens = tokenize('gcc -DNAME="hello world" main.c')

        assert len(tokens) == 3
        assert tokens[0].value == "gcc"
        assert tokens[1].value == "-DNAME=hello world"
        assert tokens[1].quote_type == QuoteType.DOUBLE
        assert tokens[2].value == "main.c"

    def test_single_quoted_string(self):
        """Test tokenizing single-quoted string."""
        tokens = tokenize("gcc -DNAME='hello world' main.c")

        assert len(tokens) == 3
        assert tokens[1].value == "-DNAME=hello world"
        assert tokens[1].quote_type == QuoteType.SINGLE

    def test_embedded_quotes(self):
        """Test tokenizing embedded quoted section."""
        tokens = tokenize('-fname="this is a test"')

        assert len(tokens) == 1
        assert tokens[0].value == "-fname=this is a test"
        assert tokens[0].raw == '-fname="this is a test"'

    def test_escaped_quote(self):
        """Test tokenizing escaped quotes."""
        tokens = tokenize(r'echo "hello \"world\""')

        assert len(tokens) == 2
        assert tokens[1].value == 'hello "world"'

    def test_multiple_spaces(self):
        """Test that multiple spaces are handled correctly."""
        tokens = tokenize("gcc   -o   test")

        assert len(tokens) == 3
        assert tokens[0].value == "gcc"
        assert tokens[1].value == "-o"
        assert tokens[2].value == "test"

    def test_empty_string(self):
        """Test tokenizing empty string."""
        tokens = tokenize("")

        assert len(tokens) == 0

    def test_whitespace_only(self):
        """Test tokenizing whitespace-only string."""
        tokens = tokenize("   \t  ")

        assert len(tokens) == 0

    def test_token_positions(self):
        """Test that token positions are correct."""
        text = "gcc -o test"
        tokens = tokenize(text)

        assert tokens[0].start == 0
        assert tokens[0].end == 3
        assert text[tokens[0].start:tokens[0].end] == "gcc"

        assert tokens[1].start == 4
        assert tokens[1].end == 6
        assert text[tokens[1].start:tokens[1].end] == "-o"

    def test_quoted_token_positions(self):
        """Test positions with quoted strings."""
        text = 'gcc -D"FOO BAR"'
        tokens = tokenize(text)

        assert tokens[1].start == 4
        assert tokens[1].end == 15
        assert text[tokens[1].start:tokens[1].end] == '-D"FOO BAR"'


class TestDetokenize:
    """Tests for detokenize function."""

    def test_simple_detokenize(self):
        """Test detokenizing simple tokens."""
        tokens = tokenize("gcc -o test main.c")
        result = detokenize(tokens)

        assert result == "gcc -o test main.c"

    def test_preserves_quotes(self):
        """Test that detokenize preserves original quoting."""
        text = 'gcc -DNAME="hello world" main.c'
        tokens = tokenize(text)
        result = detokenize(tokens)

        assert result == text


class TestRebuildCommand:
    """Tests for rebuild_command function."""

    def test_simple_rebuild(self):
        """Test rebuilding simple command."""
        tokens = tokenize("gcc -o test")
        result = rebuild_command(tokens)

        assert result == "gcc -o test"

    def test_adds_quotes_when_needed(self):
        """Test that rebuild adds quotes when needed."""
        tokens = [
            Token(value="gcc", start=0, end=3, raw="gcc"),
            Token(value="hello world", start=4, end=15, raw="hello world"),
        ]
        result = rebuild_command(tokens)

        assert result == 'gcc "hello world"'


class TestNeedsQuoting:
    """Tests for needs_quoting function."""

    def test_simple_string(self):
        """Test that simple strings don't need quoting."""
        assert not needs_quoting("gcc")
        assert not needs_quoting("-o")
        assert not needs_quoting("test.c")

    def test_string_with_space(self):
        """Test that strings with spaces need quoting."""
        assert needs_quoting("hello world")

    def test_string_with_special_chars(self):
        """Test that strings with special chars need quoting."""
        assert needs_quoting("$HOME")
        assert needs_quoting("foo|bar")
        assert needs_quoting("a;b")

    def test_empty_string(self):
        """Test that empty strings need quoting."""
        assert needs_quoting("")

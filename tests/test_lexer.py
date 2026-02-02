"""Tests for the lexer module."""

import pytest

from prompt_cli.editor.lexer import CommandLineLexer


class TestLightsOffMode:
    """Tests for lights-off mode functionality."""

    def test_lights_off_initially_disabled(self, sample_config):
        """Test that lights-off is disabled by default."""
        lexer = CommandLineLexer(sample_config)

        assert lexer.lights_off is False
        assert lexer.lights_off_category is None

    def test_set_lights_off_enabled(self, sample_config):
        """Test setting lights-off mode enabled."""
        lexer = CommandLineLexer(sample_config)

        lexer.set_lights_off(True, "Includes")

        assert lexer.lights_off is True
        assert lexer.lights_off_category == "Includes"

    def test_set_lights_off_disabled(self, sample_config):
        """Test disabling lights-off mode."""
        lexer = CommandLineLexer(sample_config)
        lexer.set_lights_off(True, "Includes")

        lexer.set_lights_off(False)

        assert lexer.lights_off is False
        assert lexer.lights_off_category is None

    def test_toggle_lights_off_on(self, sample_config):
        """Test toggling lights-off mode on."""
        lexer = CommandLineLexer(sample_config)

        lexer.toggle_lights_off("Includes")

        assert lexer.lights_off is True
        assert lexer.lights_off_category == "Includes"

    def test_toggle_lights_off_off(self, sample_config):
        """Test toggling lights-off mode off."""
        lexer = CommandLineLexer(sample_config)
        lexer.toggle_lights_off("Includes")

        lexer.toggle_lights_off("Includes")

        assert lexer.lights_off is False
        assert lexer.lights_off_category is None

    def test_toggle_lights_off_different_category(self, sample_config):
        """Test toggling to different category switches instead of turning off."""
        lexer = CommandLineLexer(sample_config)
        lexer.toggle_lights_off("Includes")

        # Toggle with different category should switch, not turn off
        lexer.toggle_lights_off("Libraries")

        assert lexer.lights_off is True
        assert lexer.lights_off_category == "Libraries"

    def test_toggle_lights_off_no_category(self, sample_config):
        """Test toggling lights-off with no category."""
        lexer = CommandLineLexer(sample_config)

        lexer.toggle_lights_off(None)

        assert lexer.lights_off is True
        assert lexer.lights_off_category is None


class TestLexerStyles:
    """Tests for lexer style building."""

    def test_styles_include_lights_off(self, sample_config):
        """Test that styles include lights-off classes."""
        lexer = CommandLineLexer(sample_config)
        styles = lexer.get_style_dict()

        assert "class:lights-off-dim" in styles
        assert "class:lights-off-highlight" in styles

    def test_styles_include_duplicates(self, sample_config):
        """Test that styles include duplicates classes."""
        lexer = CommandLineLexer(sample_config)
        styles = lexer.get_style_dict()

        assert "class:duplicate" in styles
        assert "class:duplicate-current" in styles
        assert "class:duplicate-selected" in styles
        assert "class:duplicate-dim" in styles

    def test_styles_include_default(self, sample_config):
        """Test that styles include default class."""
        lexer = CommandLineLexer(sample_config)
        styles = lexer.get_style_dict()

        assert "class:default" in styles

    def test_category_to_class(self, sample_config):
        """Test category name to class conversion."""
        lexer = CommandLineLexer(sample_config)

        assert lexer._category_to_class("Includes") == "class:includes"
        assert lexer._category_to_class("ui:duplicates") == "class:ui-duplicates"
        assert lexer._category_to_class("My Category") == "class:my-category"

"""Tests for duplicates mode."""

import pytest

from prompt_cli.core.tokenizer import tokenize
from prompt_cli.editor.modes.duplicates import DuplicateGroup, DuplicatesMode


class MockEditor:
    """Mock editor for testing duplicates mode."""

    def __init__(self, text: str, duplicates: dict[str, list[int]]):
        self.text = text
        self._duplicates = duplicates

    def get_tokens(self):
        return tokenize(self.text)

    def get_match_results(self):
        # Not needed for basic tests
        return []

    @property
    def buffer(self):
        class MockBuffer:
            def __init__(self, editor):
                self._editor = editor
                self.cursor_position = 0

            @property
            def text(self):
                return self._editor.text

            @text.setter
            def text(self, value):
                self._editor.text = value

        return MockBuffer(self)

    @property
    def lexer(self):
        class MockLexer:
            def __init__(self, editor):
                self._editor = editor

            @property
            def matcher(self):
                class MockMatcher:
                    def __init__(self, editor):
                        self._editor = editor

                    def find_duplicates(self, results):
                        return self._editor._duplicates

                return MockMatcher(self._editor)

        return MockLexer(self)


class TestDuplicateGroup:
    """Tests for DuplicateGroup class."""

    def test_current_result_index(self):
        """Test getting current result index."""
        group = DuplicateGroup(category="Includes", indices=[1, 3, 5])

        assert group.current_result_index == 1  # First index

        group.current_index = 1
        assert group.current_result_index == 3

        group.current_index = 2
        assert group.current_result_index == 5

    def test_empty_indices(self):
        """Test handling of empty indices."""
        group = DuplicateGroup(category="Test", indices=[])

        assert group.current_result_index == -1


class TestDuplicatesMode:
    """Tests for DuplicatesMode class."""

    def test_init_creates_groups(self):
        """Test that initialization creates groups from duplicates."""
        editor = MockEditor("gcc -I/a -I/b -L/lib", {"Includes": [1, 2]})
        duplicates = {"Includes": [1, 2], "Libraries": [3]}

        mode = DuplicatesMode(editor, duplicates)

        assert len(mode.groups) == 2
        assert mode.groups[0].category == "Includes"
        assert mode.groups[0].indices == [1, 2]

    def test_move_next_within_group(self):
        """Test moving to next duplicate within current group."""
        editor = MockEditor("gcc -I/a -I/b -I/c", {"Includes": [1, 2, 3]})
        mode = DuplicatesMode(editor, {"Includes": [1, 2, 3]})

        assert mode.current_group.current_index == 0

        mode.move_next()
        assert mode.current_group.current_index == 1

        mode.move_next()
        assert mode.current_group.current_index == 2

        # Wraps around
        mode.move_next()
        assert mode.current_group.current_index == 0

    def test_move_prev_within_group(self):
        """Test moving to previous duplicate within current group."""
        editor = MockEditor("gcc -I/a -I/b -I/c", {"Includes": [1, 2, 3]})
        mode = DuplicatesMode(editor, {"Includes": [1, 2, 3]})

        # Wraps from start to end
        mode.move_prev()
        assert mode.current_group.current_index == 2

        mode.move_prev()
        assert mode.current_group.current_index == 1

    def test_next_group(self):
        """Test moving to next group."""
        editor = MockEditor("gcc -I/a -I/b -L/lib -L/usr/lib", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2], "Libraries": [3, 4]})

        assert mode._current_group_index == 0

        mode.next_group()
        assert mode._current_group_index == 1

        # Wraps around
        mode.next_group()
        assert mode._current_group_index == 0

    def test_prev_group(self):
        """Test moving to previous group."""
        editor = MockEditor("gcc -I/a -I/b -L/lib -L/usr/lib", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2], "Libraries": [3, 4]})

        # Wraps from first to last
        mode.prev_group()
        assert mode._current_group_index == 1

        mode.prev_group()
        assert mode._current_group_index == 0

    def test_select_deselect_group(self):
        """Test selecting and deselecting groups."""
        editor = MockEditor("gcc -I/a -I/b", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2]})

        assert not mode.current_group.selected

        mode.select_group()
        assert mode.current_group.selected

        mode.deselect_group()
        assert not mode.current_group.selected

    def test_select_all_none(self):
        """Test select all and deselect all."""
        editor = MockEditor("gcc -I/a -I/b -L/lib -L/usr", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2], "Libraries": [3, 4]})

        mode.select_all()
        assert all(g.selected for g in mode.groups)

        mode.deselect_all()
        assert not any(g.selected for g in mode.groups)

    def test_get_highlighted_indices(self):
        """Test getting all duplicate indices."""
        editor = MockEditor("gcc -I/a -I/b -L/lib -L/usr", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2], "Libraries": [3, 4]})

        indices = mode.get_highlighted_indices()

        assert indices == {1, 2, 3, 4}

    def test_get_selected_indices(self):
        """Test getting indices from selected groups."""
        editor = MockEditor("gcc -I/a -I/b -L/lib -L/usr", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2], "Libraries": [3, 4]})

        # No selection initially
        assert mode.get_selected_indices() == set()

        # Select first group
        mode.select_group()
        assert mode.get_selected_indices() == {1, 2}

        # Select all
        mode.select_all()
        assert mode.get_selected_indices() == {1, 2, 3, 4}

    def test_get_current_index(self):
        """Test getting current duplicate index."""
        editor = MockEditor("gcc -I/a -I/b", {})
        mode = DuplicatesMode(editor, {"Includes": [1, 2]})

        assert mode.get_current_index() == 1

        mode.move_next()
        assert mode.get_current_index() == 2

    def test_keep_current(self):
        """Test keeping current duplicate and deleting others."""
        editor = MockEditor("gcc -I/a -I/b -I/c", {"Includes": [1, 2, 3]})
        mode = DuplicatesMode(editor, {"Includes": [1, 2, 3]})

        # Move to second duplicate
        mode.move_next()
        assert mode.current_group.current_result_index == 2

        mode.keep_current()

        # Only -I/b should remain (index 2)
        assert "-I/a" not in editor.text
        assert "-I/b" in editor.text
        assert "-I/c" not in editor.text

    def test_keep_first(self):
        """Test keeping first duplicate in each group."""
        editor = MockEditor("gcc -I/a -I/b -I/c", {"Includes": [1, 2, 3]})
        mode = DuplicatesMode(editor, {"Includes": [1, 2, 3]})

        mode.keep_first()

        # Only -I/a should remain (first one)
        assert "-I/a" in editor.text
        assert "-I/b" not in editor.text
        assert "-I/c" not in editor.text

    def test_delete_current(self):
        """Test deleting current duplicate."""
        editor = MockEditor("gcc -I/a -I/b -I/c", {"Includes": [1, 2, 3]})
        mode = DuplicatesMode(editor, {"Includes": [1, 2, 3]})

        mode.delete_current()

        # First one should be gone
        assert "-I/a" not in editor.text
        assert "-I/b" in editor.text
        assert "-I/c" in editor.text

    def test_delete_current_keeps_at_least_one(self):
        """Test that delete_current won't delete the last duplicate."""
        editor = MockEditor("gcc -I/a", {"Includes": [1]})
        mode = DuplicatesMode(editor, {"Includes": [1]})

        mode.delete_current()

        # Should still have the flag
        assert "-I/a" in editor.text

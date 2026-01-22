"""Duplicates mode for managing repeated flags."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prompt_cli.editor.prompt import CommandLineEditor


@dataclass
class DuplicateGroup:
    """A group of duplicate flags."""

    category: str
    indices: list[int]  # Indices in the match results
    selected: bool = False
    current_index: int = 0  # Index within indices list

    @property
    def current_result_index(self) -> int:
        """Get the current index in the match results."""
        if self.indices:
            return self.indices[self.current_index]
        return -1


class DuplicatesMode:
    """Mode for handling duplicate flags."""

    def __init__(self, editor: CommandLineEditor, duplicates: dict[str, list[int]]) -> None:
        """Initialize duplicates mode.

        Args:
            editor: The editor instance
            duplicates: Dict mapping category to list of indices with duplicates
        """
        self.editor = editor
        self._groups: list[DuplicateGroup] = []
        self._current_group_index = 0

        # Create groups from duplicates
        for category, indices in duplicates.items():
            self._groups.append(DuplicateGroup(category=category, indices=indices))

        # Sort groups by first occurrence
        self._groups.sort(key=lambda g: g.indices[0] if g.indices else 0)

    @property
    def current_group(self) -> DuplicateGroup | None:
        """Get the current group."""
        if 0 <= self._current_group_index < len(self._groups):
            return self._groups[self._current_group_index]
        return None

    @property
    def groups(self) -> list[DuplicateGroup]:
        """Get all groups."""
        return self._groups

    @property
    def selected_groups(self) -> list[DuplicateGroup]:
        """Get selected groups."""
        return [g for g in self._groups if g.selected]

    def move_next(self) -> None:
        """Move to next duplicate in current group."""
        group = self.current_group
        if group and group.indices:
            group.current_index = (group.current_index + 1) % len(group.indices)
            self._move_cursor_to_current()

    def move_prev(self) -> None:
        """Move to previous duplicate in current group."""
        group = self.current_group
        if group and group.indices:
            group.current_index = (group.current_index - 1) % len(group.indices)
            self._move_cursor_to_current()

    def next_group(self) -> None:
        """Move to next duplicate group."""
        if self._groups:
            self._current_group_index = (self._current_group_index + 1) % len(self._groups)
            self._move_cursor_to_current()

    def prev_group(self) -> None:
        """Move to previous duplicate group."""
        if self._groups:
            self._current_group_index = (self._current_group_index - 1) % len(self._groups)
            self._move_cursor_to_current()

    def select_group(self) -> None:
        """Select current group."""
        group = self.current_group
        if group:
            group.selected = True

    def deselect_group(self) -> None:
        """Deselect current group."""
        group = self.current_group
        if group:
            group.selected = False

    def select_all(self) -> None:
        """Select all groups."""
        for group in self._groups:
            group.selected = True

    def deselect_all(self) -> None:
        """Deselect all groups."""
        for group in self._groups:
            group.selected = False

    def keep_current(self) -> None:
        """Keep current duplicate, delete others in selected groups."""
        groups_to_process = self.selected_groups or ([self.current_group] if self.current_group else [])

        indices_to_delete: set[int] = set()
        for group in groups_to_process:
            # Keep the current one, delete the rest
            current_idx = group.current_result_index
            for idx in group.indices:
                if idx != current_idx:
                    indices_to_delete.add(idx)

        self._delete_indices(indices_to_delete)

    def delete_current(self) -> None:
        """Delete current duplicate (must keep at least 1)."""
        group = self.current_group
        if not group or len(group.indices) <= 1:
            return  # Can't delete the last one

        idx_to_delete = group.current_result_index

        # Update group's indices
        group.indices.remove(idx_to_delete)

        # Adjust current index if needed
        if group.current_index >= len(group.indices):
            group.current_index = len(group.indices) - 1

        self._delete_indices({idx_to_delete})

    def keep_first(self) -> None:
        """Keep first duplicate in selected groups."""
        groups_to_process = self.selected_groups or ([self.current_group] if self.current_group else [])

        indices_to_delete: set[int] = set()
        for group in groups_to_process:
            if group.indices:
                # Keep first, delete rest
                for idx in group.indices[1:]:
                    indices_to_delete.add(idx)

        self._delete_indices(indices_to_delete)

    def _delete_indices(self, indices: set[int]) -> None:
        """Delete tokens at the given indices."""
        if not indices:
            return

        # Get tokens and rebuild without the deleted ones
        tokens = self.editor.get_tokens()
        new_parts: list[str] = []

        for i, token in enumerate(tokens):
            if i not in indices:
                new_parts.append(token.raw)

        # Update buffer
        self.editor.buffer.text = " ".join(new_parts)

        # Refresh duplicates
        self._refresh_duplicates()

    def _refresh_duplicates(self) -> None:
        """Refresh duplicate groups after deletion."""
        results = self.editor.get_match_results()

        # Find new duplicates
        matcher = self.editor.lexer.matcher
        duplicates = matcher.find_duplicates(results)

        # Rebuild groups
        old_selected = {g.category for g in self._groups if g.selected}
        self._groups = []

        for category, indices in duplicates.items():
            group = DuplicateGroup(category=category, indices=indices)
            group.selected = category in old_selected
            self._groups.append(group)

        self._groups.sort(key=lambda g: g.indices[0] if g.indices else 0)

        # Adjust current group index
        if self._current_group_index >= len(self._groups):
            self._current_group_index = max(0, len(self._groups) - 1)

    def _move_cursor_to_current(self) -> None:
        """Move editor cursor to current duplicate."""
        group = self.current_group
        if not group:
            return

        result_index = group.current_result_index
        if result_index < 0:
            return

        tokens = self.editor.get_tokens()
        if result_index < len(tokens):
            self.editor.buffer.cursor_position = tokens[result_index].start

    def get_highlighted_indices(self) -> set[int]:
        """Get indices that should be highlighted as duplicates."""
        indices: set[int] = set()
        for group in self._groups:
            indices.update(group.indices)
        return indices

    def get_current_index(self) -> int | None:
        """Get the current duplicate index."""
        group = self.current_group
        if group:
            return group.current_result_index
        return None

    def get_selected_indices(self) -> set[int]:
        """Get indices in selected groups."""
        indices: set[int] = set()
        for group in self._groups:
            if group.selected:
                indices.update(group.indices)
        return indices

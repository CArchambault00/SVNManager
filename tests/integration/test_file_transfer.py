"""Tests for file_transfer (move files between treeviews)."""

from unittest.mock import MagicMock, patch

import pytest


def _make_tree(tk_root, rows=None):
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    for col in ("Status", "Version", "File", "Lock Date"):
        tree.heading(col, text=col)
    for row in rows or []:
        tree.insert("", "end", values=row)
    return tree


def test_add_selected_to_main_treeview(tk_root):
    from file_transfer import add_selected_to_main_treeview

    source = _make_tree(
        tk_root,
        [
            ("locked", "1", "webpage/a.asp", "2026-01-01"),
            ("locked", "2", "webpage/b.asp", "2026-01-02"),
        ],
    )
    main = _make_tree(tk_root, [("locked", "1", "webpage/a.asp", "2026-01-01")])

    # select both; a already in main, b should move
    for item in source.get_children():
        source.selection_add(item)

    add_selected_to_main_treeview(source, main)

    main_files = {main.item(i, "values")[2] for i in main.get_children()}
    assert main_files == {"webpage/a.asp", "webpage/b.asp"}
    assert source.get_children() == ()


def test_add_selected_noop_without_selection(tk_root):
    from file_transfer import add_selected_to_main_treeview

    source = _make_tree(tk_root, [("locked", "1", "webpage/a.asp", "")])
    main = _make_tree(tk_root)
    add_selected_to_main_treeview(source, main)
    assert len(source.get_children()) == 1
    assert len(main.get_children()) == 0


def test_remove_selected_without_locked_view(tk_root):
    from file_transfer import remove_and_return_selected_files

    main = _make_tree(
        tk_root,
        [
            ("locked", "1", "webpage/a.asp", ""),
            ("locked", "2", "webpage/b.asp", ""),
        ],
    )
    item = main.get_children()[0]
    main.selection_set(item)
    remove_and_return_selected_files(main, None)
    assert [main.item(i, "values")[2] for i in main.get_children()] == ["webpage/b.asp"]


def test_remove_returns_to_locked_if_locked_by_user(tk_root, tmp_appdata, sample_config, monkeypatch):
    from file_transfer import remove_and_return_selected_files

    main = _make_tree(tk_root, [("locked", "1", "webpage/a.asp", "d")])
    locked = _make_tree(tk_root)
    item = main.get_children()[0]
    main.selection_set(item)

    monkeypatch.setattr(
        "file_transfer.get_file_info",
        MagicMock(return_value=(True, "tester", "1", "d")),
    )
    remove_and_return_selected_files(main, locked)

    assert len(main.get_children()) == 0
    assert locked.item(locked.get_children()[0], "values")[2] == "webpage/a.asp"


def test_remove_does_not_return_if_not_locked_by_user(tk_root, tmp_appdata, sample_config, monkeypatch):
    from file_transfer import remove_and_return_selected_files

    main = _make_tree(tk_root, [("unlocked", "1", "webpage/a.asp", "")])
    locked = _make_tree(tk_root)
    main.selection_set(main.get_children()[0])
    monkeypatch.setattr(
        "file_transfer.get_file_info",
        MagicMock(return_value=(False, "", "1", "")),
    )
    remove_and_return_selected_files(main, locked)
    assert len(main.get_children()) == 0
    assert len(locked.get_children()) == 0

"""Unit tests for multi-file transfer helpers."""

from file_transfer import (
    remove_and_return_selected_files,
    prune_locked_files_already_in_main,
    _is_user_locked_row,
)


def test_is_user_locked_row():
    assert _is_user_locked_row(("locked", "1", "a.asp", "")) is True
    assert _is_user_locked_row(("unlocked", "1", "a.asp", "")) is False
    assert _is_user_locked_row(("@locked - bob", "1", "a.asp", "")) is False


def test_remove_and_return_uses_status_column(tk_root):
    from tkinter import ttk

    main = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    locked = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")

    a = main.insert("", "end", values=("locked", "10", "webpage/a.asp", "d"))
    b = main.insert("", "end", values=("unlocked", "11", "webpage/b.asp", ""))
    main.selection_set((a, b))

    remove_and_return_selected_files(main, locked)

    assert list(main.get_children()) == []
    locked_paths = [locked.item(i, "values")[2] for i in locked.get_children()]
    assert locked_paths == ["webpage/a.asp"]


def test_prune_locked_files_already_in_main(tk_root):
    from tkinter import ttk

    main = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    locked = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")

    main.insert("", "end", values=("locked", "10", "webpage/a.asp", "d"))
    locked.insert("", "end", values=("locked", "10", "webpage/a.asp", "d"))
    locked.insert("", "end", values=("locked", "11", "webpage/c.asp", "d"))

    prune_locked_files_already_in_main(locked, main)
    paths = [locked.item(i, "values")[2] for i in locked.get_children()]
    assert paths == ["webpage/c.asp"]

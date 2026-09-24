"""Tests for busy_ops fetch/apply helpers and busy wrappers."""

from unittest.mock import MagicMock
from types import SimpleNamespace

import busy_ops as bo


def test_apply_locked_files_to_tree(tk_root):
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("a", "b", "c", "d"), show="headings")
    bo.apply_locked_files_to_tree(
        tree,
        [("webpage/a.asp", "1", "2026-01-01"), ("webpage/b.asp", "2", "2026-01-02")],
        exclude_paths={"webpage/a.asp"},
    )
    paths = [tree.item(i, "values")[2] for i in tree.get_children()]
    assert paths == ["webpage/b.asp"]


def test_apply_patches_to_tree(tk_root, monkeypatch):
    from tkinter import ttk
    import patches_operations as po

    tree = ttk.Treeview(
        tk_root,
        columns=("Name", "Comments", "Size", "User", "Date", "CL"),
        show="headings",
    )
    patches = [
        {
            "NAME": "S1.0.0001-W0",
            "COMMENTS": "hello\nworld",
            "PATCH_SIZE": 1,
            "USER_ID": "u",
            "CREATION_DATE": "2026-01-01",
            "CHECK_LIST_COUNT": 0,
            "PATCH_ID": 1,
        }
    ]
    bo.apply_patches_to_tree(tree, patches)
    assert "S1.0.0001-W0" in po.patch_info_dict
    assert tree.get_children()
    assert "hello world" in tree.item(tree.get_children()[0], "values")[1]


def test_load_patches_busy_invokes_run(tk_root, monkeypatch):
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Name",), show="headings")
    called = {}

    def fake_run(parent, title, work_fn, initial_status="Please wait..."):
        called["title"] = title
        work_fn(lambda _m: None)

    monkeypatch.setattr(bo, "run_with_busy_dialog", fake_run)
    monkeypatch.setattr(bo, "fetch_patches", MagicMock(return_value=[]))
    monkeypatch.setattr(bo, "call_on_main_thread", lambda fn: fn())

    bo.load_patches_busy(tk_root, tree, False, "S")
    assert called["title"] == "Loading patches"


def test_lock_unlock_busy_invokes_run(tk_root, monkeypatch):
    called = {}

    def fake_run(parent, title, work_fn, initial_status="Please wait..."):
        called["title"] = title
        work_fn(lambda _m: None)

    monkeypatch.setattr(bo, "run_with_busy_dialog", fake_run)
    monkeypatch.setattr("svn_operations.lock_files", MagicMock())

    tree = MagicMock()
    bo.lock_unlock_busy(tk_root, ["a.asp"], tree, lock=True)
    assert "Locking" in called["title"]


def test_remove_patch_busy_skips_when_cancelled(tk_root, monkeypatch, mock_messagebox):
    mock_messagebox.askyesno.return_value = False
    remove = MagicMock()
    monkeypatch.setattr("patches_operations.remove_patch", remove)
    monkeypatch.setattr(bo, "run_with_busy_dialog", MagicMock())

    bo.remove_patch_busy(tk_root, {"NAME": "S1", "PATCH_ID": 1})
    bo.run_with_busy_dialog.assert_not_called()
    remove.assert_not_called()

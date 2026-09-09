"""Tests for buttons_function orchestration and DnD handle_drop."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def files_tree(tk_root):
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    for col in ("Status", "Version", "File", "Lock Date"):
        tree.heading(col, text=col)
    a = tree.insert("", "end", values=("locked", "1", "webpage/a.asp", "d"))
    b = tree.insert("", "end", values=("unlocked", "2", "webpage/b.asp", ""))
    return tree, a, b


def test_lock_unlock_selected_files(files_tree, monkeypatch):
    import buttons_function as bf

    tree, a, b = files_tree
    tree.selection_set(a)
    lock = MagicMock()
    unlock = MagicMock()
    monkeypatch.setattr(bf, "lock_files", lock)
    monkeypatch.setattr(bf, "unlock_files", unlock)

    bf.lock_selected_files(tree)
    lock.assert_called_once_with(["webpage/a.asp"], tree)

    tree.selection_set(a, b)
    bf.unlock_selected_files(tree)
    unlock.assert_called_once_with(["webpage/a.asp", "webpage/b.asp"], tree)


def test_check_files_is_present(files_tree):
    import buttons_function as bf

    tree, _, _ = files_tree
    assert bf.check_files_is_present(tree, ["webpage/a.asp"]) is True
    assert bf.check_files_is_present(tree, ["webpage/missing.asp"]) is False


def test_select_and_deselect_all(files_tree):
    import buttons_function as bf

    tree, a, b = files_tree
    event = SimpleNamespace(x=0, y=0)
    bf.select_all_rows(event, tree)
    assert set(tree.selection()) == {a, b}

    tree.identify_region = MagicMock(return_value="cell")
    tree.identify_row = MagicMock(return_value="")
    bf.deselect_all_rows(event, tree)
    assert tree.selection() == ()


def test_deselect_ignores_heading_click(files_tree):
    import buttons_function as bf

    tree, a, _ = files_tree
    tree.selection_set(a)
    tree.identify_region = MagicMock(return_value="heading")
    event = SimpleNamespace(x=10, y=5)
    bf.deselect_all_rows(event, tree)
    assert a in tree.selection()


def test_insert_next_version(tk_root, monkeypatch):
    import tkinter as tk
    import buttons_function as bf

    entry = tk.Entry(tk_root)
    monkeypatch.setattr(bf, "next_version", MagicMock(return_value="1.0.0099-"))
    bf.insert_next_version("S", entry)
    assert entry.get() == "1.0.0099-"


def test_modify_patch_success_and_no_selection(mock_messagebox, monkeypatch):
    import buttons_function as bf

    info = {"NAME": "S1.0.0001-W0", "PATCH_ID": 1}
    monkeypatch.setattr(bf, "get_full_patch_info", MagicMock(return_value=info))
    set_sel = MagicMock()
    monkeypatch.setattr(bf, "set_selected_patch", set_sel)
    switch = MagicMock()

    bf.modify_patch([["S1.0.0001-W0"]], switch)
    set_sel.assert_called_once_with(info)
    switch.assert_called_once_with(info)

    bf.modify_patch([], switch)
    mock_messagebox.showwarning.assert_called()


def test_build_and_view_patch_files(monkeypatch):
    import buttons_function as bf

    info = {"NAME": "S1.0.0001-W0", "PATCH_ID": 1}
    monkeypatch.setattr(bf, "get_full_patch_info", MagicMock(return_value=info))
    build = MagicMock()
    view = MagicMock()
    monkeypatch.setattr(bf, "build_patch", build)
    monkeypatch.setattr(bf, "view_files_from_patch", view)

    bf.build_existing_patch([["S1.0.0001-W0"]])
    build.assert_called_once_with(info)
    bf.view_patch_files([["S1.0.0001-W0"]])
    view.assert_called_once_with(info)


def test_view_selected_file_native_diff(files_tree, mock_messagebox, monkeypatch):
    import buttons_function as bf

    tree, a, b = files_tree
    view = MagicMock()
    monkeypatch.setattr("svn_operations.view_file_native_diff", view)

    tree.selection_set(a, b)
    bf.view_selected_file_native_diff(tree)
    mock_messagebox.showwarning.assert_called()

    tree.selection_set(a)
    bf.view_selected_file_native_diff(tree)
    view.assert_called_once_with("webpage/a.asp")


def test_remove_selected_patch(tk_root, mock_messagebox, monkeypatch):
    import buttons_function as bf
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Name",), show="headings")
    iid = tree.insert("", "end", values=("S1.0.0001-W0",))
    tree.selection_set(iid)

    info = {"NAME": "S1.0.0001-W0", "PATCH_ID": 1}
    monkeypatch.setattr(bf, "get_full_patch_info", MagicMock(return_value=info))
    monkeypatch.setattr("patches_operations.remove_patch", MagicMock(return_value=True))

    bf.remove_selected_patch(tree)
    assert tree.get_children() == ()


def test_open_file_location(files_tree, tmp_appdata, sample_config, tmp_path, mock_messagebox, monkeypatch):
    import buttons_function as bf

    tree, a, _ = files_tree
    tree.selection_set(a)

    wc = tmp_path / "wc"
    target = wc / "webpage"
    target.mkdir(parents=True)
    (target / "a.asp").write_text("x", encoding="utf-8")

    def run(args, *a, **kwargs):
        return MagicMock(returncode=0, stderr="", stdout=str(wc).replace("\\", "/") + "\n")

    monkeypatch.setattr(bf.subprocess, "run", run)
    popen = MagicMock()
    monkeypatch.setattr(bf.subprocess, "Popen", popen)

    bf.open_file_location(tree)
    popen.assert_called()


def test_handle_drop_adds_files(tk_root, tmp_appdata, sample_config, tmp_path, mock_messagebox, monkeypatch):
    import buttons_function as bf
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    wc = tmp_path / "wc"
    page = wc / "webpage"
    page.mkdir(parents=True)
    dropped = page / "new.asp"
    dropped.write_text("hi", encoding="utf-8")
    wc_norm = str(wc.resolve()).replace("\\", "/")
    dropped_norm = str(dropped.resolve()).replace("\\", "/")

    # Tk DnD paths are often brace-wrapped
    event = SimpleNamespace(data="{" + str(dropped.resolve()) + "}")

    def run(args, *a, **kwargs):
        return MagicMock(returncode=0, stderr="", stdout=wc_norm + "\n")

    def rel(path):
        path = str(path).replace("\\", "/")
        if path.rstrip("/") == wc_norm.rstrip("/"):
            return ""
        if path.startswith(wc_norm):
            return path[len(wc_norm) :].lstrip("/")
        return ""

    monkeypatch.setattr(bf.subprocess, "run", run)
    monkeypatch.setattr("svn_operations.get_relative_path", rel)
    monkeypatch.setattr(
        bf,
        "load_config",
        MagicMock(return_value={"svn_path": str(wc.resolve()), "username": "tester"}),
    )
    monkeypatch.setattr(
        bf,
        "get_file_info_batch",
        MagicMock(return_value={"webpage/new.asp": (True, "tester", "5", "2026-01-01")}),
    )
    monkeypatch.setattr(bf.os.path, "isfile", lambda p: str(p).replace("\\", "/").endswith("new.asp"))
    monkeypatch.setattr(bf.os.path, "isdir", lambda p: False)

    bf.handle_drop(event, tree)

    files = [tree.item(i, "values")[2] for i in tree.get_children()]
    assert "webpage/new.asp" in files, f"got {files}, outside={mock_messagebox.showerror.called}"


def test_show_files_outside_svn_error(mock_messagebox):
    import buttons_function as bf

    bf._show_files_outside_svn_error([f"f{i}" for i in range(25)])
    args = mock_messagebox.showerror.call_args
    assert "...and 5 more files" in args[0][1]

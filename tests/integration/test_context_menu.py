"""Tests for context menu helpers and menu item wiring."""

from unittest.mock import MagicMock

import pytest


def _files_tree(tk_root, rows):
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    for row in rows:
        tree.insert("", "end", values=row)
    return tree


def _patches_tree(tk_root, names):
    from tkinter import ttk

    tree = ttk.Treeview(
        tk_root,
        columns=("Name", "Comments", "Size", "User", "Date", "Checklist"),
        show="headings",
    )
    for name in names:
        tree.insert("", "end", values=(name, "c", 1, "u", "d", 0))
    return tree


def test_create_files_menu_lock_unlock_labels(tk_root, monkeypatch):
    import tkinter as tk
    from context_menu import ContextMenuManager

    monkeypatch.setattr(tk.Menu, "post", MagicMock())
    mgr = ContextMenuManager()
    tree = _files_tree(tk_root, [("locked", "1", "webpage/a.asp", "")])
    menu = mgr.create_files_menu(tree, menu_name="lock_unlock")
    assert menu is not None

    tree.selection_set(tree.get_children()[0])
    tree.event_generate("<Button-3>", x=5, y=5, rootx=10, rooty=10)
    labels = [
        menu.entrycget(i, "label")
        for i in range(menu.index("end") + 1)
        if menu.type(i) != "separator"
    ]
    assert "Lock selected files" in labels
    assert "Unlock selected files" in labels
    assert "View Diff" in labels


def test_create_files_menu_locked_files_add_to_patch(tk_root, monkeypatch):
    import tkinter as tk
    from context_menu import ContextMenuManager

    monkeypatch.setattr(tk.Menu, "post", MagicMock())
    mgr = ContextMenuManager()
    tree = _files_tree(tk_root, [("locked", "1", "webpage/a.asp", "")])
    menu = mgr.create_files_menu(tree, menu_name="locked_files")
    tree.selection_set(tree.get_children()[0])
    tree.event_generate("<Button-3>", x=5, y=5, rootx=10, rooty=10)
    labels = [
        menu.entrycget(i, "label")
        for i in range(menu.index("end") + 1)
        if menu.type(i) != "separator"
    ]
    assert "Add to Patch" in labels


def test_create_patches_menu_labels(tk_root, monkeypatch):
    import tkinter as tk
    from context_menu import ContextMenuManager

    monkeypatch.setattr(tk.Menu, "post", MagicMock())
    mgr = ContextMenuManager()
    tree = _patches_tree(tk_root, ["S1.0.0001-W0"])
    menu = mgr.create_patches_menu(tree, switch_callback=MagicMock())
    tree.selection_set(tree.get_children()[0])
    tree.event_generate("<Button-3>", x=5, y=5, rootx=10, rooty=10)
    labels = [
        menu.entrycget(i, "label")
        for i in range(menu.index("end") + 1)
        if menu.type(i) != "separator"
    ]
    assert "Modify Patch" in labels
    assert "Build Patch" in labels
    assert "View Patch Details" in labels
    assert "Edit Description" in labels
    assert "Remove Patch" in labels


def test_add_to_main_and_remove_from_patch(tk_root, tmp_appdata, sample_config, monkeypatch):
    from context_menu import ContextMenuManager
    import tkinter as tk

    mgr = ContextMenuManager()
    root = tk_root
    container = tk.Frame(root)
    container.pack()

    # Mimic structure: LabelFrames with treeviews that find helpers can locate
    # Use direct monkeypatch of find helpers instead for stability
    main = _files_tree(root, [])
    locked = _files_tree(root, [("locked", "1", "webpage/a.asp", "d")])
    locked.selection_set(locked.get_children()[0])

    monkeypatch.setattr(mgr, "_find_main_treeview", MagicMock(return_value=main))
    mgr._add_to_main_treeview(locked)
    assert [main.item(i, "values")[2] for i in main.get_children()] == ["webpage/a.asp"]
    assert locked.get_children() == ()

    main.selection_set(main.get_children()[0])
    monkeypatch.setattr(mgr, "_find_locked_files_treeview", MagicMock(return_value=locked))
    monkeypatch.setattr("context_menu.get_file_info", MagicMock(return_value=(True, "tester", "1", "d")))
    mgr._remove_from_patch(main)
    assert main.get_children() == ()
    assert [locked.item(i, "values")[2] for i in locked.get_children()] == ["webpage/a.asp"]


def test_build_view_remove_patch_handlers(tk_root, mock_messagebox, monkeypatch):
    from context_menu import ContextMenuManager
    import patches_operations as po

    info = {
        "NAME": "S1.0.0001-W0",
        "PATCH_ID": 1,
        "COMMENTS": "desc",
        "USER_ID": "tester",
        "CREATION_DATE": "2026-01-01",
    }
    po.patch_info_dict["S1.0.0001-W0"] = info

    mgr = ContextMenuManager()
    tree = _patches_tree(tk_root, ["S1.0.0001-W0"])
    tree.selection_set(tree.get_children()[0])

    build = MagicMock()
    view = MagicMock()
    remove = MagicMock(return_value=True)
    monkeypatch.setattr("context_menu.build_patch", build)
    monkeypatch.setattr("context_menu.view_files_from_patch", view)
    monkeypatch.setattr("context_menu.remove_patch", remove)

    mgr._build_patch(tree)
    build.assert_called_once_with(info)
    mgr._view_patch_files(tree)
    view.assert_called_once_with(info)
    mgr._remove_patch(tree)
    remove.assert_called_once_with(info)
    assert tree.get_children() == ()


def test_modify_patch_prefix_guard(tk_root, tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    from context_menu import ContextMenuManager
    import patches_operations as po

    # Profile prefix is S; patch starts with J
    info = {"NAME": "J1.0.0001-W0", "PATCH_ID": 2, "COMMENTS": "x"}
    po.patch_info_dict["J1.0.0001-W0"] = info

    switch = MagicMock()
    mgr = ContextMenuManager()
    mgr.switch_callback = switch
    tree = _patches_tree(tk_root, ["J1.0.0001-W0"])
    tree.selection_set(tree.get_children()[0])
    mgr._modify_patch(tree)
    mock_messagebox.showerror.assert_called()
    switch.assert_not_called()


def test_prefix_combobox_helpers(tk_root):
    from context_menu import ContextMenuManager
    from tkinter import ttk

    mgr = ContextMenuManager()
    assert mgr.get_current_prefix() is None
    combo = ttk.Combobox(tk_root, values=["S", "J"])
    combo.set("J")
    mgr.set_prefix_combobox(combo)
    assert mgr.get_current_prefix() == "J"

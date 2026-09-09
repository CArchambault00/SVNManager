"""Tests for dialog helpers, username flow, and view_files_from_patch."""

from unittest.mock import MagicMock, patch

import pytest


def test_validate_current_patches_and_dsn(tmp_path):
    from dialog import validate_current_patches, validate_dsn_name

    d = tmp_path / "patches"
    d.mkdir()
    assert validate_current_patches(str(d)) is True
    assert validate_current_patches(str(tmp_path / "missing")) is False
    assert validate_dsn_name("CYFRAMEPROD") is True
    assert validate_dsn_name("") is False


def test_validate_svn_folder(monkeypatch):
    from dialog import validate_svn_folder

    monkeypatch.setattr(
        "dialog.subprocess.run",
        MagicMock(return_value=MagicMock(returncode=0)),
    )
    assert validate_svn_folder("C:/svn") is True
    monkeypatch.setattr(
        "dialog.subprocess.run",
        MagicMock(return_value=MagicMock(returncode=1)),
    )
    assert validate_svn_folder("C:/not") is False


def test_show_messagebox_routes(mock_messagebox, monkeypatch):
    import dialog as dlg

    monkeypatch.setattr(dlg, "messagebox", mock_messagebox)
    dlg.show_messagebox("info", "t", "m")
    dlg.show_messagebox("warning", "t", "m")
    dlg.show_messagebox("error", "t", "m")
    mock_messagebox.showinfo.assert_called()
    mock_messagebox.showwarning.assert_called()
    mock_messagebox.showerror.assert_called()


def test_set_username_saves(tmp_appdata, sample_profile, mock_messagebox, monkeypatch):
    import dialog as dlg
    from config import load_config, save_config
    import tkinter as tk

    save_config({"username": "", "active_profile": "dev"})

    monkeypatch.setattr(dlg, "messagebox", mock_messagebox)
    monkeypatch.setattr(dlg.simpledialog, "askstring", MagicMock(return_value="alice"))
    monkeypatch.setattr(dlg, "show_messagebox", MagicMock())

    root = tk.Tk()
    root.withdraw()
    try:
        menu_bar = tk.Menu(root)
        config_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Config ❌", menu=config_menu)
        menu_bar.add_cascade(label="Profile ❌", menu=tk.Menu(menu_bar, tearoff=0))
        config_menu.add_command(label="Username ❌")
        root.config(menu=menu_bar)

        dlg.set_username(config_menu, menu_bar)
        assert load_config()["username"] == "alice"
    finally:
        root.destroy()


def test_set_username_cancel_change(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    import dialog as dlg
    import tkinter as tk

    monkeypatch.setattr(dlg, "messagebox", mock_messagebox)
    mock_messagebox.askyesno.return_value = False
    monkeypatch.setattr(dlg, "show_messagebox", MagicMock())
    ask = MagicMock()
    monkeypatch.setattr(dlg.simpledialog, "askstring", ask)

    root = tk.Tk()
    root.withdraw()
    try:
        menu_bar = tk.Menu(root)
        config_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Config ✔️", menu=config_menu)
        config_menu.add_command(label="Username ✔️")
        dlg.set_username(config_menu, menu_bar)
        ask.assert_not_called()
    finally:
        root.destroy()


def test_display_patch_files(tk_root, monkeypatch):
    import tkinter as tk
    from dialog import display_patch_files

    monkeypatch.setattr(tk.Toplevel, "grab_set", MagicMock())
    monkeypatch.setattr(tk.Toplevel, "transient", MagicMock())

    display_patch_files(
        ["locked || VERSION: 1 || webpage/a.asp"],
        "S1.0.0001-W0",
        "desc",
        "tester",
        "2026-01-01",
    )

    found = False
    for w in list(tk._default_root.winfo_children()):
        if isinstance(w, tk.Toplevel):
            for child in w.winfo_children():
                if child.winfo_class() == "Frame":
                    for sub in child.winfo_children():
                        if sub.winfo_class() == "Text":
                            content = sub.get("1.0", "end")
                            assert "S1.0.0001-W0" in content
                            assert "webpage/a.asp" in content
                            found = True
            w.destroy()
    assert found


def test_view_files_from_patch(tmp_appdata, sample_config, mock_db, mock_messagebox, monkeypatch):
    import patches_operations as po

    patch_id = mock_db.create_patch_header("S", "1.0.0400-W0", "viewme", "tester", False, 1, 0, 400)
    mock_db.patch_files[patch_id] = [
        {
            "FILE_ID": 1,
            "PATH": "webpage/a.asp",
            "NAME": "a.asp",
            "VERSION": "7",
            "FOLDER_TYPE": "1",
            "SVN_PATH": "webpage",
            "DELETED_YN": "N",
            "PATCH_NAME": "S1.0.0400-W0",
        }
    ]
    monkeypatch.setattr(po, "get_file_info", MagicMock(return_value=(True, "tester", "7", "2026-01-01")))
    display = MagicMock()
    monkeypatch.setattr(po, "display_patch_files", display)

    po.view_files_from_patch(mock_db.patches[patch_id])
    display.assert_called_once()
    files_arg = display.call_args[0][0]
    assert any("webpage/a.asp" in f and "locked" in f for f in files_arg)


def test_handle_path_selection_success_and_cancel(monkeypatch, mock_messagebox):
    import dialog as dlg

    monkeypatch.setattr(dlg, "messagebox", mock_messagebox)
    monkeypatch.setattr(dlg, "show_messagebox", MagicMock())

    monkeypatch.setattr(dlg.filedialog, "askdirectory", MagicMock(return_value="C:/ok"))
    cb = MagicMock()
    assert dlg.handle_path_selection("t", lambda p: True, cb, "err") is True
    cb.assert_called_once_with("C:/ok")

    monkeypatch.setattr(dlg.filedialog, "askdirectory", MagicMock(return_value=""))
    assert dlg.handle_path_selection("t", lambda p: True, MagicMock(), "err") is False

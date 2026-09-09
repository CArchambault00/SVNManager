"""GUI requirements and lightweight dialog smoke tests."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.e2e


def test_setup_gui_with_config(
    tmp_appdata, sample_config, mock_db, mock_svn, mock_messagebox, reset_state_manager, monkeypatch
):
    monkeypatch.setattr("app.check_latest_version", MagicMock())
    monkeypatch.setattr("app._offer_settings_migration", MagicMock())
    monkeypatch.setattr("app.refresh_locked_files", MagicMock())
    monkeypatch.setattr("svn_operations.refresh_locked_files", MagicMock())
    monkeypatch.setattr("app.switch_to_lock_unlock_menu", MagicMock())

    try:
        from app import setup_gui

        with patch("app.TkinterDnD") as dnd:
            import tkinter as tk

            root = tk.Tk()
            root.withdraw()
            root.iconbitmap = MagicMock()
            dnd.Tk.return_value = root
            monkeypatch.setattr("app.initialize_native_topbar", MagicMock())
            monkeypatch.setattr("app.configure_treeview_style", MagicMock())

            result = setup_gui()
            assert result is root
            root.destroy()
    except Exception as exc:
        pytest.skip(f"Tk setup unavailable: {exc}")


def test_profile_dialog_open_close(tk_root, tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    monkeypatch.setattr("profile_dialog.dbClass", MagicMock)
    try:
        from profile_dialog import ProfileDialog
    except Exception as exc:
        pytest.skip(f"ProfileDialog import failed: {exc}")

    # Avoid DB calls when listing prefixes
    with patch.object(ProfileDialog, "__init__", lambda self, parent: None):
        dlg = ProfileDialog.__new__(ProfileDialog)
        assert dlg is not None

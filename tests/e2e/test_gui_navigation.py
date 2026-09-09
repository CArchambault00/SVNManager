"""GUI smoke / e2e navigation tests (mocked backends)."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture
def gui_app(tk_root, tmp_appdata, sample_config, mock_db, mock_svn, mock_messagebox, reset_state_manager, monkeypatch):
    """Prepare root window with mocked SVN refresh and no network version check."""
    monkeypatch.setattr("app.refresh_locked_files", MagicMock())
    monkeypatch.setattr("app.refresh_patches", MagicMock())
    monkeypatch.setattr("app.refresh_patch_files", MagicMock())
    monkeypatch.setattr("app.check_latest_version", MagicMock())
    monkeypatch.setattr("app._offer_settings_migration", MagicMock())
    monkeypatch.setattr("svn_operations.refresh_locked_files", MagicMock())
    monkeypatch.setattr("svn_operations.get_all_locked_files", MagicMock(return_value=[]))
    monkeypatch.setattr("buttons_function.insert_next_version", MagicMock())

    # Avoid iconbitmap failures in some environments
    monkeypatch.setattr(tk_root, "iconbitmap", MagicMock())

    yield tk_root


def test_check_requirements_ok(tmp_appdata, sample_config, mock_messagebox):
    from app import check_requirements

    assert check_requirements() is True


def test_check_requirements_missing_username(tmp_appdata, mock_messagebox):
    from app import check_requirements
    from config import save_config

    save_config({"username": "", "active_profile": None})
    assert check_requirements() is False
    mock_messagebox.showwarning.assert_called()


def test_navigate_lock_unlock(gui_app, mock_messagebox, reset_state_manager):
    from app import switch_to_lock_unlock_menu
    from state_manager import state_manager

    switch_to_lock_unlock_menu(gui_app)
    gui_app.update_idletasks()
    assert state_manager.current_menu == "lock_unlock"
    assert gui_app.winfo_children()


def test_navigate_all_main_screens(gui_app, mock_messagebox, reset_state_manager, mock_db, monkeypatch):
    from app import (
        switch_to_lock_unlock_menu,
        switch_to_modify_patch_menu,
        switch_to_patch_menu,
        switch_to_patches_menu,
    )
    from state_manager import state_manager

    monkeypatch.setattr("version_operation.next_version", MagicMock(return_value="1.0.0001-"))
    monkeypatch.setattr("buttons_function.insert_next_version", MagicMock())

    switch_to_lock_unlock_menu(gui_app)
    gui_app.update()
    assert state_manager.current_menu == "lock_unlock"

    switch_to_patch_menu(gui_app)
    gui_app.update()
    assert state_manager.current_menu == "patch"

    # Seed a patch for modify menu
    patch_id = mock_db.create_patch_header("S", "1.0.0300-W0", "e2e", "tester", False, 1, 0, 300)
    details = mock_db.patches[patch_id]

    switch_to_patches_menu(gui_app)
    gui_app.update()
    assert state_manager.current_menu == "patches"

    monkeypatch.setattr("app.refresh_patch_files", MagicMock())
    switch_to_modify_patch_menu(details, gui_app)
    gui_app.update()
    assert state_manager.current_menu == "modify_patch"


def test_reset_current_menu(gui_app, mock_messagebox, reset_state_manager, monkeypatch):
    from app import switch_to_patch_menu
    from native_topbar import reset_current_menu
    from state_manager import state_manager

    monkeypatch.setattr("version_operation.next_version", MagicMock(return_value="1.0.0001-"))
    monkeypatch.setattr("buttons_function.insert_next_version", MagicMock())

    switch_to_patch_menu(gui_app)
    gui_app.update()
    state_manager.save_state("patch", patch_version="1.0.9999-W0", patch_description="keep?")
    reset_current_menu(gui_app)
    gui_app.update()
    assert state_manager.get_state("patch")["patch_version"] == ""
    assert state_manager.current_menu == "patch"

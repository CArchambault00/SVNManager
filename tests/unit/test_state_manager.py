"""Unit tests for state_manager and create_component helpers."""

from datetime import datetime

from create_component import _column_sort_key, parse_date
from state_manager import StateManager


def test_save_and_get_state():
    sm = StateManager()
    sm.save_state("patch", patch_version="1.0.0001-W0", patch_description="hi")
    state = sm.get_state("patch")
    assert state["patch_version"] == "1.0.0001-W0"
    assert state["patch_description"] == "hi"
    assert sm.get_current_menu() == "patch"


def test_clear_state_preserves_modify_patch_details():
    sm = StateManager()
    details = {"PATCH_ID": 1, "NAME": "S1.0.0001-W0"}
    sm.save_state("modify_patch", patch_details=details, patch_version="1.0.0001-W0")
    # original_patch_details is not in initial keys — set directly
    sm.states["modify_patch"]["original_patch_details"] = details
    sm.states["modify_patch"]["patch_details"] = details

    sm.clear_state("modify_patch")
    assert sm.get_state("modify_patch")["patch_details"] == details
    assert sm.get_state("modify_patch")["patch_version"] == ""


def test_clear_all_states():
    sm = StateManager()
    sm.save_state("lock_unlock", selected_files=["a"])
    sm.clear_state()
    assert sm.get_state("lock_unlock")["selected_files"] == []
    assert sm.current_menu is None


def test_prefix_history():
    sm = StateManager()
    sm.update_prefix_selection("S")
    sm.update_prefix_selection("J")
    assert sm.get_state("patches")["selected_prefix"] == "J"
    assert sm.get_last_prefix() == "S"


def test_loading_flag():
    sm = StateManager()
    sm.set_loading(True)
    assert sm.is_menu_loading() is True
    sm.set_loading(False)
    assert sm.is_menu_loading() is False


def test_parse_date_formats():
    assert parse_date("2026-01-02 03:04:05") == datetime(2026, 1, 2, 3, 4, 5)
    assert parse_date("") == datetime.min
    assert parse_date("bogus") == datetime.min


def test_column_sort_key_version_and_size():
    assert _column_sort_key("Size", "10") < _column_sort_key("Size", "20")
    assert _column_sort_key("Patch Version", "S1.0.0002-W0") > _column_sort_key(
        "Patch Version", "S1.0.0001-W0"
    )
    assert _column_sort_key("Name", "B") > _column_sort_key("Name", "A")

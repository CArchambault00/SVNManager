"""Unit tests for profiles CRUD."""

import pytest

from config import save_config
from profiles import (
    create_profile,
    delete_profile,
    get_profile,
    list_profiles,
    load_profiles,
    update_profile,
)


def test_create_and_load_profile(tmp_appdata):
    create_profile("alpha", "C:/svn", ["A"], "C:/patches", "DSN1")
    profiles = load_profiles()
    assert "alpha" in profiles
    assert profiles["alpha"].dsn_name == "DSN1"
    assert list_profiles() == ["alpha"]
    assert get_profile("alpha").name == "alpha"


def test_duplicate_name_raises(tmp_appdata):
    create_profile("alpha", "C:/svn", ["A"], "C:/patches", "DSN1")
    with pytest.raises(ValueError, match="already exists"):
        create_profile("alpha", "C:/svn2", ["B"], "C:/patches2", "DSN2")


def test_duplicate_prefix_raises(tmp_appdata):
    create_profile("alpha", "C:/svn", ["A"], "C:/patches", "DSN1")
    with pytest.raises(ValueError, match="Patch prefix"):
        create_profile("beta", "C:/svn", ["A"], "C:/patches", "DSN1")


def test_update_profile(tmp_appdata):
    create_profile("alpha", "C:/svn", ["A"], "C:/patches", "DSN1")
    updated = update_profile("alpha", svn_path="D:/svn", dsn_name="DSN2")
    assert updated.svn_path == "D:/svn"
    assert updated.dsn_name == "DSN2"
    assert get_profile("alpha").patch_prefix == ["A"]


def test_cannot_delete_active_profile(tmp_appdata, sample_config):
    create_profile("other", "C:/svn2", ["B"], "C:/patches2", "DSN2")
    with pytest.raises(ValueError, match="active profile"):
        delete_profile("dev")


def test_cannot_delete_last_profile(tmp_appdata):
    create_profile("only", "C:/svn", ["A"], "C:/patches", "DSN1")
    save_config({"username": "u", "active_profile": None})
    with pytest.raises(ValueError, match="last profile"):
        delete_profile("only")


def test_delete_non_active_profile(tmp_appdata, sample_config):
    create_profile("other", "C:/svn2", ["B"], "C:/patches2", "DSN2")
    delete_profile("other")
    assert "other" not in load_profiles()
    assert "dev" in load_profiles()

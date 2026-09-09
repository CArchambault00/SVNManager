"""Unit tests for config load/save/merge."""

import json

import pytest

from config import get_unset_var, load_config, log_error, log_success, save_config, verify_config


def test_load_config_empty(tmp_appdata):
    cfg = load_config()
    assert cfg.get("username") == ""
    assert cfg.get("active_profile") is None


def test_load_config_merges_profile(tmp_appdata, sample_config):
    cfg = load_config()
    assert cfg["username"] == "tester"
    assert cfg["active_profile"] == "dev"
    assert cfg["dsn_name"] == "TESTDSN"
    assert cfg["svn_path"]
    assert cfg["patch_prefix"] == ["S"]


def test_save_config_only_username_and_profile(tmp_appdata, sample_profile):
    save_config(
        {
            "username": "alice",
            "active_profile": "dev",
            "svn_path": "should-not-persist",
        }
    )
    raw = json.loads((tmp_appdata / "svn_config.json").read_text(encoding="utf-8"))
    assert raw == {"username": "alice", "active_profile": "dev"}
    assert "svn_path" not in raw


def test_get_unset_var(tmp_appdata):
    assert "username" in get_unset_var()
    save_config({"username": "bob", "active_profile": None})
    unset = get_unset_var()
    assert "username" not in unset
    assert "active_profile" in unset


def test_verify_config_raises(tmp_appdata):
    with pytest.raises(ValueError, match="not set"):
        verify_config()


def test_verify_config_ok(tmp_appdata, sample_config):
    verify_config()


def test_log_error_and_success(tmp_appdata, sample_config):
    log_error("boom")
    log_success("Test Action", "details")
    err = (tmp_appdata / "SVNManager_error.log").read_text(encoding="utf-8")
    ok = (tmp_appdata / "SVNManager_success.log").read_text(encoding="utf-8")
    assert "boom" in err
    assert "Test Action" in ok

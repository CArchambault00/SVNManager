"""Unit tests for user_data migration helpers."""

import json
import os
from pathlib import Path

import user_data


def test_has_user_settings_false_when_empty(tmp_appdata, monkeypatch):
    monkeypatch.setattr(user_data, "get_user_data_dir", lambda: str(tmp_appdata))
    assert user_data.has_user_settings() is False


def test_has_user_settings_true_with_config(tmp_appdata, monkeypatch):
    monkeypatch.setattr(user_data, "get_user_data_dir", lambda: str(tmp_appdata))
    (tmp_appdata / "svn_config.json").write_text('{"username":"u"}', encoding="utf-8")
    assert user_data.has_user_settings() is True


def test_mark_settings_ready(tmp_appdata, monkeypatch):
    monkeypatch.setattr(user_data, "get_user_data_dir", lambda: str(tmp_appdata))
    user_data.mark_settings_ready()
    assert (tmp_appdata / user_data.MARKER_FILENAME).is_file()


def test_import_from_folder(tmp_appdata, tmp_path, monkeypatch):
    monkeypatch.setattr(user_data, "get_user_data_dir", lambda: str(tmp_appdata))
    monkeypatch.setattr(user_data, "_migrated_sources", [])

    legacy = tmp_path / "old_install"
    legacy.mkdir()
    (legacy / "svn_config.json").write_text('{"username":"legacy"}', encoding="utf-8")
    (legacy / "svn_profiles.json").write_text("{}", encoding="utf-8")

    imported = user_data.import_from_folder(str(legacy))
    assert len(imported) == 2
    assert json.loads((tmp_appdata / "svn_config.json").read_text(encoding="utf-8"))[
        "username"
    ] == "legacy"


def test_should_prompt_false_when_not_frozen(tmp_appdata, monkeypatch):
    monkeypatch.setattr(user_data, "get_user_data_dir", lambda: str(tmp_appdata))
    monkeypatch.setattr(user_data.sys, "frozen", False, raising=False)
    assert user_data.should_prompt_for_legacy_settings() is False


def test_migrate_file_from_legacy_dir(tmp_appdata, tmp_path, monkeypatch):
    monkeypatch.setattr(user_data, "get_user_data_dir", lambda: str(tmp_appdata))
    monkeypatch.setattr(user_data, "_migrated_sources", [])
    monkeypatch.setattr(user_data, "get_install_dir", lambda: str(tmp_path / "install"))
    install = tmp_path / "install"
    install.mkdir()
    (install / "svn_config.json").write_text('{"username":"from-install"}', encoding="utf-8")

    dest = user_data._migrate_file("svn_config.json", str(tmp_appdata), track=True)
    assert Path(dest).is_file()
    assert "from-install" in Path(dest).read_text(encoding="utf-8")
    assert user_data._migrated_sources

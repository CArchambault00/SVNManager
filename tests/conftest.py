"""Shared fixtures for SVN Manager tests. External Oracle/SVN are always mocked."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def tmp_appdata(tmp_path, monkeypatch):
    """Isolate AppData config/profiles under a temporary directory."""
    appdata = tmp_path / "AppData"
    data_dir = appdata / "SVNManager"
    data_dir.mkdir(parents=True)

    monkeypatch.setenv("APPDATA", str(appdata))

    config_file = str(data_dir / "svn_config.json")
    profiles_file = str(data_dir / "svn_profiles.json")
    error_log = str(data_dir / "SVNManager_error.log")
    success_log = str(data_dir / "SVNManager_success.log")

    monkeypatch.setattr("user_data.USER_DATA_DIR", str(data_dir))
    monkeypatch.setattr("user_data.CONFIG_FILE", config_file)
    monkeypatch.setattr("user_data.PROFILES_FILE", profiles_file)
    monkeypatch.setattr("user_data.ERROR_LOG_FILE", error_log)
    monkeypatch.setattr("user_data.SUCCESS_LOG_FILE", success_log)
    monkeypatch.setattr("user_data._initialized", True)
    monkeypatch.setattr("user_data._migrated_sources", [])

    monkeypatch.setattr("config.CONFIG_FILE", config_file)
    monkeypatch.setattr("config.ERROR_LOG_FILE", error_log)
    monkeypatch.setattr("config.SUCCESS_LOG_FILE", success_log)
    monkeypatch.setattr("profiles.PROFILES_FILE", profiles_file)

    return data_dir


@pytest.fixture
def sample_profile(tmp_appdata, tmp_path):
    """Write a default profile and return its fields."""
    svn_path = str(tmp_path / "svn_wc")
    patches_path = str(tmp_path / "patches" / "Current")
    Path(svn_path).mkdir(parents=True, exist_ok=True)
    Path(patches_path).mkdir(parents=True, exist_ok=True)

    profiles = {
        "dev": {
            "name": "dev",
            "svn_path": svn_path,
            "patch_prefix": ["S"],
            "current_patches": patches_path,
            "dsn_name": "TESTDSN",
        }
    }
    with open(tmp_appdata / "svn_profiles.json", "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)

    return profiles["dev"]


@pytest.fixture
def sample_config(tmp_appdata, sample_profile):
    """Write username + active profile config."""
    config = {"username": "tester", "active_profile": "dev"}
    with open(tmp_appdata / "svn_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f)
    return {**config, **sample_profile, "patch_prefix": sample_profile["patch_prefix"]}


@pytest.fixture
def mock_messagebox(monkeypatch):
    """Prevent blocking Tk dialogs."""
    stubs = SimpleNamespace(
        showerror=MagicMock(),
        showinfo=MagicMock(),
        showwarning=MagicMock(),
        askyesno=MagicMock(return_value=True),
        askokcancel=MagicMock(return_value=True),
    )
    for mod in (
        "tkinter.messagebox",
        "config.messagebox",
        "dialog.messagebox",
        "version_operation.messagebox",
        "patch_generation.messagebox",
        "patches_operations.messagebox",
        "svn_operations.messagebox",
        "app.messagebox",
        "native_topbar.messagebox",
        "buttons_function.messagebox",
    ):
        try:
            monkeypatch.setattr(f"{mod}.showerror", stubs.showerror, raising=False)
            monkeypatch.setattr(f"{mod}.showinfo", stubs.showinfo, raising=False)
            monkeypatch.setattr(f"{mod}.showwarning", stubs.showwarning, raising=False)
            monkeypatch.setattr(f"{mod}.askyesno", stubs.askyesno, raising=False)
            monkeypatch.setattr(f"{mod}.askokcancel", stubs.askokcancel, raising=False)
        except Exception:
            pass

    # Also patch modules that use `from tkinter import messagebox`
    for mod_name in (
        "version_operation",
        "patch_generation",
        "patches_operations",
        "svn_operations",
        "app",
        "config",
        "native_topbar",
    ):
        try:
            import importlib

            mod = importlib.import_module(mod_name)
            if hasattr(mod, "messagebox"):
                monkeypatch.setattr(mod, "messagebox", stubs)
        except Exception:
            pass

    return stubs


class FakeDB:
    """In-memory stand-in for dbClass used by integration tests."""

    def __init__(self):
        self.conn = MagicMock()
        self.patches: Dict[str, Any] = {}
        self.patch_files: Dict[Any, List[Dict]] = {}
        self.next_patch_id = 1
        self.applications = {"S": "CORE", "J": "JTIME"}
        self.folders = {"webpage": 1, "Database": 2, "Projects/SVN/webpage": 1}

    def close(self):
        pass

    def get_max_version(self, application_id: str) -> List[Dict]:
        return [{"MAJOR": 1, "MINOR": 0, "REVISION": 100}]

    def get_application_id(self, prefix: str) -> str:
        return self.applications.get(prefix.upper() if prefix else "", "CORE")

    def check_patch_exists(self, prefix: str, version: str) -> bool:
        name = f"{prefix}{version}"
        return any(p.get("NAME", "").startswith(f"{prefix}{version}") for p in self.patches.values())

    def create_patch_header(
        self, prefix, version, description, username, flag, major, minor, revision
    ):
        patch_id = self.next_patch_id
        self.next_patch_id += 1
        name = f"{prefix}{version}"
        self.patches[patch_id] = {
            "PATCH_ID": patch_id,
            "NAME": name,
            "COMMENTS": description,
            "USER_ID": username,
            "CREATION_DATE": "2026-01-01 12:00:00",
            "PATCH_SIZE": 0,
            "CHECK_LIST_COUNT": 0,
            "MAJOR": major,
            "MINOR": minor,
            "REVISION": revision,
        }
        self.patch_files[patch_id] = []
        return patch_id

    def get_folder_id(self, soft_path: str) -> int:
        return self.folders.get(soft_path, 1)

    def create_patch_detail(self, patch_id, fake_path, clean_path, filename, revision, folder_id):
        file_id = len(self.patch_files.get(patch_id, [])) + 1
        entry = {
            "FILE_ID": file_id,
            "PATH": clean_path + filename if clean_path else filename,
            "NAME": filename,
            "VERSION": revision or "1",
            "FOLDER_TYPE": "1" if "webpage" in (clean_path or "") else "2",
            "SVN_PATH": "webpage" if "webpage" in (clean_path or "") else "Database",
            "DELETED_YN": "N",
            "PATCH_NAME": self.patches[patch_id]["NAME"],
        }
        self.patch_files.setdefault(patch_id, []).append(entry)
        return file_id

    def set_md5(self, patch_id, file_id, md5checksum):
        pass

    def get_patch_list(self, temp, application_id) -> List[Dict]:
        return list(self.patches.values())

    def get_patch_file_list_new(self, patch_id) -> List[Dict]:
        return list(self.patch_files.get(patch_id, []))

    def get_folder_patch_list_new(self, folder_path) -> List[Dict]:
        return []

    def get_prefix_list(self) -> List[str]:
        return ["S", "J"]

    def remove_patch(self, patch_id):
        self.patches.pop(patch_id, None)
        self.patch_files.pop(patch_id, None)

    def delete_patch_details(self, patch_id):
        self.patch_files[patch_id] = []

    def delete_patch_detail(self, patch_id):
        self.patch_files[patch_id] = []

    def update_patch_header(self, *args, **kwargs):
        if args:
            patch_id = args[0]
            if patch_id in self.patches and len(args) >= 4:
                self.patches[patch_id]["COMMENTS"] = args[3]
                self.patches[patch_id]["NAME"] = f"{args[1]}{args[2]}"

    def update_comment(self, patch_id, comment):
        if patch_id in self.patches:
            self.patches[patch_id]["COMMENTS"] = comment


@pytest.fixture
def fake_db():
    return FakeDB()


@pytest.fixture
def mock_db(fake_db, monkeypatch):
    """Patch dbClass constructors to return the shared FakeDB."""

    def _factory(*args, **kwargs):
        return fake_db

    for target in (
        "db_handler.dbClass",
        "version_operation.dbClass",
        "patch_generation.dbClass",
        "patches_operations.dbClass",
        "patch_utils.dbClass",
        "create_buttons.dbClass",
        "buttons_function.dbClass",
        "profile_dialog.dbClass",
        "dialog.dbClass",
    ):
        monkeypatch.setattr(target, _factory, raising=False)
    return fake_db


@pytest.fixture
def mock_svn(monkeypatch):
    """Mock subprocess.run for SVN CLI calls."""
    wc_root = "C:/svn/wc"

    def _run(args, *a, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = ""
        cmd = args[0] if args else ""
        if cmd == "svn":
            sub = args[1] if len(args) > 1 else ""
            if sub == "info":
                if "--show-item" in args and "wc-root" in args:
                    result.stdout = wc_root + "\n"
                else:
                    result.stdout = "Relative URL: ^/\nURL: svn://example/trunk\n"
            elif sub in ("lock", "unlock", "commit", "revert"):
                result.stdout = "OK\n"
            elif sub == "status":
                result.stdout = '<?xml version="1.0"?><status></status>\n'
            elif sub == "cat":
                result.stdout = "file content"
        return result

    monkeypatch.setattr("subprocess.run", _run)
    for mod in ("svn_operations", "patch_generation", "patches_operations"):
        try:
            monkeypatch.setattr(f"{mod}.subprocess.run", _run, raising=False)
        except Exception:
            pass
    return SimpleNamespace(wc_root=wc_root, run=_run)


@pytest.fixture
def reset_state_manager():
    """Reset the global StateManager between tests."""
    from state_manager import state_manager

    state_manager.clear_state()
    state_manager.current_menu = None
    state_manager.is_loading = False
    state_manager.refresh_timer = None
    yield state_manager
    state_manager.clear_state()
    state_manager.current_menu = None
    state_manager.is_loading = False


@pytest.fixture
def tk_root():
    """Create a Tk root for GUI tests; skip if display is unavailable."""
    try:
        try:
            from tkinterdnd2 import TkinterDnD

            root = TkinterDnD.Tk()
        except Exception:
            import tkinter as tk

            root = tk.Tk()
        root.withdraw()
        yield root
        try:
            root.destroy()
        except Exception:
            pass
    except Exception as exc:
        pytest.skip(f"Tk display unavailable: {exc}")

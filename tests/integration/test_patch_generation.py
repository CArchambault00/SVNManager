"""Integration tests for patch_generation with mocked DB/SVN."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from patch_generation import generate_patch


@pytest.fixture
def patch_env(tmp_appdata, sample_config, mock_db, mock_svn, mock_messagebox, monkeypatch):
    """Common stubs around generate_patch side effects."""
    monkeypatch.setattr("patch_generation.commit_files", MagicMock())
    monkeypatch.setattr(
        "patch_generation.get_file_head_revision_batch",
        MagicMock(return_value={"webpage/a.asp": "42"}),
    )
    monkeypatch.setattr(
        "patch_generation.get_md5_checksum_batch",
        MagicMock(return_value={"C:/svn/wc/webpage/a.asp": "abc123"}),
    )
    monkeypatch.setattr("patch_generation.create_patch_files_batch", MagicMock())
    monkeypatch.setattr("patch_generation.setup_patch_folder", MagicMock())
    monkeypatch.setattr("patch_generation.create_depend_txt", MagicMock())

    def _write_readme(folder, *args, **kwargs):
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / "ReadMe.txt").write_text("readme", encoding="utf-8")

    def _write_main_sql(folder, *args, **kwargs):
        Path(folder).mkdir(parents=True, exist_ok=True)
        (Path(folder) / "MainSQL.sql").write_text("sql", encoding="utf-8")

    monkeypatch.setattr("patch_generation.create_readme_file", _write_readme)
    monkeypatch.setattr("patch_generation.create_main_sql_file", _write_main_sql)
    return sample_config


def test_generate_patch_success(patch_env, mock_db, mock_messagebox):
    generate_patch(
        selected_files=["webpage/a.asp"],
        patch_prefixe="S",
        patch_version="1.0.0101-W0",
        patch_description="Test patch",
        unlock_files=False,
    )

    assert any(p["NAME"].startswith("S1.0.0101") for p in mock_db.patches.values())
    patch_folder = Path(patch_env["current_patches"]) / "S1.0.0101-W0"
    assert patch_folder.is_dir()
    assert (patch_folder / "ReadMe.txt").is_file()
    assert (patch_folder / "MainSQL.sql").is_file()
    mock_messagebox.showinfo.assert_called()
    mock_db.conn.commit.assert_called()


def test_generate_patch_invalid_version(patch_env, mock_db, mock_messagebox):
    generate_patch(
        selected_files=["webpage/a.asp"],
        patch_prefixe="S",
        patch_version="1.0.0101",  # missing -suffix
        patch_description="Test",
        unlock_files=False,
    )
    mock_messagebox.showerror.assert_called()
    assert len(mock_db.patches) == 0


def test_generate_patch_duplicate(patch_env, mock_db, mock_messagebox):
    mock_db.create_patch_header("S", "1.0.0101-W0", "first", "tester", False, 1, 0, 101)
    # check_patch_exists should see existing
    generate_patch(
        selected_files=["webpage/a.asp"],
        patch_prefixe="S",
        patch_version="1.0.0101-W0",
        patch_description="dup",
        unlock_files=False,
    )
    mock_messagebox.showerror.assert_called()
    mock_db.conn.rollback.assert_called()


def test_generate_patch_empty_files_cancelled(patch_env, mock_db, mock_messagebox):
    mock_messagebox.askyesno.return_value = False
    generate_patch(
        selected_files=[],
        patch_prefixe="S",
        patch_version="1.0.0102-W0",
        patch_description="empty",
        unlock_files=False,
    )
    assert len(mock_db.patches) == 0

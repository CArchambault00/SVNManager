"""Integration tests for patches_operations with mocked DB/SVN."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import patches_operations as po


@pytest.fixture
def seeded_patch(tmp_appdata, sample_config, mock_db, mock_svn, mock_messagebox):
    patch_id = mock_db.create_patch_header(
        "S", "1.0.0200-W0", "seed", "tester", False, 1, 0, 200
    )
    mock_db.patch_files[patch_id] = [
        {
            "FILE_ID": 1,
            "PATH": "webpage/pages/a.asp",
            "NAME": "a.asp",
            "VERSION": "10",
            "FOLDER_TYPE": "1",
            "SVN_PATH": "webpage",
            "DELETED_YN": "N",
            "PATCH_NAME": "S1.0.0200-W0",
        }
    ]
    po.patch_info_dict.clear()
    po.patch_info_dict["S1.0.0200-W0"] = mock_db.patches[patch_id]
    return mock_db.patches[patch_id]


def test_refresh_patches_dict(seeded_patch, mock_db):
    po.patch_info_dict.clear()
    po.refresh_patches_dict(False, "S")
    assert "S1.0.0200-W0" in po.patch_info_dict


def test_refresh_patches_treeview(seeded_patch, mock_db):
    tree = MagicMock()
    tree.get_children.return_value = []
    po.refresh_patches(tree, False, "S", "tester")
    assert tree.insert.called
    assert "S1.0.0200-W0" in po.patch_info_dict


def test_selected_patch_roundtrip(seeded_patch):
    po.set_selected_patch(seeded_patch)
    assert po.get_selected_patch() == seeded_patch
    assert po.get_full_patch_info("S1.0.0200-W0") == seeded_patch


def test_remove_patch_confirmed(seeded_patch, mock_db, mock_messagebox):
    mock_messagebox.askyesno.return_value = True
    result = po.remove_patch(seeded_patch)
    assert result is True
    assert seeded_patch["PATCH_ID"] not in mock_db.patches
    mock_db.conn.commit.assert_called()


def test_remove_patch_cancelled(seeded_patch, mock_db, mock_messagebox):
    mock_messagebox.askyesno.return_value = False
    result = po.remove_patch(seeded_patch)
    assert result is None
    assert seeded_patch["PATCH_ID"] in mock_db.patches


def test_build_patch(seeded_patch, sample_config, mock_db, mock_messagebox, monkeypatch):
    monkeypatch.setattr(po, "get_file_specific_version", MagicMock())
    monkeypatch.setattr(po, "setup_patch_folder", MagicMock())
    monkeypatch.setattr(po, "create_depend_txt", MagicMock())

    po.build_patch(seeded_patch)

    folder = Path(sample_config["current_patches"]) / "S1.0.0200-W0"
    assert folder.is_dir()
    assert (folder / "ReadMe.txt").is_file()
    mock_messagebox.showinfo.assert_called()


def test_update_patch(seeded_patch, sample_config, mock_db, mock_messagebox, monkeypatch, tmp_path):
    # FakeDB needs delete_patch_detail
    mock_db.delete_patch_detail = MagicMock(side_effect=lambda pid: mock_db.patch_files.__setitem__(pid, []))
    mock_db.update_patch_header = MagicMock()

    monkeypatch.setattr(po, "commit_files", MagicMock())
    monkeypatch.setattr(po, "get_file_head_revision", MagicMock(return_value="99"))
    monkeypatch.setattr(po, "get_md5_checksum", MagicMock(return_value="deadbeef"))
    monkeypatch.setattr(po, "create_patch_files_batch", MagicMock())
    monkeypatch.setattr(po, "setup_patch_folder", MagicMock())
    monkeypatch.setattr(po, "create_depend_txt", MagicMock())
    monkeypatch.setattr(po, "create_readme_file", MagicMock())
    monkeypatch.setattr(po, "create_main_sql_file", MagicMock())
    switch = MagicMock()

    # Create real file for get_md5 if still called with path — already mocked
    po.update_patch(
        selected_files=["webpage/pages/a.asp"],
        patch_id=seeded_patch["PATCH_ID"],
        patch_version_prefixe="S",
        patch_version_entry="1.0.0200-W0",
        patch_description="updated",
        switch_to_modify_patch_menu=switch,
        unlock_files=False,
    )

    mock_db.conn.commit.assert_called()
    mock_db.delete_patch_detail.assert_called()

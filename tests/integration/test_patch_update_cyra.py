"""Integration tests: update_patch (patch modification) Cyra automation."""

from unittest.mock import MagicMock

import pytest

import cyra_release
import patches_operations as po


class _LinksDB:
    def __init__(self, links):
        self._links = links

    def get_cyra_release_links(self):
        return self._links


def test_update_plan_rebuilds_linked_release():
    db = _LinksDB([{"VERSION": "1.1.0", "REQUIRES_PATCH": 101085,
                    "REQUIRES_PATCH_NAME": "S1.0.1085-W1S1"}])
    plan = cyra_release.build_update_plan(db, "C:/wc", "S1.0.1085-W1S1")
    assert plan["rebuild"] is True
    assert plan["release_version"] == "1.1.0"          # same version, no bump
    assert plan["link_patch"] == 101085


def test_update_plan_creates_release_when_not_linked(monkeypatch):
    db = _LinksDB([])
    monkeypatch.setattr(cyra_release, "build_cyra_plan",
                        lambda db_, wc, patch_name=None: {
                            "release_version": "1.2.0", "link_patch": 101085,
                            "link_patch_name": patch_name, "link_source": "new patch"})
    plan = cyra_release.build_update_plan(db, "C:/wc", "S1.0.1085-W1S1")
    assert plan["rebuild"] is False
    assert plan["release_version"] == "1.2.0"


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


@pytest.fixture
def update_env(seeded_patch, sample_config, mock_db, mock_messagebox, monkeypatch):
    mock_db.delete_patch_detail = MagicMock(
        side_effect=lambda pid: mock_db.patch_files.__setitem__(pid, []))
    mock_db.update_patch_header = MagicMock()
    calls = {}
    monkeypatch.setattr(po, "commit_files", MagicMock())
    monkeypatch.setattr(po, "get_file_head_revision_batch",
                        MagicMock(return_value={"cyra/core/a.py": "99"}))
    monkeypatch.setattr(po, "get_md5_checksum_batch", MagicMock(return_value={}))
    monkeypatch.setattr(po, "get_wc_root", MagicMock(return_value="C:/wc"))
    monkeypatch.setattr(po, "create_patch_files_batch", MagicMock())
    monkeypatch.setattr(po, "setup_patch_folder", MagicMock())
    monkeypatch.setattr(po, "create_depend_txt", MagicMock())
    monkeypatch.setattr(po, "create_readme_file", MagicMock())
    monkeypatch.setattr(po, "create_main_sql_file", MagicMock())
    monkeypatch.setattr(po, "build_cyra_update_plan", MagicMock(return_value={
        "release_version": "1.1.0", "link_patch": 101085,
        "link_patch_name": "S1.0.0200-W0",
        "link_source": "rebuild of Cyra 1.1.0 already linked to S1.0.0200-W0",
        "rebuild": True,
    }))

    def _build(wc_root, plan, username, description, status_callback=None):
        calls["build"] = plan["release_version"]
        return {"version": plan["release_version"], "revision": "777"}

    monkeypatch.setattr(po, "build_and_commit_cyra_release", _build)
    monkeypatch.setattr(po, "record_cyra_link", lambda db, plan: calls.__setitem__("link", plan["release_version"]))
    return calls


def test_update_patch_with_cyra_files_rebuilds_release(update_env, seeded_patch):
    po.update_patch(
        selected_files=["cyra/core/a.py"],
        patch_id=seeded_patch["PATCH_ID"],
        patch_version_prefixe="S",
        patch_version_entry="1.0.0200-W0",
        patch_description="updated",
        switch_to_modify_patch_menu=MagicMock(),
        unlock_files=False,
    )
    assert update_env["build"] == "1.1.0"
    assert update_env["link"] == "1.1.0"

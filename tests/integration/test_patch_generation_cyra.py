"""Integration tests: generate_patch Cyra-release automation branches."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

import patch_generation
from patch_generation import generate_patch

PLAN = {
    "release_version": "1.2.0",
    "link_patch": 1085,
    "link_patch_name": "S1.0.1085-W1S1",
    "link_source": "same patch as Cyra 1.1.0 (no web/db change)",
}


@pytest.fixture
def patch_env(tmp_appdata, sample_config, mock_db, mock_svn, mock_messagebox, monkeypatch):
    """Common stubs around generate_patch side effects (as in test_patch_generation)."""
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


@pytest.fixture
def cyra_env(patch_env, monkeypatch):
    """Stub every Cyra side effect of generate_patch."""
    calls = {}
    monkeypatch.setattr(patch_generation, "get_wc_root", MagicMock(return_value="C:/wc"))
    monkeypatch.setattr(patch_generation, "build_cyra_plan", MagicMock(return_value=dict(PLAN)))

    def _bump(wc_root, version, username):
        calls["bump"] = version
        return ["cyra/VERSION", "cyra/core/__init__.py"]

    def _build(wc_root, plan, username, description, status_callback=None):
        calls["build"] = plan["release_version"]
        return {"version": plan["release_version"], "revision": "4242"}

    def _record(db, plan):
        calls["link"] = plan["link_patch_name"]

    monkeypatch.setattr(patch_generation, "apply_cyra_version_bump", _bump)
    monkeypatch.setattr(patch_generation, "build_and_commit_cyra_release", _build)
    monkeypatch.setattr(patch_generation, "record_cyra_link", _record)
    return calls


def test_cyra_only_creates_release_without_patch(cyra_env, patch_env, mock_db, mock_messagebox):
    generate_patch(
        selected_files=["cyra/core/a.py"],
        patch_prefixe="S",
        patch_version="",
        patch_description="",
        unlock_files=False,
    )
    assert len(mock_db.patches) == 0                      # no patch created
    assert cyra_env["bump"] == "1.2.0"                   # version files bumped
    assert cyra_env["build"] == "1.2.0"                  # release built/committed
    assert cyra_env["link"] == "S1.0.1085-W1S1"          # inherited previous link
    committed = patch_generation.commit_files.call_args[0][0]
    assert "cyra/VERSION" in committed and "cyra/core/__init__.py" in committed
    mock_messagebox.showinfo.assert_called()


def test_cyra_and_web_creates_patch_and_release(cyra_env, patch_env, mock_db, mock_messagebox):
    generate_patch(
        selected_files=[
            "cyra/core/a.py",
            # nested marker must stay Cyra (regression: was misclassified as webpage)
            "cyra/webpage/CMACentral/CustomerAI/ai-assistant.js",
            "webpage/a.asp",
            "Database/CF_AI/Scripts/seed.sql",
        ],
        patch_prefixe="S",
        patch_version="1.0.0101-W0",
        patch_description="Test patch",
        unlock_files=False,
    )
    assert any(p["NAME"].startswith("S1.0.0101") for p in mock_db.patches.values())
    assert cyra_env["build"] == "1.2.0"
    assert cyra_env["link"] == "S1.0.1085-W1S1"
    # cyra/ is committed + released, but never recorded in the Web/DB patch
    patch_id = next(pid for pid, p in mock_db.patches.items() if p["NAME"].startswith("S1.0.0101"))
    detail_names = [f["NAME"] for f in mock_db.patch_files[patch_id]]
    assert detail_names == ["a.asp", "seed.sql"]
    committed = patch_generation.commit_files.call_args[0][0]
    assert "cyra/core/a.py" in committed
    assert "cyra/webpage/CMACentral/CustomerAI/ai-assistant.js" in committed
    assert "webpage/a.asp" in committed
    copied = patch_generation.create_patch_files_batch.call_args[0][0]
    assert copied == ["webpage/a.asp", "Database/CF_AI/Scripts/seed.sql"]
    info_text = str(mock_messagebox.showinfo.call_args)
    assert "Cyra 1.2.0" in info_text


def test_cyra_confirm_cancel_does_nothing(cyra_env, patch_env, mock_db, mock_messagebox):
    mock_messagebox.askyesno.return_value = False
    generate_patch(
        selected_files=["cyra/core/a.py", "webpage/a.asp"],
        patch_prefixe="S",
        patch_version="1.0.0101-W0",
        patch_description="Test patch",
        unlock_files=False,
    )
    assert len(mock_db.patches) == 0
    assert "build" not in cyra_env
    patch_generation.commit_files.assert_not_called()
    assert Path(patch_env["current_patches"]).exists()

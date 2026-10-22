"""Unit tests for cyra_release classification / version / link rules."""

import json
import zipfile

import pytest

from cyra_release import (
    classify_files,
    gate_file_json,
    missing_release_files,
    normalize_rel,
    pick_previous_link,
    pick_release_version,
    required_release_paths,
    verify_release_tree,
)

SILENT_CMD = (
    "@echo off\n"
    'start "" powershell.exe -NoProfile -ExecutionPolicy Bypass '
    '-WindowStyle Hidden -File "%~dp0scripts\\install_cyra_gui.ps1" '
    '-ReleaseFolder "%~dp0."\n'
    "exit /b 0\n"
)


def _make_complete_release(root):
    for rel in required_release_paths():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SILENT_CMD if rel.endswith("InstallCyra.cmd") else "x",
                        encoding="utf-8")
    return root


def test_complete_release_tree_passes(tmp_path):
    _make_complete_release(tmp_path)
    assert missing_release_files(str(tmp_path)) == []
    assert verify_release_tree(str(tmp_path)) is True


def test_missing_top_install_cyra_is_reported(tmp_path):
    _make_complete_release(tmp_path)
    (tmp_path / "InstallCyra.cmd").unlink()
    missing = missing_release_files(str(tmp_path))
    assert "InstallCyra.cmd" in missing
    with pytest.raises(RuntimeError, match="InstallCyra"):
        verify_release_tree(str(tmp_path))


def test_missing_side_installer_script_is_reported(tmp_path):
    _make_complete_release(tmp_path)
    (tmp_path / "CyraProd" / "scripts" / "install_cyra_gui.ps1").unlink()
    assert "CyraProd/scripts/install_cyra_gui.ps1" in missing_release_files(str(tmp_path))


def test_visible_powershell_launcher_is_rejected(tmp_path):
    _make_complete_release(tmp_path)
    (tmp_path / "InstallCyra.cmd").write_text(
        'powershell -File "%~dp0CyraTest\\scripts\\install_cyra_gui.ps1"\n',
        encoding="utf-8")
    assert any("InstallCyra.cmd" in m for m in missing_release_files(str(tmp_path)))


def test_zip_must_contain_install_cyra_too(tmp_path):
    _make_complete_release(tmp_path)
    zip_path = tmp_path / "release.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for rel in required_release_paths():
            if rel != "InstallCyra.cmd":
                zf.write(tmp_path / rel, rel)
    with pytest.raises(RuntimeError, match="in zip: InstallCyra.cmd"):
        verify_release_tree(str(tmp_path), str(zip_path))
    with zipfile.ZipFile(zip_path, "a") as zf:
        zf.write(tmp_path / "InstallCyra.cmd", "InstallCyra.cmd")
    assert verify_release_tree(str(tmp_path), str(zip_path)) is True


def test_normalize_strips_scope_prefix():
    assert normalize_rel("jtdev/cyra/core/a.py") == "cyra/core/a.py"
    assert normalize_rel("cyra\\core\\a.py") == "cyra/core/a.py"
    assert normalize_rel("webpage/a.asp") == "webpage/a.asp"


def test_classify_files():
    groups = classify_files([
        "cyra/core/a.py",
        "jtdev/cyra/scripts/b.ps1",
        "webpage/x.asp",
        "Database/CMATC/SP/P.PKB",
        "Tools/other.txt",
    ])
    assert len(groups["cyra"]) == 2
    assert len(groups["web"]) == 1
    assert len(groups["db"]) == 1
    assert len(groups["other"]) == 1


def test_pick_release_version_bumps_minor():
    assert pick_release_version(["1.0.0", "1.1.0"], "1.1.0") == "1.2.0"


def test_pick_release_version_source_ahead_wins():
    assert pick_release_version(["1.0.0", "1.1.0"], "2.0.0") == "2.0.0"


def test_pick_release_version_first_release():
    assert pick_release_version([], "1.1.0") == "1.1.0"
    assert pick_release_version([], "") == "1.0.0"


def test_pick_previous_link_highest_below():
    links = [
        {"VERSION": "1.0.0", "REQUIRES_PATCH": 900, "REQUIRES_PATCH_NAME": "S1.0.0900"},
        {"VERSION": "1.1.0", "REQUIRES_PATCH": 1085, "REQUIRES_PATCH_NAME": "S1.0.1085-W1S1"},
        {"VERSION": "1.2.0", "REQUIRES_PATCH": None, "REQUIRES_PATCH_NAME": None},
    ]
    prev = pick_previous_link(links, "1.3.0")
    assert prev["VERSION"] == "1.1.0"
    # Nothing below the first linked release.
    assert pick_previous_link(links, "1.0.0") is None


def test_gate_file_json_is_stable():
    data = json.loads(gate_file_json("1.2.0", 1085, "S1.0.1085-W1S1"))
    assert data["version"] == "1.2.0"
    # Composite key (major*100000 + minor*10000 + revision), not the bare revision.
    assert data["requiresPatch"] == 101085
    assert data["requiresPatchVersion"] == "1.0.1085"
    assert data["requiresPatchName"] == "S1.0.1085-W1S1"
    assert gate_file_json("1.2.0", 1085, "S1.0.1085-W1S1") == gate_file_json("1.2.0", 1085, "S1.0.1085-W1S1")


def test_patch_key_s_major_rollover():
    from cyra_release import parse_patch_name, patch_key, resolve_patch_key
    assert parse_patch_name("S2.0.0001-W0") == (2, 0, 1)
    assert patch_key((2, 0, 1)) == 200001
    assert patch_key((2, 0, 1)) > patch_key((1, 0, 9999))
    # Legacy revision-only stored numbers are upgraded via the patch name.
    assert resolve_patch_key(1085, "S1.0.1085-W1S1") == 101085
    assert resolve_patch_key(101085, "S1.0.1085-W1S1") == 101085
    assert resolve_patch_key(1085, "") == 1085

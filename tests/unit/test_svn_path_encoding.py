"""Tests for SVN path UTF-8 / mojibake repair."""

import os
from unittest.mock import MagicMock

import svn_operations as svn


def test_repair_mojibake_path_recovers_a_grave():
    good = "Liste_des_rapports_de_mise_à_jour_de_GL"
    bad = good.encode("utf-8").decode("cp1252")
    assert "Ã" in bad or "\xa0" in bad
    assert svn.repair_mojibake_path(bad) == good


def test_repair_mojibake_path_leaves_ascii_alone():
    path = "webpage/doc_images/SP/foo.png"
    assert svn.repair_mojibake_path(path) == path


def test_resolve_wc_relative_path_repairs_when_needed(tmp_path):
    good_name = "mise_à_jour"
    folder = tmp_path / "webpage" / good_name
    folder.mkdir(parents=True)
    (folder / "a.png").write_bytes(b"x")

    bad_rel = "webpage/" + good_name.encode("utf-8").decode("cp1252") + "/a.png"
    assert not os.path.exists(os.path.join(tmp_path, bad_rel))

    resolved = svn.resolve_wc_relative_path(str(tmp_path), bad_rel)
    assert os.path.exists(os.path.join(tmp_path, resolved))
    assert "à" in resolved


def test_run_svn_forces_utf8_encoding(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    monkeypatch.setattr(svn.subprocess, "run", fake_run)
    svn.run_svn(["svn", "info"])
    assert captured.get("encoding") == "utf-8"
    assert captured.get("text") is True
    assert captured.get("capture_output") is True


def test_run_svn_allows_stdout_devnull(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return MagicMock(returncode=0, stdout=None, stderr=None)

    monkeypatch.setattr(svn.subprocess, "run", fake_run)
    svn.run_svn(["svn", "export", "a", "b"], check=True, stdout=svn.subprocess.DEVNULL)
    assert "capture_output" not in captured
    assert captured.get("stdout") is svn.subprocess.DEVNULL

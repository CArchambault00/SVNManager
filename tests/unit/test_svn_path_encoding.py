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


def test_run_svn_with_path_args_passes_plain_paths(monkeypatch):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = list(args)
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(svn.subprocess, "run", fake_run)
    svn.run_svn_with_path_args(["svn", "unlock"], ["webpage/a.asp", "webpage/b.asp"])
    assert captured["args"] == ["svn", "unlock", "--", "webpage/a.asp", "webpage/b.asp"]


def test_run_svn_with_path_args_uses_targets_for_spaces(monkeypatch, tmp_path):
    captured = {}

    def fake_run(args, **kwargs):
        captured["args"] = list(args)
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(svn.subprocess, "run", fake_run)
    spaced = "webpage/Blown Film/Bag Type/a.asp"
    svn.run_svn_with_path_args(["svn", "unlock"], [spaced])
    assert captured["args"][:2] == ["svn", "unlock"]
    assert "--targets" in captured["args"]
    assert spaced not in captured["args"]
    assert captured["args"][captured["args"].index("--targets") + 1].endswith(".txt")


def test_run_svn_with_path_args_escapes_at_sign(monkeypatch):
    captured = {}
    written = {}

    def fake_run(args, **kwargs):
        captured["args"] = list(args)
        idx = args.index("--targets")
        with open(args[idx + 1], encoding="utf-8") as fh:
            written["body"] = fh.read()
        return MagicMock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(svn.subprocess, "run", fake_run)
    svn.run_svn_with_path_args(["svn", "info", "--xml"], ["webpage/foo@bar.asp"])
    assert "--targets" in captured["args"]
    assert written["body"].strip() == "webpage/foo@bar.asp@"


def test_svn_escape_path_and_scope_helpers():
    assert svn._svn_escape_path(r"webpage\a.asp") == "webpage/a.asp"
    assert svn._svn_escape_path("webpage/foo@bar.asp") == "webpage/foo@bar.asp@"
    assert svn._svn_escape_path("webpage/foo@bar.asp@") == "webpage/foo@bar.asp@"
    assert svn.path_in_svn_scope("webpage/a.asp", "webpage") is True
    assert svn.path_in_svn_scope("webpage_old/a.asp", "webpage") is False
    assert svn.path_in_svn_scope("mywebpage/a.asp", "webpage") is False
    assert svn.path_in_svn_scope("Projects/x.asp", "") is False
    assert svn.path_in_svn_scope("webpage/x.asp", "") is True
    assert svn._paths_need_targets_file(["webpage/-odd.asp"]) is True

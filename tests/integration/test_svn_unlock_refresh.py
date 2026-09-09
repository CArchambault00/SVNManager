"""Additional SVN integration tests: unlock, refresh locked, revert, get_all_locked_files."""

from unittest.mock import MagicMock

import pytest

import svn_operations as svn

LOCKED_STATUS_XML = """<?xml version="1.0"?>
<status>
  <target path=".">
    <entry path="webpage/a.asp">
      <wc-status item="normal" revision="10">
        <commit revision="10"/>
        <lock>
          <owner>tester</owner>
          <created>2026-01-15T18:30:00.000000Z</created>
        </lock>
      </wc-status>
    </entry>
    <entry path="webpage/other.asp">
      <wc-status item="normal" revision="11">
        <commit revision="11"/>
        <lock>
          <owner>someoneelse</owner>
          <created>2026-01-15T18:30:00.000000Z</created>
        </lock>
      </wc-status>
    </entry>
    <entry path="webpage/free.asp">
      <wc-status item="normal" revision="12">
        <commit revision="12"/>
      </wc-status>
    </entry>
  </target>
</status>
"""


def _svn_run_with_status(args, *a, **kwargs):
    result = MagicMock()
    result.returncode = 0
    result.stderr = ""
    result.stdout = ""
    if args and args[0] == "svn":
        sub = args[1] if len(args) > 1 else ""
        if sub == "info" and "--show-item" in args and "wc-root" in args:
            result.stdout = "C:/svn/wc\n"
        elif sub == "status":
            result.stdout = LOCKED_STATUS_XML
        elif sub in ("lock", "unlock", "revert", "commit"):
            result.stdout = "OK\n"
    return result


def test_unlock_files_success(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    monkeypatch.setattr(svn.subprocess, "run", _svn_run_with_status)
    monkeypatch.setattr(svn, "refresh_locked_files", MagicMock())
    svn.unlock_files(["webpage/a.asp"], MagicMock())
    mock_messagebox.showinfo.assert_called()
    svn.refresh_locked_files.assert_called_once()


def test_revert_files(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    calls = []

    def tracking_run(args, *a, **kwargs):
        calls.append(list(args))
        return _svn_run_with_status(args, *a, **kwargs)

    monkeypatch.setattr(svn.subprocess, "run", tracking_run)
    svn.revert_files(["webpage/a.asp"])
    assert any(c[:2] == ["svn", "revert"] for c in calls)


def test_refresh_locked_files_inserts_user_locks(
    tmp_appdata, sample_config, mock_messagebox, monkeypatch, tk_root
):
    from tkinter import ttk

    monkeypatch.setattr(svn.subprocess, "run", _svn_run_with_status)
    monkeypatch.setattr(svn, "get_relative_path", MagicMock(return_value=""))

    tree = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    svn.refresh_locked_files(tree)

    files = [tree.item(i, "values")[2] for i in tree.get_children()]
    assert "webpage/a.asp" in files
    assert "webpage/other.asp" not in files  # other owner
    assert "webpage/free.asp" not in files  # unlocked


def test_refresh_locked_files_invalid_path(tmp_appdata, mock_messagebox, monkeypatch):
    monkeypatch.setattr(
        svn,
        "load_config",
        MagicMock(return_value={"svn_path": "C:/does/not/exist/path", "username": "tester"}),
    )
    svn.refresh_locked_files(MagicMock())
    mock_messagebox.showwarning.assert_called()


def test_get_all_locked_files(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    monkeypatch.setattr(svn.subprocess, "run", _svn_run_with_status)
    monkeypatch.setattr(svn, "get_relative_path", MagicMock(return_value=""))
    locked = svn.get_all_locked_files()
    paths = [p[0] for p in locked]
    assert paths == ["webpage/a.asp"]


def test_lock_reports_locked_by_others(tmp_appdata, sample_config, mock_messagebox, monkeypatch):
    def run_lock_fail(args, *a, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = "C:/svn/wc\n"
        if args and len(args) > 1 and args[1] == "lock":
            result.returncode = 1
            result.stderr = "Path '/webpage/a.asp' is already locked by user 'bob'\n"
        return result

    monkeypatch.setattr(svn.subprocess, "run", run_lock_fail)
    monkeypatch.setattr(svn, "refresh_locked_files", MagicMock())
    svn.lock_files(["webpage/a.asp"], MagicMock())
    mock_messagebox.showerror.assert_called()

"""Unit tests for multi-file SVN helpers and lock XML parsing."""

from unittest.mock import MagicMock

import pytest

import svn_operations as svn


MULTI_INFO_XML = """<?xml version="1.0"?>
<info>
  <entry path="webpage/a.asp" revision="10">
    <commit revision="10"/>
    <lock>
      <owner>tester</owner>
      <created>2026-01-15T18:30:00.000000Z</created>
    </lock>
  </entry>
  <entry path="webpage/b.asp" revision="11">
    <commit revision="11"/>
  </entry>
</info>
"""


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
    <entry path="Projects/other.asp">
      <wc-status item="normal" revision="11">
        <commit revision="11"/>
        <lock>
          <owner>tester</owner>
          <created>2026-01-15T18:30:00.000000Z</created>
        </lock>
      </wc-status>
    </entry>
  </target>
</status>
"""


def test_parse_user_locks_from_status_xml_filters_owner_and_projects():
    locked = svn._parse_user_locks_from_status_xml(LOCKED_STATUS_XML, "tester", "")
    paths = [p[0] for p in locked]
    assert paths == ["webpage/a.asp"]


def test_parse_user_locks_with_scope_relative():
    locked = svn._parse_user_locks_from_status_xml(
        LOCKED_STATUS_XML, "tester", "webpage"
    )
    paths = [p[0] for p in locked]
    assert paths == ["webpage/a.asp"]


def test_get_file_info_batch_multi_path(tmp_appdata, sample_config, monkeypatch):
    calls = []

    def run(args, *a, **kwargs):
        calls.append(list(args))
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        if args[:3] == ["svn", "info", "--show-item"] and "wc-root" in args:
            result.stdout = "C:/svn/wc\n"
        elif args[:3] == ["svn", "info", "--xml"]:
            result.stdout = MULTI_INFO_XML
        else:
            result.stdout = ""
        return result

    monkeypatch.setattr(svn.subprocess, "run", run)
    monkeypatch.setattr(svn.os.path, "exists", lambda p: True)
    monkeypatch.setattr(svn, "load_config", MagicMock(return_value={
        "username": "tester",
        "svn_path": "C:/svn/wc",
    }))

    results = svn.get_file_info_batch(["webpage/a.asp", "webpage/b.asp"])

    info_calls = [c for c in calls if c[:3] == ["svn", "info", "--xml"]]
    assert len(info_calls) == 1
    assert "webpage/a.asp" in info_calls[0]
    assert "webpage/b.asp" in info_calls[0]

    assert results["webpage/a.asp"][0] is True
    assert results["webpage/a.asp"][1] == "tester"
    assert results["webpage/a.asp"][2] == "10"
    assert results["webpage/b.asp"][0] is False
    assert results["webpage/b.asp"][2] == "11"


def test_get_file_info_batch_missing_file(tmp_appdata, sample_config, monkeypatch):
    monkeypatch.setattr(svn, "get_wc_root", MagicMock(return_value="C:/svn/wc"))
    monkeypatch.setattr(svn.os.path, "exists", lambda p: False)
    monkeypatch.setattr(svn, "load_config", MagicMock(return_value={
        "username": "tester",
        "svn_path": "C:/svn/wc",
    }))
    results = svn.get_file_info_batch(["missing.asp"])
    assert results["missing.asp"] == (False, "", "", "")


def test_update_listbox_removes_unlocked(tmp_appdata, sample_config, monkeypatch, tk_root):
    from tkinter import ttk

    tree = ttk.Treeview(tk_root, columns=("Status", "Version", "File", "Lock Date"), show="headings")
    item = tree.insert("", "end", values=("locked", "10", "webpage/a.asp", "2026-01-01"))
    tree.insert("", "end", values=("locked", "11", "webpage/b.asp", "2026-01-01"))

    monkeypatch.setattr(
        svn,
        "get_file_info_batch",
        MagicMock(return_value={
            "webpage/a.asp": (False, "", "10", ""),
            "webpage/b.asp": (True, "tester", "11", "2026-01-01"),
        }),
    )
    svn.update_listbox_file_info(
        tree,
        paths=["webpage/a.asp", "webpage/b.asp"],
        remove_if_not_user_locked=True,
    )
    remaining = [tree.item(i, "values")[2] for i in tree.get_children()]
    assert remaining == ["webpage/b.asp"]


def test_scope_relative_path_unmappable():
    assert svn.scope_relative_path("D:/other", "C:/svn/wc") == ""
    assert svn.scope_relative_path("C:/svn/wc/webpage", "C:/svn/wc") == "webpage"

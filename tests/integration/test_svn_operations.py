"""Integration tests for svn_operations with mocked SVN CLI."""

from unittest.mock import MagicMock, patch

import pytest

import svn_operations as svn


def test_is_svn_repo_root_true(mock_svn):
    assert svn.is_svn_repo_root("C:/svn/wc") is True


def test_is_svn_repo_root_false_on_error(monkeypatch):
    def boom(*a, **k):
        raise svn.subprocess.CalledProcessError(1, "svn")

    monkeypatch.setattr(svn.subprocess, "run", boom)
    assert svn.is_svn_repo_root("C:/not-svn") is False


def test_get_relative_path(mock_svn):
    rel = svn.get_relative_path("C:/svn/wc/webpage/a.asp")
    assert rel == "webpage/a.asp"


def test_lock_files_success(tmp_appdata, sample_config, mock_svn, mock_messagebox, monkeypatch):
    listbox = MagicMock()
    monkeypatch.setattr(svn, "update_listbox_file_info", MagicMock())
    svn.lock_files(["webpage/a.asp"], listbox)
    mock_messagebox.showinfo.assert_called()
    svn.update_listbox_file_info.assert_called_once_with(
        listbox, paths=["webpage/a.asp"], remove_if_not_user_locked=False
    )


def test_lock_files_no_selection(tmp_appdata, sample_config, mock_svn, mock_messagebox, monkeypatch):
    monkeypatch.setattr(svn, "update_listbox_file_info", MagicMock())
    svn.lock_files([], MagicMock())
    mock_messagebox.showerror.assert_called()


def test_commit_files(tmp_appdata, sample_config, mock_svn, mock_messagebox):
    svn.commit_files(["webpage/a.asp"], unlock_files=False)


def test_build_tortoise_diff_cmdline_quotes_path_value():
    """Tortoise requires /path:"..." around the path, not the whole switch."""
    cmdline = svn.build_tortoise_diff_cmdline(
        r"C:\Program Files\TortoiseSVN\bin\TortoiseProc.exe",
        r"D:\my repo\webpage\a.asp",
    )
    assert cmdline.startswith('"C:\\Program Files\\TortoiseSVN\\bin\\TortoiseProc.exe"')
    assert '/command:diff' in cmdline
    assert '/path:"D:\\my repo\\webpage\\a.asp"' in cmdline
    # Must NOT be the broken list2cmdline form that quotes the whole /path: token
    assert '"/path:D:\\my repo\\webpage\\a.asp"' not in cmdline


def test_find_tortoise_proc_program_files(tmp_path, monkeypatch, tmp_appdata):
    pf = tmp_path / "PF"
    exe = pf / "TortoiseSVN" / "bin" / "TortoiseProc.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("ProgramFiles", str(pf))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "PFx86"))
    monkeypatch.setattr(svn, "_registry_tortoise_directory", lambda: None)
    monkeypatch.setattr(svn.shutil, "which", lambda _n: None)
    found = svn.find_tortoise_proc()
    assert found == str(exe)


def test_find_tortoise_proc_path_fallback(tmp_path, monkeypatch, tmp_appdata):
    exe = tmp_path / "TortoiseProc.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(svn, "_registry_tortoise_directory", lambda: None)
    monkeypatch.setenv("ProgramFiles", str(tmp_path / "empty_pf"))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "empty_pfx86"))
    monkeypatch.setattr(svn.shutil, "which", lambda _n: str(exe))
    assert svn.find_tortoise_proc() == str(exe)


def test_launch_tortoise_diff_success(monkeypatch, tmp_appdata):
    monkeypatch.setattr(svn, "find_tortoise_proc", lambda: r"C:\TortoiseSVN\bin\TortoiseProc.exe")
    proc = MagicMock()
    proc.poll.return_value = None
    popen = MagicMock(return_value=proc)
    monkeypatch.setattr(svn.subprocess, "Popen", popen)
    assert svn.launch_tortoise_diff(r"D:\wc\file with spaces.asp") is True
    cmdline = popen.call_args[0][0]
    assert isinstance(cmdline, str)
    assert popen.call_args.kwargs.get("shell") is False
    assert '/command:diff' in cmdline
    assert '/path:"D:\\wc\\file with spaces.asp"' in cmdline
    assert '"/path:D:\\wc\\file with spaces.asp"' not in cmdline


def test_unlock_uses_targets_file_for_spaced_paths(
    tmp_appdata, sample_config, mock_messagebox, monkeypatch
):
    calls = []

    def tracking_run(args, *a, **kwargs):
        calls.append(list(args))
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = "C:/svn/wc\n" if "--show-item" in args else "OK\n"
        return result

    monkeypatch.setattr(svn.subprocess, "run", tracking_run)
    monkeypatch.setattr(svn, "update_listbox_file_info", MagicMock())
    spaced = "webpage/Blown Film/Bag Type/BagTypeLookup.asp"
    svn.unlock_files([spaced], MagicMock())

    unlock_calls = [c for c in calls if len(c) > 1 and c[1] == "unlock"]
    assert unlock_calls
    assert "--targets" in unlock_calls[0]
    assert spaced not in unlock_calls[0]  # path goes in the targets file, not argv


def test_commit_uses_targets_file_for_spaced_paths(
    tmp_appdata, sample_config, mock_messagebox, monkeypatch
):
    calls = []

    def tracking_run(args, *a, **kwargs):
        calls.append(list(args))
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        result.stdout = "C:/svn/wc\n" if "--show-item" in args else "OK\n"
        return result

    monkeypatch.setattr(svn.subprocess, "run", tracking_run)
    spaced = "webpage/Blown Film/a.asp"
    svn.commit_files([spaced], unlock_files=True)

    commit_calls = [c for c in calls if len(c) > 1 and c[1] == "commit"]
    assert commit_calls
    assert "--targets" in commit_calls[0]
    assert "--no-unlock" not in commit_calls[0]


def test_launch_tortoise_diff_missing(monkeypatch, tmp_appdata):
    monkeypatch.setattr(svn, "find_tortoise_proc", lambda: None)
    assert svn.launch_tortoise_diff(r"D:\wc\a.asp") is False


def test_view_file_native_diff_tortoise_success(tmp_path, monkeypatch, mock_messagebox, tmp_appdata, sample_config):
    wc = tmp_path / "wc"
    target = wc / "webpage"
    target.mkdir(parents=True)
    file_path = target / "a.asp"
    file_path.write_text("x", encoding="utf-8")

    monkeypatch.setattr(svn, "get_wc_root", lambda _p=None: str(wc).replace("\\", "/"))
    monkeypatch.setattr(svn, "resolve_wc_relative_path", lambda _wc, rel: rel.replace("\\", "/"))
    launch = MagicMock(return_value=True)
    monkeypatch.setattr(svn, "launch_tortoise_diff", launch)
    text_fb = MagicMock()
    monkeypatch.setattr(svn, "_show_text_diff_fallback", text_fb)

    svn.view_file_native_diff("webpage/a.asp")
    launch.assert_called_once()
    text_fb.assert_not_called()
    activity = (tmp_appdata / "SVNManager_activity.log").read_text(encoding="utf-8")
    assert "View Diff requested" in activity


def test_view_file_native_diff_text_fallback(tmp_path, monkeypatch, mock_messagebox, tmp_appdata, sample_config):
    wc = tmp_path / "wc"
    target = wc / "webpage"
    target.mkdir(parents=True)
    (target / "a.asp").write_text("x", encoding="utf-8")

    monkeypatch.setattr(svn, "get_wc_root", lambda _p=None: str(wc).replace("\\", "/"))
    monkeypatch.setattr(svn, "resolve_wc_relative_path", lambda _wc, rel: rel.replace("\\", "/"))
    monkeypatch.setattr(svn, "launch_tortoise_diff", lambda _p: False)

    shown = MagicMock()
    monkeypatch.setattr(svn, "_show_text_diff_fallback", shown)
    svn.view_file_native_diff("webpage/a.asp")
    shown.assert_called_once()
    activity = (tmp_appdata / "SVNManager_activity.log").read_text(encoding="utf-8")
    assert "falling back to text window" in activity


def test_view_file_native_diff_empty_diff_message(tmp_path, monkeypatch, mock_messagebox, tmp_appdata, sample_config):
    wc = tmp_path / "wc"
    target = wc / "webpage"
    target.mkdir(parents=True)
    (target / "a.asp").write_text("x", encoding="utf-8")

    monkeypatch.setattr(svn, "get_wc_root", lambda _p=None: str(wc).replace("\\", "/"))
    monkeypatch.setattr(svn, "resolve_wc_relative_path", lambda _wc, rel: rel.replace("\\", "/"))
    monkeypatch.setattr(svn, "launch_tortoise_diff", lambda _p: False)
    monkeypatch.setattr(
        svn,
        "run_svn",
        lambda *a, **k: MagicMock(returncode=0, stdout="", stderr=""),
    )
    svn.view_file_native_diff("webpage/a.asp")
    mock_messagebox.showinfo.assert_called()
    activity = (tmp_appdata / "SVNManager_activity.log").read_text(encoding="utf-8")
    assert "View Diff no differences" in activity

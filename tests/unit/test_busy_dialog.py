"""Tests for busy_dialog loading UI helpers."""

from unittest.mock import MagicMock
import threading
import time

import busy_dialog as bd


def test_call_on_main_thread_without_session_runs_inline():
    called = []
    result = bd.call_on_main_thread(lambda: called.append(1) or 42)
    assert result == 42
    assert called == [1]


def test_run_with_busy_dialog_runs_work(tk_root, monkeypatch):
    done = threading.Event()
    seen = []
    completed = []

    # Avoid grabbing / centering issues in headless
    monkeypatch.setattr(bd.BusySession, "_center_on_parent", lambda self: None)

    def work(set_status):
        set_status("Working…")
        seen.append("ran")
        done.set()

    bd.run_with_busy_dialog(
        tk_root,
        "Test",
        work,
        initial_status="Start",
        on_complete=lambda: completed.append(True),
    )
    assert done.wait(timeout=3)
    bd.wait_until_idle(tk_root)
    assert "ran" in seen
    assert bd._active_session is None
    assert completed == [True]


def test_messagebox_hook_marshals_to_main(tk_root, monkeypatch):
    monkeypatch.setattr(bd.BusySession, "_center_on_parent", lambda self: None)

    call_threads = []
    stub_info = MagicMock(
        side_effect=lambda *a, **k: call_threads.append(threading.current_thread().ident)
    )
    monkeypatch.setattr("tkinter.messagebox.showinfo", stub_info)

    done = threading.Event()
    worker_id = []

    def work(set_status):
        from tkinter import messagebox

        worker_id.append(threading.current_thread().ident)
        messagebox.showinfo("T", "M")
        done.set()

    bd.run_with_busy_dialog(tk_root, "Test", work)
    deadline = time.time() + 5
    while time.time() < deadline and not done.is_set():
        tk_root.update()
        time.sleep(0.02)
    assert done.is_set()
    bd.wait_until_idle(tk_root)

    stub_info.assert_called_once()
    assert worker_id and worker_id[0] != threading.main_thread().ident
    assert call_threads and call_threads[0] == threading.main_thread().ident

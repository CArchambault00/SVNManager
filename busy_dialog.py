"""Modal busy/loading dialog for long-running work without freezing the UI."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional, Any, Dict, List

_main_thread = threading.main_thread()
_active_session: Optional["BusySession"] = None
# Stack of pre-hook messagebox callables so restore preserves test mocks / nesting.
_hook_stack: List[Dict[str, Callable]] = []


def _install_messagebox_hooks():
    _hook_stack.append(
        {
            "showinfo": messagebox.showinfo,
            "showerror": messagebox.showerror,
            "showwarning": messagebox.showwarning,
            "askyesno": messagebox.askyesno,
        }
    )
    messagebox.showinfo = _hook_showinfo
    messagebox.showerror = _hook_showerror
    messagebox.showwarning = _hook_showwarning
    messagebox.askyesno = _hook_askyesno


def _restore_messagebox_hooks():
    if not _hook_stack:
        return
    prev = _hook_stack.pop()
    messagebox.showinfo = prev["showinfo"]
    messagebox.showerror = prev["showerror"]
    messagebox.showwarning = prev["showwarning"]
    messagebox.askyesno = prev["askyesno"]


def _force_clear_session():
    """Drop a stale session (destroyed parent / abandoned test)."""
    global _active_session
    session = _active_session
    _active_session = None
    if session is not None:
        try:
            session._alive = False
            session._close_now()
        except Exception:
            pass
    while _hook_stack:
        _restore_messagebox_hooks()


def _session_alive() -> bool:
    if _active_session is None:
        return False
    try:
        return bool(_active_session.win.winfo_exists())
    except tk.TclError:
        return False


def _underlying(name: str) -> Callable:
    if _hook_stack:
        return _hook_stack[-1][name]
    return getattr(messagebox, name)


def _hook_showinfo(title, message, **kwargs):
    if _active_session and threading.current_thread() is not _main_thread:
        return _active_session.ui_showinfo(title, message)
    return _underlying("showinfo")(title, message, **kwargs)


def _hook_showerror(title, message, **kwargs):
    if _active_session and threading.current_thread() is not _main_thread:
        return _active_session.ui_showerror(title, message)
    return _underlying("showerror")(title, message, **kwargs)


def _hook_showwarning(title, message, **kwargs):
    if _active_session and threading.current_thread() is not _main_thread:
        return _active_session.ui_showwarning(title, message)
    return _underlying("showwarning")(title, message, **kwargs)


def _hook_askyesno(title, message, **kwargs):
    if _active_session and threading.current_thread() is not _main_thread:
        return _active_session.ui_askyesno(title, message)
    return _underlying("askyesno")(title, message, **kwargs)


class BusySession:
    """Indeterminate progress dialog + main-thread marshaling for Tk calls."""

    def __init__(self, parent: tk.Misc, title: str, initial_status: str = "Please wait..."):
        self.parent = parent
        self._queue: queue.Queue = queue.Queue()
        self._alive = True
        self._worker_done = False
        self._on_complete: Optional[Callable[[], None]] = None

        self.win = tk.Toplevel(parent)
        self.win.title(title)
        self.win.resizable(False, False)
        self.win.transient(parent.winfo_toplevel())
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)  # block close while busy

        frame = ttk.Frame(self.win, padding=16)
        frame.pack(fill="both", expand=True)

        self.status_var = tk.StringVar(value=initial_status)
        ttk.Label(frame, textvariable=self.status_var, wraplength=360).pack(anchor="w", pady=(0, 10))

        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=360)
        self.progress.pack(fill="x")
        self.progress.start(12)

        self.win.update_idletasks()
        self._center_on_parent()
        try:
            self.win.grab_set()
        except tk.TclError:
            pass

        self._poll()

    def _center_on_parent(self):
        try:
            self.win.update_idletasks()
            pw = self.parent.winfo_toplevel()
            x = pw.winfo_rootx() + (pw.winfo_width() - self.win.winfo_width()) // 2
            y = pw.winfo_rooty() + (pw.winfo_height() - self.win.winfo_height()) // 2
            self.win.geometry(f"+{max(0, x)}+{max(0, y)}")
        except tk.TclError:
            pass

    def set_status(self, text: str) -> None:
        self._queue.put(("status", text))

    def call_on_main(self, fn: Callable[[], Any]) -> Any:
        """Run fn on the Tk main thread and wait for the result."""
        if threading.current_thread() is _main_thread:
            return fn()
        done = threading.Event()
        box: dict = {}

        def runner():
            try:
                box["result"] = fn()
            except Exception as exc:
                box["error"] = exc
            finally:
                done.set()

        self._queue.put(("call", runner))
        done.wait()
        if "error" in box:
            raise box["error"]
        return box.get("result")

    def ui_showinfo(self, title, message):
        return self.call_on_main(lambda: _underlying("showinfo")(title, message))

    def ui_showerror(self, title, message):
        return self.call_on_main(lambda: _underlying("showerror")(title, message))

    def ui_showwarning(self, title, message):
        return self.call_on_main(lambda: _underlying("showwarning")(title, message))

    def ui_askyesno(self, title, message):
        return self.call_on_main(lambda: _underlying("askyesno")(title, message))

    def _poll(self):
        global _active_session
        try:
            while True:
                kind, *payload = self._queue.get_nowait()
                if kind == "status":
                    self.status_var.set(payload[0])
                elif kind == "call":
                    payload[0]()
                elif kind == "done":
                    self._close_now()
                    _restore_messagebox_hooks()
                    _active_session = None
                    if self._on_complete is not None:
                        try:
                            self._on_complete()
                        except Exception:
                            pass
                    return
                elif kind == "close":
                    self._close_now()
                    return
        except queue.Empty:
            pass

        if self._alive:
            try:
                if not self.win.winfo_exists():
                    raise tk.TclError("busy window gone")
                self.parent.after(50, self._poll)
            except tk.TclError:
                self._alive = False
                _force_clear_session()

    def _close_now(self):
        self._alive = False
        try:
            self.progress.stop()
        except tk.TclError:
            pass
        try:
            self.win.grab_release()
        except tk.TclError:
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    def request_close(self):
        self._queue.put(("close",))

    def mark_done(self):
        self._queue.put(("done",))


def run_with_busy_dialog(
    parent: tk.Misc,
    title: str,
    work_fn: Callable[[Callable[[str], None]], Any],
    initial_status: str = "Please wait...",
    on_complete: Optional[Callable[[], None]] = None,
) -> None:
    """
    Show a loading dialog and run work_fn(set_status) on a background thread.

    Tk messagebox calls from the worker are marshaled to the main thread.
    on_complete runs on the main thread after the dialog closes (if provided).
    """
    global _active_session

    if _session_alive():
        # Avoid nested busy dialogs; run inline under the existing session
        work_fn(lambda _msg: None)
        if on_complete is not None:
            on_complete()
        return
    if _active_session is not None:
        _force_clear_session()

    root = parent.winfo_toplevel()
    session = BusySession(root, title, initial_status=initial_status)
    session._on_complete = on_complete
    _active_session = session
    _install_messagebox_hooks()

    def worker():
        try:
            work_fn(session.set_status)
        except Exception as exc:
            try:
                session.ui_showerror("Error", str(exc))
            except Exception:
                pass
        finally:
            session.mark_done()

    threading.Thread(target=worker, daemon=True).start()


def wait_until_idle(root: tk.Misc, timeout: float = 5.0) -> None:
    """Pump Tk events until no busy session remains (tests / post-work sync)."""
    import time

    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _session_alive() and _active_session is None:
            return
        try:
            root.update()
        except tk.TclError:
            _force_clear_session()
            return
        time.sleep(0.02)
    _force_clear_session()


def call_on_main_thread(fn: Callable[[], Any]) -> Any:
    """Run fn on the Tk main thread (used for menu switches after background work)."""
    if _active_session is not None:
        return _active_session.call_on_main(fn)
    return fn()


def wrap_callback(parent: tk.Misc, title: str, fn: Callable[[], Any], initial_status: str = "Please wait..."):
    """Return a zero-arg callback that runs fn under a busy dialog."""

    def _run():
        run_with_busy_dialog(parent, title, lambda _set_status: fn(), initial_status=initial_status)

    return _run

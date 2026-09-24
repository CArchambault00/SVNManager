"""Busy-dialog wrappers for long UI loads (SVN / DB) without freezing Tk."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from busy_dialog import call_on_main_thread, run_with_busy_dialog


LockedRow = Tuple[str, str, str]  # path, revision, lock_date


def fetch_locked_files() -> List[LockedRow]:
    """SVN I/O only — safe for worker threads."""
    from svn_operations import get_all_locked_files

    return list(get_all_locked_files() or [])


def apply_locked_files_to_tree(
    treeview,
    locked_files: Sequence[LockedRow],
    *,
    exclude_paths: Optional[set] = None,
    tags: Tuple[str, ...] = (),
) -> None:
    """Populate a Treeview with locked-file rows (main thread only)."""
    treeview.delete(*treeview.get_children())
    exclude = exclude_paths or set()
    for path, revision, lock_date in locked_files:
        if path in exclude:
            continue
        kwargs = {}
        if tags:
            kwargs["tags"] = tags
        treeview.insert(
            "",
            "end",
            values=("locked", revision, path, lock_date),
            **kwargs,
        )


def existing_paths_from_tree(treeview) -> set:
    return {
        treeview.item(item, "values")[2]
        for item in treeview.get_children()
    }


def load_locked_files_busy(
    parent,
    treeview,
    *,
    exclude_treeview=None,
    title: str = "Refreshing locked files",
    initial_status: str = "Querying SVN…",
    tags: Tuple[str, ...] = (),
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    """Fetch locked files in background and fill treeview on the main thread."""

    def work(set_status):
        try:
            set_status("Querying SVN for locked files…")
            locked_files = fetch_locked_files()

            def apply():
                set_status("Updating list…")
                exclude = (
                    existing_paths_from_tree(exclude_treeview)
                    if exclude_treeview is not None
                    else set()
                )
                apply_locked_files_to_tree(
                    treeview, locked_files, exclude_paths=exclude, tags=tags
                )
                try:
                    treeview.update_idletasks()
                except Exception:
                    pass

            call_on_main_thread(apply)
        finally:
            if on_done is not None:
                call_on_main_thread(on_done)

    run_with_busy_dialog(parent, title, work, initial_status=initial_status)


def fetch_patches(temp, application_id) -> List[Dict[str, Any]]:
    from db_handler import dbClass

    db = dbClass()
    return list(db.get_patch_list(temp, application_id) or [])


def apply_patches_to_tree(treeview, patches: Sequence[Dict[str, Any]]) -> None:
    """Clear tree + patch_info_dict and insert rows (main thread only)."""
    import patches_operations as po

    for item in treeview.get_children():
        treeview.delete(item)
    po.patch_info_dict.clear()

    for patch in patches:
        name = patch.get("NAME") or ""
        comments = (patch.get("COMMENTS") or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        patch_size = patch.get("PATCH_SIZE") or 0
        user_id = patch.get("USER_ID") or ""
        creation_date = patch.get("CREATION_DATE") or ""
        checklist_count = patch.get("CHECK_LIST_COUNT") or ""
        po.patch_info_dict[name] = patch
        treeview.insert(
            "",
            "end",
            values=(name, comments, patch_size, user_id, creation_date, checklist_count),
        )


def load_patches_busy(
    parent,
    treeview,
    temp,
    application_id,
    *,
    title: str = "Loading patches",
    initial_status: str = "Querying database…",
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    def work(set_status):
        try:
            set_status("Querying database…")
            patches = fetch_patches(temp, application_id)

            def apply():
                set_status("Updating list…")
                apply_patches_to_tree(treeview, patches)

            call_on_main_thread(apply)
        finally:
            if on_done is not None:
                call_on_main_thread(on_done)

    run_with_busy_dialog(parent, title, work, initial_status=initial_status)


def fetch_patch_file_rows(patch_info) -> List[Tuple[str, Any, str, str]]:
    """Return list of (status, version, path, lock_date) for a patch."""
    from db_handler import dbClass
    from svn_operations import get_file_info_batch

    db = dbClass()
    files = db.get_patch_file_list_new(patch_info["PATCH_ID"])
    file_paths = [f["PATH"] for f in files]
    info_results = get_file_info_batch(file_paths) if file_paths else {}

    rows = []
    for file in files:
        file_path = file["PATH"]
        lock_by_user, lock_owner, _svn_revision, lock_date = info_results.get(
            file_path, (False, "", "", "")
        )
        if lock_by_user:
            status = "locked"
        elif lock_owner == "":
            status = "unlocked"
        else:
            status = f"@locked - {lock_owner}"
        rows.append((status, file["VERSION"], file_path, lock_date or ""))
    return rows


def apply_patch_file_rows(treeview, rows: Sequence[Tuple[str, Any, str, str]], *, select_all: bool = True) -> None:
    treeview.delete(*treeview.get_children())
    for status, version, path, lock_date in rows:
        item = treeview.insert("", "end", values=(status, version, path, lock_date))
        if select_all:
            treeview.selection_add(item)


def load_patch_files_busy(
    parent,
    treeview,
    patch_info,
    *,
    title: str = "Loading patch files",
    initial_status: str = "Loading…",
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    def work(set_status):
        try:
            set_status("Loading patch files from database…")
            rows = fetch_patch_file_rows(patch_info)

            def apply():
                set_status("Updating list…")
                apply_patch_file_rows(treeview, rows)

            call_on_main_thread(apply)
        finally:
            if on_done is not None:
                call_on_main_thread(on_done)

    run_with_busy_dialog(parent, title, work, initial_status=initial_status)


def load_modify_patch_screen_busy(
    parent,
    files_listbox,
    locked_treeview,
    patch_info,
    *,
    load_patch_files: bool,
    title: str = "Loading modify patch",
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    """One busy session: optional patch files + available locked files + status refresh."""

    def work(set_status):
        try:
            rows = None
            if load_patch_files and patch_info:
                set_status("Loading patch files…")
                rows = fetch_patch_file_rows(patch_info)

            set_status("Querying SVN for locked files…")
            locked_files = fetch_locked_files()

            def apply():
                if rows is not None:
                    set_status("Updating patch files…")
                    apply_patch_file_rows(files_listbox, rows)
                else:
                    set_status("Refreshing file status…")
                    from svn_operations import refresh_file_status_version

                    refresh_file_status_version(files_listbox)

                set_status("Updating locked files…")
                exclude = existing_paths_from_tree(files_listbox)
                apply_locked_files_to_tree(
                    locked_treeview, locked_files, exclude_paths=exclude
                )

            call_on_main_thread(apply)
        finally:
            if on_done is not None:
                call_on_main_thread(on_done)

    run_with_busy_dialog(parent, title, work, initial_status="Starting…")


def load_create_patch_screen_busy(
    parent,
    files_listbox,
    locked_treeview,
    *,
    title: str = "Loading create patch",
    on_done: Optional[Callable[[], None]] = None,
) -> None:
    def work(set_status):
        try:
            set_status("Querying SVN for locked files…")
            locked_files = fetch_locked_files()

            def apply():
                set_status("Refreshing file status…")
                from svn_operations import refresh_file_status_version

                refresh_file_status_version(files_listbox)
                set_status("Updating locked files…")
                exclude = existing_paths_from_tree(files_listbox)
                apply_locked_files_to_tree(
                    locked_treeview, locked_files, exclude_paths=exclude
                )

            call_on_main_thread(apply)
        finally:
            if on_done is not None:
                call_on_main_thread(on_done)

    run_with_busy_dialog(parent, title, work, initial_status="Starting…")


def lock_unlock_busy(parent, files, listbox, *, lock: bool) -> None:
    action = "Locking" if lock else "Unlocking"
    title = f"{action} files"

    def work(set_status):
        set_status(f"{action} {len(files)} file(s)…")
        from svn_operations import lock_files, unlock_files

        if lock:
            lock_files(files, listbox)
        else:
            unlock_files(files, listbox)

    run_with_busy_dialog(parent, title, work, initial_status=f"{action}…")


def refresh_file_status_busy(parent, files_listbox) -> None:
    def work(set_status):
        set_status("Refreshing file status…")

        def apply():
            from svn_operations import refresh_file_status_version

            refresh_file_status_version(files_listbox)

        call_on_main_thread(apply)

    run_with_busy_dialog(
        parent, "Refreshing files", work, initial_status="Starting…"
    )


def remove_patch_busy(parent, patch_info, on_success: Optional[Callable[[], None]] = None) -> None:
    """Ask confirm on main, then remove under busy dialog."""
    from tkinter import messagebox
    from patches_operations import remove_patch

    patch_name = patch_info.get("NAME", "")
    if not messagebox.askyesno(
        "Confirm Removal",
        f"Are you sure you want to remove patch '{patch_name}'?\nThis action cannot be undone.",
    ):
        return

    def work(set_status):
        set_status(f"Removing {patch_name}…")
        ok = remove_patch(patch_info, confirm=False)
        if ok and on_success is not None:
            call_on_main_thread(on_success)

    run_with_busy_dialog(parent, "Removing patch", work, initial_status="Starting…")


def handle_drop_busy(parent, event, listbox) -> None:
    """Process drag-and-drop under a busy dialog when there are new files."""
    import os
    import subprocess
    from tkinter import messagebox
    from config import load_config
    from svn_operations import get_wc_root, relative_to_wc_root, get_file_info_batch
    from buttons_function import _show_files_outside_svn_error

    files = listbox.tk.splitlist(event.data)
    config = load_config()
    svn_path = config.get("svn_path")

    if not svn_path:
        messagebox.showerror("Error", "SVN path not configured")
        return

    files_outside_svn = []
    files_to_process = []

    try:
        wc_root = get_wc_root(svn_path)
    except subprocess.SubprocessError as e:
        messagebox.showerror("Error", f"Failed to get SVN working copy root: {e}")
        return

    wc_root_n = wc_root.replace("\\", "/").rstrip("/")
    svn_path_n = svn_path.replace("\\", "/").rstrip("/")
    try:
        svn_relative_path = relative_to_wc_root(svn_path_n, wc_root_n)
    except ValueError:
        svn_relative_path = ""

    def is_file_in_svn_scope(file_path):
        file_n = file_path.replace("\\", "/")
        if not (file_n == wc_root_n or file_n.startswith(wc_root_n + "/")):
            return False
        file_relative_path = file_n[len(wc_root_n) :].lstrip("/")
        if svn_relative_path == "":
            return not file_relative_path.startswith("Projects")
        return (
            file_relative_path == svn_relative_path
            or file_relative_path.startswith(svn_relative_path + "/")
        )

    def normalize_file_path(file_path):
        return file_path.replace("\\", "/").replace(wc_root_n + "/", "")

    def process_file(file_path):
        if is_file_in_svn_scope(file_path):
            files_to_process.append(normalize_file_path(file_path))
        else:
            files_outside_svn.append(file_path)

    for item in files:
        if os.path.isfile(item):
            process_file(item)
        elif os.path.isdir(item):
            try:
                for root, _dirs, dir_files in os.walk(item):
                    for dir_file in dir_files:
                        process_file(os.path.join(root, dir_file))
            except OSError as e:
                messagebox.showerror("Error", f"Failed to process directory {item}: {e}")
        else:
            files_outside_svn.append(item)

    existing_files = {listbox.item(item, "values")[2] for item in listbox.get_children()}
    new_files = [f for f in files_to_process if f not in existing_files]

    if not new_files and not files_outside_svn:
        messagebox.showinfo("Info", "No new files to add - all selected files are already in the list.")
        return

    if not new_files:
        if files_outside_svn:
            _show_files_outside_svn_error(files_outside_svn)
        return

    def work(set_status):
        set_status(f"Looking up {len(new_files)} file(s) in SVN…")
        file_info_results = get_file_info_batch(new_files)

        def apply():
            set_status("Adding files to list…")
            BATCH_SIZE = 50
            total_files = len(new_files)
            for i in range(0, total_files, BATCH_SIZE):
                batch = new_files[i : i + BATCH_SIZE]
                for file in batch:
                    info = file_info_results.get(file, (False, "", "", ""))
                    lock_by_user, lock_owner, revision, lock_date = info
                    if lock_by_user:
                        status = "locked"
                    elif lock_owner == "":
                        status = "unlocked"
                    else:
                        status = f"@locked - {lock_owner}"
                    listbox.insert("", "end", values=(status, revision, file, lock_date))
                listbox.update_idletasks()

        call_on_main_thread(apply)
        if files_outside_svn:
            call_on_main_thread(lambda: _show_files_outside_svn_error(files_outside_svn))

    run_with_busy_dialog(parent, "Adding files", work, initial_status="Starting…")

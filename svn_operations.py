# svn_operations.py
import subprocess
from tkinter import messagebox
from config import load_config, verify_config, log_error, log_success
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone

def run_svn(args, **kwargs):
    """Run svn CLI with UTF-8 stdout/stderr (Windows default cp1252 corrupts accents)."""
    kwargs.setdefault("shell", False)
    if os.name == "nt":
        kwargs.setdefault("creationflags", subprocess.CREATE_NO_WINDOW)

    # capture_output cannot be combined with explicit stdout/stderr
    if "stdout" in kwargs or "stderr" in kwargs:
        kwargs.pop("capture_output", None)
    else:
        kwargs.setdefault("capture_output", True)

    if kwargs.get("capture_output") or kwargs.get("text"):
        kwargs.setdefault("text", True)
        kwargs.setdefault("encoding", "utf-8")
        kwargs.setdefault("errors", "surrogateescape")

    return subprocess.run(args, **kwargs)


def repair_mojibake_path(path):
    """
    Repair paths corrupted by decoding UTF-8 bytes as cp1252
    (e.g. 'à' -> 'Ã ' / 'Ã ').
    """
    if not path or not isinstance(path, str):
        return path
    try:
        repaired = path.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return path
    return repaired


def resolve_wc_relative_path(wc_root, rel_path):
    """Return a WC-relative path that exists, repairing mojibake when needed."""
    rel = (rel_path or "").replace("\\", "/")
    candidates = [rel]
    repaired = repair_mojibake_path(rel)
    if repaired != rel:
        candidates.append(repaired)
    for candidate in candidates:
        if os.path.exists(os.path.join(wc_root, candidate)):
            return candidate
    return rel



def get_wc_root(svn_path=None):
    """Return the SVN working-copy root for svn_path (or config svn_path)."""
    if svn_path is None:
        svn_path = load_config().get("svn_path")
    result = run_svn(
        ["svn", "info", "--show-item", "wc-root", svn_path],
        capture_output=True,
        text=True,
        shell=False,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return result.stdout.strip().replace("\\", "/")


def relative_to_wc_root(absolute_path, wc_root):
    """Return path relative to a known wc_root without an extra svn call."""
    abs_norm = absolute_path.replace("\\", "/")
    root_norm = wc_root.replace("\\", "/").rstrip("/")
    if not abs_norm.startswith(root_norm):
        raise ValueError(f"Path '{absolute_path}' is not under SVN working copy root '{wc_root}'")
    return abs_norm[len(root_norm):].lstrip("/")


def scope_relative_path(svn_path, wc_root):
    """Relative path of configured svn_path under wc_root; '' if at root or unmappable."""
    try:
        return relative_to_wc_root(svn_path, wc_root)
    except ValueError:
        return ""


def _format_lock_date(created_str):
    if not created_str:
        return ""
    try:
        dt_utc = datetime.strptime(created_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        return dt_utc.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            dt = datetime.strptime(created_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""


def _parse_info_entry(entry, username):
    """Parse one svn info --xml <entry> into (is_lock_by_user, lock_owner, revision, lock_date)."""
    commit = entry.find(".//commit")
    if commit is not None:
        revision = commit.get("revision", "")
    else:
        revision = entry.get("revision", "")

    lock = entry.find(".//lock")
    if lock is not None:
        lock_owner = lock.findtext("owner", "")
        lock_date = _format_lock_date(lock.findtext("created", ""))
        is_lock_by_user = lock_owner == username
    else:
        lock_owner = ""
        lock_date = ""
        is_lock_by_user = False

    return (is_lock_by_user, lock_owner, revision, lock_date)


def _match_info_path(entry_path, requested_paths, wc_root):
    """Map an XML entry path back to one of the requested relative paths."""
    path = (entry_path or "").replace("\\", "/")
    if path in requested_paths:
        return path
    root_norm = wc_root.replace("\\", "/").rstrip("/")
    if path.startswith(root_norm + "/"):
        rel = path[len(root_norm) + 1:]
        if rel in requested_paths:
            return rel
    basename_map = {}
    for req in requested_paths:
        base = req.replace("\\", "/").rsplit("/", 1)[-1]
        basename_map.setdefault(base, []).append(req)
    base = path.rsplit("/", 1)[-1]
    candidates = basename_map.get(base, [])
    if len(candidates) == 1:
        return candidates[0]
    for req in requested_paths:
        if path.endswith(req) or req.endswith(path):
            return req
    return None


def _status_to_values(lock_by_user, lock_owner, revision, file_path, lock_date):
    if lock_by_user:
        status = "locked"
    elif lock_owner == "":
        status = "unlocked"
    else:
        status = f"@locked - {lock_owner}"
    return (status, revision, file_path, lock_date)


def update_listbox_file_info(files_listbox, paths=None, remove_if_not_user_locked=False):
    """
    Update Status/Version/Lock Date for rows in the listbox.
    If paths is given, only those paths are refreshed.
    If remove_if_not_user_locked, delete rows that are no longer locked by the user.
    """
    path_filter = set(paths) if paths is not None else None
    items_by_path = {}
    for item in files_listbox.get_children():
        values = files_listbox.item(item, "values")
        file_path = values[2]
        if path_filter is None or file_path in path_filter:
            items_by_path[file_path] = item

    if not items_by_path:
        return

    file_info_results = get_file_info_batch(list(items_by_path.keys()))
    for file_path, item in items_by_path.items():
        lock_by_user, lock_owner, revision, lock_date = file_info_results.get(
            file_path, (False, "", "", "")
        )
        if remove_if_not_user_locked and not lock_by_user:
            files_listbox.delete(item)
            continue
        files_listbox.item(
            item,
            values=_status_to_values(lock_by_user, lock_owner, revision, file_path, lock_date),
        )


def _parse_user_locks_from_status_xml(status_xml, username, scope_relative_path):
    """
    Parse svn status --xml output into [(path, revision, lock_date), ...] for locks
    owned by username within the configured SVN scope.
    """
    locked_files = []
    root = ET.fromstring(status_xml)
    relative_path = (scope_relative_path or "").replace("\\", "/")

    for entry in root.findall(".//entry"):
        path = entry.get("path", "").replace("\\", "/")
        wc_status = entry.find("wc-status")

        commit = wc_status.find("commit") if wc_status is not None else None
        revision = commit.get("revision") if commit is not None else ""
        if not revision and wc_status is not None:
            revision = wc_status.get("revision", "")

        for status_tag in ["wc-status", "repos-status"]:
            lock = entry.find(f"{status_tag}/lock")
            if lock is None:
                continue
            owner = lock.findtext("owner")
            in_scope = (
                (relative_path and relative_path in path)
                or (not relative_path and not path.startswith("Projects"))
            )
            if owner == username and in_scope:
                lock_date = _format_lock_date(lock.findtext("created", ""))
                locked_files.append((path.replace("\\", "/"), revision, lock_date))
                break

    return locked_files


def lock_files(selected_files, patch_listbox):
    _lock_unlock_files(selected_files, patch_listbox, lock=True)

def unlock_files(selected_files, patch_listbox):
    _lock_unlock_files(selected_files, patch_listbox, lock=False)

def _lock_unlock_files(selected_files, patch_listbox, lock=True, batch_size=50):
    try:
        verify_config()
        config = load_config()
        username = config.get("username")
        svn_path = config.get("svn_path")

        if not selected_files:
            messagebox.showerror("Error", "No files selected to lock/unlock!")
            return

        command = "lock" if lock else "unlock"
        base_args = ["svn", command]

        if lock:
            lock_message = f"Locking by {username}"
            base_args += ["--message", lock_message]

        locked_by_others = []
        must_update_files = []
        wc_root = get_wc_root(svn_path)
        svn_targets = [
            resolve_wc_relative_path(wc_root, f) for f in selected_files
        ]

        # Process files in batches
        for i in range(0, len(svn_targets), batch_size):
            batch = svn_targets[i:i + batch_size]
            args = base_args + batch
            
            result = run_svn(
                args,
                cwd=wc_root,
                capture_output=True,
                text=True,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode != 0:
                stderr = result.stderr
                
                # Match standard "already locked" errors
                matches = re.findall(r"Path '(/.*?)' is already locked by user '(.*?)'", stderr)
                for path, user in matches:
                    if user != username:
                        locked_by_others.append((path, user))

                # Match W160042: Lock failed errors for "newer version exists"
                matches_alt = re.findall(r"W160042: Lock failed: newer version of '(.*?)' exists", stderr)
                must_update_files.extend(matches_alt)

        if locked_by_others or must_update_files:
            messages = []
            if locked_by_others:
                locked_msg = "\n".join(f"{file:<35} -> locked by {user}" for file, user in locked_by_others)
                messages.append(f"The following files could not be locked:\n\n{locked_msg}")

            if must_update_files:
                update_msg = "\n".join(f"{file:<35} -> must updated" for file in must_update_files)
                messages.append(f"The following files have newer versions:\n\n{update_msg}")

            error_msg = "Lock/Unlock failed:\n" + "\n".join(messages)
            print(error_msg)
            log_error(error_msg)
            raise Exception(error_msg)

        success_details = f"Action: {'Lock' if lock else 'Unlock'}\nFiles: {len(selected_files)}\nUser: {username}"
        log_success("SVN Lock Operation", success_details)
        messagebox.showinfo("Success", f"Files {'locked' if lock else 'unlocked'} successfully!")
        from busy_dialog import call_on_main_thread

        call_on_main_thread(
            lambda: update_listbox_file_info(
                patch_listbox,
                paths=selected_files,
                remove_if_not_user_locked=not lock,
            )
        )
    except Exception as e:
        error_msg = f"Failed to {'lock' if lock else 'unlock'} files.\n\n{e}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        messagebox.showerror("Error", error_msg)
    
def refresh_locked_files(files_listbox):
    """
    Refresh locked files into a treeview (synchronous).
    Prefer busy_ops.load_locked_files_busy for UI entry points.
    """
    from busy_ops import apply_locked_files_to_tree, fetch_locked_files

    config = load_config()
    svn_path = config.get("svn_path", "").replace("\\", "/")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return

    try:
        locked_files = fetch_locked_files()
        apply_locked_files_to_tree(
            files_listbox, locked_files, tags=("unchecked",)
        )
    except ET.ParseError as e:
        messagebox.showerror("Error", f"Failed to parse SVN status XML:\n{e}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load locked files:\n{e}")

def commit_files_batch(selected_files, unlock_files, batch_size=50):
    """Commit files in batches to avoid command line length limits."""
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    
    if not selected_files:
        return
        
    base_args = [
        "svn", "commit",
        "--username", username,
        "--message", f"Committed by {username}",
    ]
    
    if unlock_files == False:
        base_args.append("--no-unlock")
    
    try:
        wc_root = get_wc_root(svn_path)

        # Repair paths mojibake'd by older cp1252 svn decoding (à -> Ã )
        resolved_files = [
            resolve_wc_relative_path(wc_root, f) for f in selected_files
        ]

        for i in range(0, len(resolved_files), batch_size):
            batch = resolved_files[i:i + batch_size]
            args = base_args + batch
            result = run_svn(args, cwd=wc_root)
            if result.returncode != 0:
                raise Exception(result.stderr)
        
        success_details = f"Files: {len(selected_files)}\nUser: {username}\nUnlock after commit: {unlock_files}"
        log_success("SVN Commit", success_details)
    except Exception as e:
        error_msg = f"Failed to commit files batch: {e}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        raise Exception(error_msg)

def commit_files(selected_files, unlock_files):
    """Wrapper for backward compatibility."""
    return commit_files_batch(selected_files, unlock_files)

def get_file_info_batch(files, batch_size=50):
    """
    Get SVN info for multiple files in true multi-path batches.
    Returns a dictionary mapping file paths to (is_lock_by_user, lock_owner, revision, lock_date) tuples.
    """
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    results = {}

    if not files:
        return results

    wc_root = get_wc_root(svn_path)
    pending = set(files)
    # Map resolved (on-disk) path -> original keys so callers can look up either
    resolved_to_originals = {}
    resolved_order = []

    for file in files:
        resolved = resolve_wc_relative_path(wc_root, file)
        resolved_to_originals.setdefault(resolved, []).append(file)
        if resolved not in resolved_order:
            resolved_order.append(resolved)

    for i in range(0, len(resolved_order), batch_size):
        batch = resolved_order[i:i + batch_size]
        valid_files = []

        for file in batch:
            file_path = os.path.join(wc_root, file)
            if os.path.exists(file_path):
                valid_files.append(file)
            else:
                for original in resolved_to_originals.get(file, [file]):
                    results[original] = (False, "", "", "")
                    pending.discard(original)
                print(f"Skipping non-existent or system file: {file}")
                log_error(f"Skipping non-existent or system file: {file}")

        if not valid_files:
            continue

        try:
            args = ["svn", "info", "--xml"] + valid_files
            result = run_svn(args, cwd=wc_root)

            if result.returncode == 0 and result.stdout:
                root = ET.fromstring(result.stdout)
                for entry in root.findall(".//entry"):
                    matched = _match_info_path(entry.get("path", ""), valid_files, wc_root)
                    if matched is None:
                        continue
                    info = _parse_info_entry(entry, username)
                    for original in resolved_to_originals.get(matched, [matched]):
                        results[original] = info
                        pending.discard(original)
            else:
                print(f"Warning: Could not get batch info: {result.stderr}")
                log_error(f"Warning: Could not get batch info: {result.stderr}")
        except ET.ParseError as e:
            print(f"Warning: XML parsing error in batch info: {e}")
            log_error(f"Warning: XML parsing error in batch info: {e}")
        except Exception as e:
            print(f"Error getting batch info: {e}")
            log_error(f"Error getting batch info: {e}")

        for file in valid_files:
            for original in resolved_to_originals.get(file, [file]):
                if original not in results:
                    results[original] = (False, "", "", "")
                    pending.discard(original)

    for file in pending:
        results.setdefault(file, (False, "", "", ""))

    return results

def get_file_info(file):
    """
    Get SVN info for a single file.
    For backward compatibility, wraps get_file_info_batch.
    """
    results = get_file_info_batch([file])
    return results.get(file, (False, "", "", ""))

def get_file_revision_batch(files, batch_size=50):
    """
    Get SVN revision numbers for multiple files via multi-path svn info --xml.
    Returns a dictionary mapping file paths to revision numbers.
    """
    config = load_config()
    svn_path = config.get("svn_path")
    results = {}

    if not files:
        return results

    wc_root = get_wc_root(svn_path)
    resolved_to_originals = {}
    resolved_order = []
    for file in files:
        resolved = resolve_wc_relative_path(wc_root, file)
        resolved_to_originals.setdefault(resolved, []).append(file)
        if resolved not in resolved_order:
            resolved_order.append(resolved)

    for i in range(0, len(resolved_order), batch_size):
        batch = resolved_order[i:i + batch_size]
        valid_files = []

        for file in batch:
            file_path = os.path.join(wc_root, file)
            if os.path.exists(file_path):
                valid_files.append(file)
            else:
                for original in resolved_to_originals.get(file, [file]):
                    results[original] = ""
                print(f"Skipping non-existent or system file: {file}")
                log_error(f"Skipping non-existent or system file: {file}")

        if not valid_files:
            continue

        try:
            args = ["svn", "info", "--xml"] + valid_files
            result = run_svn(args, cwd=wc_root)
            if result.returncode == 0 and result.stdout:
                root = ET.fromstring(result.stdout)
                for entry in root.findall(".//entry"):
                    matched = _match_info_path(entry.get("path", ""), valid_files, wc_root)
                    if matched is None:
                        continue
                    _, _, revision, _ = _parse_info_entry(entry, "")
                    for original in resolved_to_originals.get(matched, [matched]):
                        results[original] = revision
            else:
                print(f"Warning: Could not get batch revisions: {result.stderr}")
                log_error(f"Warning: Could not get batch revisions: {result.stderr}")
        except Exception as e:
            print(f"Error getting batch revisions: {e}")
            log_error(f"Error getting batch revisions: {e}")

        for file in valid_files:
            for original in resolved_to_originals.get(file, [file]):
                results.setdefault(original, "")

    return results

def get_file_revision(file):
    """Wrapper for backward compatibility."""
    results = get_file_revision_batch([file])
    return results.get(file, "")

def get_file_specific_version(file_path, file_folderStruture, file_name, revision, destination):
    """
    Export a specific version of a file from SVN.
    
    Args:
        file_path: Full path to the file in the working copy
        file_folderStruture: The folder structure to maintain in the destination
        file_name: Name of the file
        revision: SVN revision number to export
        destination: Base destination directory
    """
    config = load_config()
    destination_folder = file_folderStruture.replace(file_name, "")
    destination_folder = destination + "/" + destination_folder
    if not os.path.isdir(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)  
    try:
        # Use svn export with specific revision
        args = ["svn", "export", "-r", str(revision), "--force", file_path, os.path.join(destination_folder, file_name)]
        result = run_svn(args, capture_output=True, text=True, cwd=config.get("svn_path"), shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            raise Exception(f"SVN export failed: {result.stderr}")
    except Exception as e:
        raise Exception(f"Failed to export {file_path} revision {revision} from SVN\nError might be caused by missing SVN command line tool\n\n {e}")
    
def revert_files(selected_files, batch_size=50):
    """
    Reverts the changes made to the selected files in the SVN working copy.
    """
    config = load_config()
    svn_path = config.get("svn_path")

    try:
        wc_root = get_wc_root(svn_path)
        for i in range(0, len(selected_files), batch_size):
            batch = selected_files[i:i + batch_size]
            try:
                args = ["svn", "revert"] + batch
                run_svn(
                    args,
                    capture_output=True,
                    text=True,
                    cwd=wc_root,
                    shell=False,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception as e:
                raise Exception("Failed to run SVN revert command", e)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to run SVN revert file\nError might be cause by missing SVN command line tool\n\n {e}")

def copy_InstallConfig(destination):
    # Copy InstallConfig.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        result = run_svn(
            ["svn", "info", "--show-item", "wc-root", svn_path],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        wc_root = result.stdout.strip().replace("\\", "/")
        run_svn(["svn", "export", "--force", f"{wc_root}/Tools/Misc Tools/InstallConfig/InstallConfig.exe", destination], check=True,  stdout=subprocess.DEVNULL, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to copy InstallConfig.exe from SVN: {e}")

def copy_RunScript(destination):
    # Copy RunScript.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        result = run_svn(
            ["svn", "info", "--show-item", "wc-root", svn_path],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        wc_root = result.stdout.strip().replace("\\", "/")
        run_svn(["svn", "export", "--force", f"{wc_root}/Tools/Misc Tools/InstallConfig/RunScript.bat", destination], check=True,  stdout=subprocess.DEVNULL, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        raise Exception(f"Failed to copy RunScript.exe from SVN: {e}")

def copy_UnderTestInstallConfig(destination):
    # Copy InstallConfig.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:  
        result = run_svn(
            ["svn", "info", "--show-item", "wc-root", svn_path],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        wc_root = result.stdout.strip().replace("\\", "/")
        run_svn(["svn", "export", "--force", f"{wc_root}/Tools/Test/UNDERTEST_InstallConfig.exe", destination], check=True,  stdout=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        raise Exception(f"Failed to copy UNDERTEST_InstallConfig.exe: {e}")

def get_file_head_revision_batch(files, batch_size=50):
    """
    Get SVN HEAD (last-changed) revision numbers via multi-path svn info --xml.
    Returns a dictionary mapping file paths to revision numbers.
    """
    # Same XML commit revision used by get_file_revision_batch
    return get_file_revision_batch(files, batch_size=batch_size)

def get_file_head_revision(file):
    """Get the HEAD revision for a single file."""
    results = get_file_head_revision_batch([file])
    return results.get(file, "")


def view_file_native_diff(file_path):
    """
    Open the native SVN diff tool to compare working copy with repository version.
    
    Args:
        file_path: Path to the file to compare
    """
    try:
        config = load_config()
        svn_path = config.get("svn_path")

        wc_root = run_svn(
            ["svn", "info", "--show-item", "wc-root", svn_path],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).stdout.strip().replace("\\", "/")

        full_path = os.path.join(wc_root, file_path)
        
        # Method 1: Try TortoiseSVN first (best visual diff on Windows)
        try:
            tortoise_path = "TortoiseProc.exe"
            result = run_svn(
                [tortoise_path, "/command:diff", f"/path:{full_path}"],
                capture_output=True,
                text=True,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                return  # TortoiseSVN opened successfully
        except FileNotFoundError:
            # TortoiseProc not found, continue to next method
            pass
        except Exception as e:
            print(f"TortoiseSVN error: {e}")
            log_error(f"TortoiseSVN error: {e}")
        
        # Method 2: Try using SVN diff with system-configured diff tool
        try:
            result = run_svn(
                ["svn", "diff", file_path],
                cwd=wc_root,
                shell=False
            )
            if result.returncode == 0:
                return  # SVN diff opened successfully
        except Exception as e:
            print(f"SVN diff error: {e}")
            log_error(f"SVN diff error: {e}")
            
        # Method 3: If previous methods failed, get the diff content and display in a window

        try:
            result = run_svn(
                ["svn", "diff", file_path],
                cwd=wc_root,
                capture_output=True,
                text=True,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            # If we have diff content, show it in a window
            if result.stdout:
                # Create a new window to display the diff
                import tkinter as tk
                from tkinter import scrolledtext
                
                diff_window = tk.Toplevel()
                diff_window.title(f"Diff for {file_path}")
                diff_window.geometry("800x600")
                
                diff_text = scrolledtext.ScrolledText(diff_window, wrap=tk.WORD, font=("Courier New", 10))
                diff_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
                diff_text.insert(tk.END, result.stdout)
                diff_text.config(state=tk.DISABLED)  # Make it read-only
                
                # Add a close button
                close_button = tk.Button(diff_window, text="Close", command=diff_window.destroy)
                close_button.pack(pady=10)
                
                return
            else:
                raise Exception("No differences found or failed to retrieve diff content")
                
        except Exception as e:
            raise Exception(f"Failed to show diff: {e}")
                
    except Exception as e:
        messagebox.showerror("Error", f"Failed to open diff viewer:\n{e}")

def refresh_file_status_version(files_listbox):
    """
    Refreshes only the status and version of files in the files_listbox
    without replacing the contents of the listbox.
    """
    config = load_config()
    svn_path = config.get("svn_path", "").replace("\\", "/")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return

    try:
        update_listbox_file_info(files_listbox)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to refresh file status and version:\n{e}")

def get_all_locked_files():
    """
    Gets all files locked by the current user from SVN.
    Returns a list of tuples (file_path, revision, lock_date).
    """
    config = load_config()
    svn_path = config.get("svn_path", "").replace("\\", "/")
    username = config.get("username")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return []

    try:
        wc_root = get_wc_root(svn_path)
        scope_relative = scope_relative_path(svn_path, wc_root)

        result = run_svn(
            ["svn", "status", "--xml"],
            cwd=wc_root,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            raise Exception(result.stderr)

        return _parse_user_locks_from_status_xml(
            result.stdout, username, scope_relative
        )

    except ET.ParseError as e:
        messagebox.showerror("Error", f"Failed to parse SVN status XML:\n{e}")
        return []
    except Exception as e:
        messagebox.showerror("Error", f"Failed to get locked files:\n{e}")
        return []
    
def is_svn_repo_root(path):
    try:
        result = run_svn(
            ["svn", "info", path],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        info = result.stdout
        
        for line in info.splitlines():
            if line.startswith("Relative URL:"):
                relative_url = line.split(":", 1)[1].strip()
                return relative_url == "^/"
        return False
    
    except subprocess.CalledProcessError:
        return False
    
def get_relative_path(absolute_path, wc_root=None):
    """
    Get the relative path from the SVN working copy root to the given absolute path.
    Pass wc_root to avoid an extra svn info call when already known.
    """
    try:
        if wc_root is None:
            wc_root = get_wc_root(absolute_path)
        return relative_to_wc_root(absolute_path, wc_root)
    except Exception as e:
        raise Exception(f"Failed to get relative path for '{absolute_path}': {e}")

# svn_operations.py
import subprocess
from tkinter import messagebox
from config import load_config, verify_config, log_error, log_success
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone

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

        # Process files in batches
        for i in range(0, len(selected_files), batch_size):
            batch = selected_files[i:i + batch_size]
            args = base_args + batch
            
            result = subprocess.run(
                args,
                cwd=svn_path,
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
    except Exception as e:
        error_msg = f"Failed to {'lock' if lock else 'unlock'} files.\n\n{e}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        messagebox.showerror("Error", error_msg)

    refresh_locked_files(patch_listbox)
    
def refresh_locked_files(files_listbox):
    config = load_config()
    svn_path = config.get("svn_path", "").replace("\\", "/")
    username = config.get("username")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return

    try:
        result = subprocess.run(
            ["svn", "status", "--xml", "--verbose"],
            cwd=svn_path,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            raise Exception(result.stderr)

        files_listbox.delete(*files_listbox.get_children())
        root = ET.fromstring(result.stdout)

        for entry in root.findall(".//entry"):
            path = entry.get("path", "").replace("\\", "/")
            wc_status = entry.find("wc-status")
            
            # Look for commit revision instead of wc-status revision
            commit = wc_status.find("commit") if wc_status is not None else None
            revision = commit.get("revision") if commit is not None else ""
            
            # If commit revision is not available, fall back to working copy revision
            if not revision and wc_status is not None:
                revision = wc_status.get("revision", "")

            # Check wc-status and repos-status for lock
            for status_tag in ["wc-status", "repos-status"]:
                lock = entry.find(f"{status_tag}/lock")
                if lock is not None and lock.findtext("owner") == username:
                    created_utc = lock.findtext("created", "")
                    if created_utc:
                        dt_utc = datetime.strptime(created_utc.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                        dt_local = dt_utc.astimezone()  # Convert to local time
                        lock_date = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        lock_date = ""
                    item = files_listbox.insert(
                        "", "end",
                        values=("locked", revision, path, lock_date),
                        tags=("unchecked",)
                    )
                    files_listbox.selection_add(item)  # Select the item
                    break

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
        for i in range(0, len(selected_files), batch_size):
            batch = selected_files[i:i + batch_size]
            args = base_args + batch
            result = subprocess.run(args, cwd=svn_path, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
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
    Get SVN info for multiple files in batches.
    Returns a dictionary mapping file paths to (is_lock_by_user, lock_owner, revision, lock_date) tuples.
    """
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    results = {}

    # Process files in batches
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        valid_files = []
        
        # First check which files exist in SVN
        for file in batch:
            file_path = os.path.join(svn_path, file)
            if os.path.exists(file_path):
                valid_files.append(file)
            else:
                results[file] = (False, "", "", "")
                print(f"Skipping non-existent or system file: {file}")
                log_error(f"Skipping non-existent or system file: {file}")
        
        if not valid_files:
            continue
            
        # Process one file at a time for working copy paths
        for file in valid_files:
            try:
                args = ["svn", "info", "--xml", file]
                result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    root = ET.fromstring(result.stdout)
                    entry = root.find(".//entry")
                    if entry is not None:
                        # Get the <commit> element instead of the entry revision
                        commit = entry.find(".//commit")
                        if commit is not None:
                            # Get revision from the commit element
                            revision = commit.get("revision", "")
                        else:
                            # Fall back to working copy revision if commit is not found
                            revision = entry.get("revision", "")
                        
                        lock = entry.find(".//lock")
                        if lock is not None:
                            lock_owner = lock.findtext("owner", "")
                            created_str = lock.findtext("created", "")
                            if created_str:
                                try:
                                    dt = datetime.strptime(created_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                                    lock_date = dt.strftime("%Y-%m-%d %H:%M:%S")
                                except:
                                    lock_date = ""
                            else:
                                lock_date = ""
                            
                            is_lock_by_user = lock_owner == username
                        else:
                            lock_owner = ""
                            lock_date = ""
                            is_lock_by_user = False
                        
                        results[file] = (is_lock_by_user, lock_owner, revision, lock_date)
                    else:
                        results[file] = (False, "", "", "")
                else:
                    print(f"Warning: Could not get info for {file}: {result.stderr}")
                    log_error(f"Warning: Could not get info for {file}: {result.stderr}")
                    results[file] = (False, "", "", "")
                    
            except ET.ParseError:
                print(f"Warning: XML parsing error for {file}")
                log_error(f"Warning: XML parsing error for {file}")
                results[file] = (False, "", "", "")
            except Exception as e:
                print(f"Error getting info for {file}: {e}")
                log_error(f"Error getting info for {file}: {e}")
                results[file] = (False, "", "", "")

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
    Get SVN revision numbers for multiple files in batches.
    Returns a dictionary mapping file paths to revision numbers.
    """
    config = load_config()
    svn_path = config.get("svn_path")
    results = {}
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        valid_files = []
        
        # First check which files exist in SVN
        for file in batch:
            file_path = os.path.join(svn_path, file)
            if os.path.exists(file_path):
                valid_files.append(file)
            else:
                results[file] = ""
                print(f"Skipping non-existent or system file: {file}")
                log_error(f"Skipping non-existent or system file: {file}")
        
        if not valid_files:
            continue
            
        # Process one file at a time for working copy paths
        for file in valid_files:
            try:
                args = ["svn", "info", "--show-item", "revision", file]
                result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    revision = result.stdout.strip()
                    results[file] = revision
                else:
                    print(f"Warning: Could not get revision for {file}: {result.stderr}")
                    log_error(f"Warning: Could not get revision for {file}: {result.stderr}")
                    results[file] = ""
                    
            except Exception as e:
                print(f"Error getting revision for {file}: {e}")
                log_error(f"Error getting revision for {file}: {e}")
                results[file] = ""
                
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
    destination_folder = destination + destination_folder
    if not os.path.isdir(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    try:
        # Use svn export with specific revision
        args = ["svn", "export", "-r", str(revision), "--force", file_path, os.path.join(destination_folder, file_name)]
        result = subprocess.run(args, capture_output=True, text=True, cwd=config.get("svn_path"), shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            raise Exception(f"SVN export failed: {result.stderr}")
    except Exception as e:
        raise Exception(f"Failed to export {file_path} revision {revision} from SVN\nError might be caused by missing SVN command line tool\n\n {e}")
    
def revert_files(selected_files):
    """
    Reverts the changes made to the selected files in the SVN working copy.
    """
    config = load_config()
    svn_path = config.get("svn_path")

    try:
        for file in selected_files:
            # Run the SVN revert command for each file
            try:
                args = ["svn", "revert", file]
                subprocess.run(args, capture_output=True, text=True, cwd=svn_path, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                raise Exception("Failed to run SVN revert command", e)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to run SVN revert file\nError might be cause by missing SVN command line tool\n\n {e}")

def copy_InstallConfig(destination):
    # Copy InstallConfig.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        subprocess.run(["svn", "export", "--force", f"{svn_path}/Tools/Misc Tools/InstallConfig/InstallConfig.exe", destination], check=True,  stdout=subprocess.DEVNULL, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to copy InstallConfig.exe from SVN: {e}")

def copy_RunScript(destination):
    # Copy RunScript.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        subprocess.run(["svn", "export", "--force", f"{svn_path}/Tools/Misc Tools/InstallConfig/RunScript.bat", destination], check=True,  stdout=subprocess.DEVNULL, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        raise Exception(f"Failed to copy RunScript.exe from SVN: {e}")

def copy_UnderTestInstallConfig(destination):
    # Copy InstallConfig.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        subprocess.run(["svn", "export", "--force", f"{svn_path}/Tools/Test/UNDERTEST_InstallConfig.exe", destination], check=True,  stdout=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        raise Exception(f"Failed to copy UNDERTEST_InstallConfig.exe: {e}")

def get_file_head_revision_batch(files, batch_size=50):
    """
    Get SVN HEAD revision numbers for multiple files in batches.
    Returns a dictionary mapping file paths to revision numbers.
    """
    config = load_config()
    svn_path = config.get("svn_path")
    results = {}
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        valid_files = []
        
        # First check which files exist in SVN
        for file in batch:
            file_path = os.path.join(svn_path, file)
            if os.path.exists(file_path):
                valid_files.append(file)
            else:
                results[file] = ""
                print(f"Skipping non-existent or system file: {file}")
                log_error(f"Skipping non-existent or system file: {file}")
        
        if not valid_files:
            continue
            
        # Process one file at a time for working copy paths
        for file in valid_files:
            try:
                args = ["svn", "info", "--show-item", "last-changed-revision", file]
                result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode == 0:
                    revision = result.stdout.strip()
                    results[file] = revision
                else:
                    print(f"Warning: Could not get HEAD revision for {file}: {result.stderr}")
                    log_error(f"Warning: Could not get HEAD revision for {file}: {result.stderr}")
                    results[file] = ""
                    
            except Exception as e:
                print(f"Error getting HEAD revision for {file}: {e}")
                log_error(f"Error getting HEAD revision for {file}: {e}")
                results[file] = ""
                
    return results

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
        full_path = os.path.join(svn_path, file_path)
        
        # Method 1: Try TortoiseSVN first (best visual diff on Windows)
        try:
            tortoise_path = "TortoiseProc.exe"
            result = subprocess.run(
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
            result = subprocess.run(
                ["svn", "diff", file_path],
                cwd=svn_path,
                shell=False
            )
            if result.returncode == 0:
                return  # SVN diff opened successfully
        except Exception as e:
            print(f"SVN diff error: {e}")
            log_error(f"SVN diff error: {e}")
            
        # Method 3: If previous methods failed, get the diff content and display in a window
        try:
            result = subprocess.run(
                ["svn", "diff", file_path],
                cwd=svn_path,
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
    username = config.get("username")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return

    try:
        # Get all existing files from the listbox
        file_paths = []
        for item in files_listbox.get_children():
            file_path = files_listbox.item(item, "values")[2]  # File path is at index 2
            file_paths.append(file_path)

        # Get file info in batch
        file_info_results = get_file_info_batch(file_paths)

        # Update each file in the listbox
        for item in files_listbox.get_children():
            values = files_listbox.item(item, "values")
            file_path = values[2]
            
            lock_by_user, lock_owner, revision, lock_date = file_info_results.get(file_path, (False, "", "", ""))
            
            # Update the status and version columns
            if lock_by_user:
                new_status = "locked"
                files_listbox.item(item, values=(new_status, revision, file_path, lock_date))
            elif not lock_by_user and lock_owner == "":
                new_status = "unlocked"
                files_listbox.item(item, values=(new_status, revision, file_path, lock_date))
            else:
                new_status = f"@locked - {lock_owner}"
                files_listbox.item(item, values=(new_status, revision, file_path, lock_date))

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
        result = subprocess.run(
            ["svn", "status", "--xml", "--verbose"],
            cwd=svn_path,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if result.returncode != 0:
            raise Exception(result.stderr)

        locked_files = []
        root = ET.fromstring(result.stdout)

        for entry in root.findall(".//entry"):
            path = entry.get("path", "").replace("\\", "/")
            wc_status = entry.find("wc-status")
            
            # Look for commit revision instead of wc-status revision
            commit = wc_status.find("commit") if wc_status is not None else None
            revision = commit.get("revision") if commit is not None else ""
            
            # If commit revision is not available, fall back to working copy revision
            if not revision and wc_status is not None:
                revision = wc_status.get("revision", "")

            # Check wc-status and repos-status for lock
            for status_tag in ["wc-status", "repos-status"]:
                lock = entry.find(f"{status_tag}/lock")
                if lock is not None and lock.findtext("owner") == username:
                    created_utc = lock.findtext("created", "")
                    if created_utc:
                        dt_utc = datetime.strptime(created_utc.split(".")[0], "%Y-%m-%dT%H:%M:%S")
                        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
                        dt_local = dt_utc.astimezone()  # Convert to local time
                        lock_date = dt_local.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        lock_date = ""
                    locked_files.append((path, revision, lock_date))
                    break

        return locked_files

    except ET.ParseError as e:
        messagebox.showerror("Error", f"Failed to parse SVN status XML:\n{e}")
        return []
    except Exception as e:
        messagebox.showerror("Error", f"Failed to get locked files:\n{e}")
        return []
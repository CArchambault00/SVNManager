# svn_operations.py
import subprocess
from tkinter import messagebox
from config import load_config, verify_config
import xml.etree.ElementTree as ET
import os
import re
from datetime import datetime, timezone

def lock_files(selected_files, patch_listbox):
    _lock_unlock_files(selected_files, patch_listbox, lock=True)

def unlock_files(selected_files, patch_listbox):
    _lock_unlock_files(selected_files, patch_listbox, lock=False)

def _lock_unlock_files(selected_files, patch_listbox, lock=True):
    try:
        verify_config()
        config = load_config()
        username = config.get("username")
        svn_path = config.get("svn_path")

        if not selected_files:
            messagebox.showerror("Error", "No files selected to lock/unlock!")
            return

        command = "lock" if lock else "unlock"
        base_command = ["svn", command]

        if lock:
            lock_message = f"Locking by {username}"
            base_command += ["--message", lock_message]

        base_command += selected_files

        result = subprocess.run(
            base_command,
            cwd=svn_path,
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        if result.returncode != 0:
            stderr = result.stderr
            locked_by_others = []
            must_update_files = []

            # Match standard "already locked" errors
            matches = re.findall(r"Path '(/.*?)' is already locked by user '(.*?)'", stderr)
            for path, user in matches:
                if user != username:
                    locked_by_others.append((path, user))

            # Match W160042: Lock failed errors for "newer version exists"
            matches_alt = re.findall(r"W160042: Lock failed: newer version of '(.*?)' exists", stderr)
            for path in matches_alt:
                must_update_files.append(path.strip())

            messages = []

            if locked_by_others:
                locked_msg = "\n".join(f"{file:<35} -> locked by {user}" for file, user in locked_by_others)
                messages.append(f"The following files could not be locked:\n\n{locked_msg}")

            if must_update_files:
                update_msg = "\n".join(f"{file:<35} -> must updated" for file in must_update_files)
                messages.append(f"The following files have newer versions:\n\n{update_msg}")

            if messages:
                raise Exception("Lock/Unlock failed:\n" + "\n".join(messages))
            else:
                raise Exception("Lock/Unlock failed:\n" + "\n".join(stderr.splitlines()))
        else:
            messagebox.showinfo("Success", f"Files {'locked' if lock else 'unlocked'} successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to {'lock' if lock else 'unlock'} files.\n\n{e}")

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
            revision = wc_status.get("revision") if wc_status is not None else ""

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
                    files_listbox.insert(
                        "", "end",
                        values=("locked", revision, path, lock_date),
                        tags=("unchecked",)
                    )
                    break

    except ET.ParseError as e:
        messagebox.showerror("Error", f"Failed to parse SVN status XML:\n{e}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load locked files:\n{e}")

def commit_files(selected_files, unlock_files):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    print(unlock_files)
    if selected_files:
        args = [
            "svn", "commit",
            "--username", username,
            "--message", f"Committed by {username}",
        ]

        # Add unlock flag based on condition
        if unlock_files == False:
            args.append("--no-unlock")

        # Add the files to commit
        args.extend(selected_files)
        print(args)
        try:
            subprocess.run(args, cwd=svn_path, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            raise Exception(f"Failed to commit files\nError might be cause by missing SVN command line tool\n\n {e}")

def get_file_info(file):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")

    file_on_svn = "svn://10.31.10.249/" + file

    args = ["svn", "info", file_on_svn]
    try:
        result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        # Extract revision  
        revision = ""
        if "Revision: " in result.stdout:
            try:
                revision = result.stdout.split("Revision: ")[1].split("\n")[0].strip()
            except IndexError:
                revision = ""

        # Extract lock owner
        lock_owner = ""
        if "Lock Owner: " in result.stdout:
            try:
                lock_owner = result.stdout.split("Lock Owner: ")[1].split("\n")[0].strip()
            except IndexError:
                lock_owner = ""
        lock_date = ""
        if "Lock Created: " in result.stdout:
            try:
                created_str = result.stdout.split("Lock Created: ")[1].split("\n")[0].strip()
                trimmed = created_str.split(" ")[0] + " " + created_str.split(" ")[1]
                dt = datetime.strptime(trimmed, "%Y-%m-%d %H:%M:%S")
                lock_date = dt.strftime("%Y-%m-%d %H:%M:%S")
            except IndexError:
                lock_date = ""

        # Determine if the lock is by the current user
        is_lock_by_user = lock_owner == username

        # Always return a tuple (is_lock_by_user, lock_owner, revision)
        return (is_lock_by_user, lock_owner, revision, lock_date)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to get {file} info from SVN\nError might be cause by missing SVN command line tool\n\n {e}")
        return (False, "", "")

def get_file_revision(file):
    config = load_config()
    svn_path = config.get("svn_path")
    
    # Run the SVN log command to get the latest revision number
    try:
        args = ["svn", "log", "-l", "1", file]
        result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        log_output = result.stdout
        revision_line = log_output.splitlines()[1]  # The second line contains the revision info
        revision_number = revision_line.split()[0].strip('r')
        return revision_number
    except Exception as e:
        raise Exception(f"Failed to get file revision! For file: {file}\nError might be cause by missing SVN command line tool\n\n {e}")
    

def get_file_specific_version(file_path, file_folderStruture,file_name,  revision, destination):
    config = load_config()
    destination_folder = file_folderStruture.replace(file_name, "")
    destination_folder = destination + destination_folder
    if not os.path.isdir(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)
    try:
        args = ["svn", "export", f"-r{revision}", file_path, destination_folder]
        subprocess.run(args, capture_output=True, text=True, cwd=config.get("svn_path"), shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        raise Exception(f"Failed to export {file_path} from SVN\nError might be cause by missing SVN command line tool\n\n {e}")
    
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
    # Copy RunScript.exe from the remote SVN Tools/Misc Tools/RunScript folder to the local destination
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
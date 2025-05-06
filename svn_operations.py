# svn_operations.py
import subprocess
from tkinter import messagebox
from config import load_config, verify_config
import xml.etree.ElementTree as ET
import os
import re

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

        # Decide SVN command and lock message
        if lock:
            command = "lock"
            lock_message = f"Locking by {username}"
        else:
            command = "unlock"

        # Prepare the command
        base_command = ["svn", command]

        if lock:
            base_command += ["--message", lock_message]

        # Add all files
        base_command += selected_files

        # Run the svn lock/unlock command
        result = subprocess.run(base_command, cwd=svn_path, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode != 0:
            stderr = result.stderr

            # Look for already locked warnings
            locked_info = re.findall(
                r"Path '(.*?)' is already locked by user '(.*?)'", stderr
            )

            locked_by_others = [
                (file, user) for file, user in locked_info if user != username
            ]

            if locked_by_others:
                locked_files_msg = "\n".join(
                        f"{file} → locked by {user}" for file, user in locked_by_others
                    )
                raise Exception(f"Some files are already locked by another user:\n\n{locked_files_msg}")
        messagebox.showinfo("Success", f"Files {'locked' if lock else 'unlocked'} successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to locked files\nError might be cause by missing SVN command line tool\n\n {e}")

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
                    files_listbox.insert("", "end", values=("locked", revision, path), tags=("unchecked",))
                    break

    except ET.ParseError as e:
        messagebox.showerror("Error", f"Failed to parse SVN status XML:\n{e}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load locked files:\n{e}")


def commit_files(selected_files):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    if selected_files:
        args = [
            "svn", "commit",
            "--username", username,
            "--message", f"Committed by {username}",
            "--no-unlock",
            *selected_files
        ]
        try:
            subprocess.run(args, cwd=svn_path, capture_output=True, text=True, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception as e:
            raise Exception(f"Failed to commit files\nError might be cause by missing SVN command line tool\n\n {e}")

def get_file_info(file):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")

    args = ["svn", "info", file]
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

        # Determine if the lock is by the current user
        is_lock_by_user = lock_owner == username

        # Always return a tuple (is_lock_by_user, lock_owner, revision)
        return (is_lock_by_user, lock_owner, revision)
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
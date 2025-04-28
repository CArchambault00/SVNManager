# svn_operations.py
import subprocess
from tkinter import messagebox
from config import load_config
import xml.etree.ElementTree as ET
import os

def load_user_locked_files():
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return []

    # Run the SVN command to get the XML status output
    command = f'svn status --xml {svn_path}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
   
    if result.returncode != 0:
        messagebox.showerror("Error", "Failed to get SVN status!")
        return []

    locked_files = []
    try:
        root = ET.fromstring(result.stdout)

        # Iterate through all <entry> elements in the XML
        for entry in root.findall(".//entry"):
            # Get the file path from the 'path' attribute of the <entry> element
            file_path = entry.get("path")

            file_path = file_path.replace("\\", "/")

            # Check for <lock> in <wc-status>
            wc_status = entry.find("wc-status")
            if wc_status is not None:
                lock = wc_status.find("lock")
                if lock is not None:
                    lock_owner = lock.find("owner").text
                    if lock_owner == username:
                        locked_files.append(file_path)
                        continue  # Skip checking <repos-status> if already found in <wc-status>

            # Check for <lock> in <repos-status>
            repos_status = entry.find("repos-status")
            if repos_status is not None:
                lock = repos_status.find("lock")
                if lock is not None:
                    lock_owner = lock.find("owner").text
                    if lock_owner == username:
                        locked_files.append(file_path)

    except ET.ParseError as e:
        messagebox.showerror("Error", f"Failed to parse SVN status XML: {e}")
        return []

    return locked_files


def lock_files(selected_files, patch_listbox):
    _lock_unlock_files(selected_files, patch_listbox, lock=True)

def unlock_files(selected_files, patch_listbox):
    _lock_unlock_files(selected_files, patch_listbox, lock=False)

def _lock_unlock_files(selected_files, patch_listbox, lock=True):
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
    result = subprocess.run(base_command, cwd=svn_path, capture_output=True, text=True)

    if result.returncode == 0:
        messagebox.showinfo("Success", f"Files {'locked' if lock else 'unlocked'} successfully!")
    else:
        messagebox.showerror("SVN Error", result.stderr)

    refresh_locked_files(patch_listbox)

def refresh_locked_files(files_listbox):
    config = load_config()
    svn_path = config.get("svn_path")
    if svn_path:
        svn_path = svn_path.replace("\\", "/")
        files_listbox.delete(*files_listbox.get_children())
        for file in load_user_locked_files():
            file_name = file.split(svn_path + "/")[1]
            lock_by_user, lock_owner, revision = get_file_info(file)
            files_listbox.insert("", "end", values=("locked",revision, file_name), tags=("unchecked",))

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

        result = subprocess.run(args, cwd=svn_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"SVN commit failed: {result.stderr}")

def get_file_info(file):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")

    args = ["svn", "info", file]
    result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path)

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

def get_file_revision(file):
    config = load_config()
    svn_path = config.get("svn_path")
    
    # Run the SVN log command to get the latest revision number
    args = ["svn", "log", "-l", "1", file]
    result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path)
    
    # Check if the command was successful
    if result.returncode == 0:
        # Extract the revision number from the output
        log_output = result.stdout
        revision_line = log_output.splitlines()[1]  # The second line contains the revision info
        revision_number = revision_line.split()[0].strip('r')
        return revision_number
    else:
        messagebox.showerror("Error", "Failed to get file revision! For file: " + file)

def get_file_specific_version(file_path, file_folderStruture,file_name,  revision, destination):
    config = load_config()
    destination_folder = file_folderStruture.replace(file_name, "")
    destination_folder = destination + destination_folder
    if not os.path.isdir(destination_folder):
        os.makedirs(destination_folder, exist_ok=True)

    args = ["svn", "export", f"-r{revision}", file_path, destination_folder]
    result = subprocess.run(args, capture_output=True, text=True, cwd=config.get("svn_path"))
    
def revert_files(selected_files):
    """
    Reverts the changes made to the selected files in the SVN working copy.
    """
    config = load_config()
    svn_path = config.get("svn_path")

    if not selected_files:
        messagebox.showerror("Error", "No files selected for revert!")
        return

    try:
        for file in selected_files:
            # Run the SVN revert command for each file
            args = ["svn", "revert", file]
            result = subprocess.run(args, capture_output=True, text=True, cwd=svn_path)

            if result.returncode != 0:
                messagebox.showerror("Error", f"Failed to revert file: {file}\n{result.stderr}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while reverting files: {e}")

def copy_InstallConfig(destination):
    # Copy InstallConfig.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        subprocess.run(["svn", "export", "--force", f"{svn_path}/Tools/Misc Tools/InstallConfig/InstallConfig.exe", destination], check=True,  stdout=subprocess.DEVNULL,)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to copy InstallConfig.exe: {e}")

def copy_RunScript(destination):
    # Copy RunScript.exe from the remote SVN Tools/Misc Tools/RunScript folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        subprocess.run(["svn", "export", "--force", f"{svn_path}/Tools/Misc Tools/InstallConfig/RunScript.bat", destination], check=True,  stdout=subprocess.DEVNULL,)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to copy RunScript.exe: {e}")

def copy_UnderTestInstallConfig(destination):
    # Copy InstallConfig.exe from the remote SVN Tools/Misc Tools/InstallConfig folder to the local destination
    config = load_config()
    svn_path = config.get("svn_path")
    try:
        subprocess.run(["svn", "export", "--force", f"{svn_path}/Tools/Test/UNDERTEST_InstallConfig.exe", destination], check=True,  stdout=subprocess.DEVNULL,)
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error", f"Failed to copy InstallConfig.exe: {e}")
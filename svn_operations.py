# svn_operations.py
import subprocess
import tkinter as tk
from tkinter import messagebox
from config import load_config
import os

TORTOISE_SVN = r"C:\Program Files\TortoiseSVN\bin\TortoiseProc.exe"


def load_locked_files():
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")

    if not os.path.isdir(svn_path):
        messagebox.showwarning("Warning", "Invalid SVN path!")
        return []

    # Run the SVN command to get the XML status output
    command = f'svn status --xml -u {svn_path}'
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
   
    if result.returncode != 0:
        messagebox.showerror("Error", "Failed to get SVN status!")
        return []

    locked_files = []

    # Parse through the SVN status XML output
    entries = result.stdout.split("<entry")  # Split by <entry> to handle each entry individually

    for entry in entries:
        if f"<owner>{username}</owner>" in entry and "<lock>" in entry:
            # Extract the file path from the entry's <path> attribute
            start = entry.find('path="') + len('path="')
            end = entry.find('"', start)
            file_path = entry[start:end]
            file_path = file_path.replace("\\", "/")
            # Add the file path to the locked_files list
            locked_files.append(file_path)
    return locked_files


def lock_files(selected_files, patch_listbox, patch_listbox_patch):
    _lock_unlock_files(selected_files, patch_listbox, patch_listbox_patch, lock=True)

def unlock_files(selected_files, patch_listbox, patch_listbox_patch):
    _lock_unlock_files(selected_files, patch_listbox, patch_listbox_patch, lock=False)

def _lock_unlock_files(selected_files, patch_listbox, patch_listbox_patch, lock=True):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    command = "lock" if lock else "unlock"
    
    # Ensure lock message is properly formatted
    lock_message = f"Locking by {username}" if lock else f"Unlocking by {username}"
    
    # Ensure selected files are correctly formatted in the command
    files_str = '*'.join(selected_files)
    
    # Prepare the command arguments
    args = [
        TORTOISE_SVN, f"/command:{command}",
        f"/path:{files_str}", "/closeonend:1", f"/lockmessage:{lock_message}"
    ]
    
    # Run the subprocess command
    subprocess.run(args, cwd=svn_path, shell=True)

    # Update the list of locked files
    locked_files = load_locked_files()
    if lock:
        locked_files.extend(selected_files)
    else:
        locked_files = [file for file in locked_files if file not in selected_files]
    
    refresh_locked_files(patch_listbox)
    refresh_locked_files(patch_listbox_patch)

def refresh_locked_files(files_listbox):
    config = load_config()
    svn_path = config.get("svn_path")
    if svn_path:
        svn_path = svn_path.replace("\\", "/")
        files_listbox.delete(*files_listbox.get_children())
        for file in load_locked_files():
            file_name = file.split(svn_path + "/")[1]
            files_listbox.insert("", "end", values=("locked", file_name), tags=("unchecked",))

def commit_files(selected_files):
    config = load_config()
    username = config.get("username")
    svn_path = config.get("svn_path")
    if selected_files:
        args = [TORTOISE_SVN, "/command:commit", f"/path:{'*'.join(selected_files)}", "/closeonend:1", f"/logmsg:{username}"]
        subprocess.run(args, shell=True, cwd=svn_path)
    else: 
        messagebox.showerror("Error", "No files selected for commit!")

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
    
    
    
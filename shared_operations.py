import os
import subprocess
from config import load_config
from tkinter import messagebox

LOCKED_FILES_FILE = "locked_files.json"

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

            # Add the file path to the locked_files list
            locked_files.append(file_path)
    return locked_files


from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from config import load_config, save_config
import subprocess
import os

def select_svn_folder(button):
    folder = filedialog.askdirectory(title="Select SVN Folder")
    # Verify that the selected folder is a valid SVN folder
    if folder:
        args = ["svn", "info", folder]
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            config = load_config()
            config["svn_path"] = folder
            save_config(config)
            button.config(background="SystemButtonFace")
        else:
            messagebox.showerror("Error", "The selected folder is not a valid SVN folder")

def select_instant_client_folder(button):
    folder = filedialog.askdirectory(title="Select INSTANT_CLIENT Folder")
    if folder:
        required_files = ["oci.dll"]  # Add other required files if necessary
        if all(os.path.exists(os.path.join(folder, file)) for file in required_files):
            config = load_config()
            config["instant_client"] = folder
            save_config(config)
            button.config(background="SystemButtonFace")
        else:
            messagebox.showerror("Error", "The selected folder is not a valid Instant Client 12.1.0 folder")


def set_username(username_entry):
    username = username_entry.get()
    if username:
        config = load_config()
        config["username"] = username
        save_config(config)
        username_entry.config(highlightthickness=0)
        messagebox.showinfo("Info", "Username saved!")
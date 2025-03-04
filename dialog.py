
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
import config

def select_svn_folder():
    folder = filedialog.askdirectory(title="Select SVN Folder")
    if folder:
        with open(".env", "a") as env_file:
            env_file.write(f"SVN_PATH={folder}\n")

def set_username(username_entry):
    username = username_entry.get()
    if username:
        with open(".env", "a") as env_file:
            env_file.write(f"USERNAME={username}\n")

def refresh_username(username_entry):
    username = config.get_env_var("USERNAME")
    print(username)
    if username:
        username_entry.insert(0, username)  # Insert the username if it exists
    else:
        messagebox.showwarning("Warning", "Please set the username!")  # Show a warning if the username is not set
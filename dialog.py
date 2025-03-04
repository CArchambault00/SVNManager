
from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from config import load_config, save_config

def select_svn_folder():
    folder = filedialog.askdirectory(title="Select SVN Folder")
    if folder:
        config = load_config()
        config["svn_path"] = folder
        save_config(config)

def set_username(username_entry):
    username = username_entry.get()
    if username:
        config = load_config()
        config["username"] = username
        save_config(config)
        messagebox.showinfo("Info", "Username saved!")

def refresh_username(username_entry):
    config = load_config()
    username = config.get("username")
    if username:
        username_entry.insert(0, username)  # Insert the username if it exists
    else:
        messagebox.showwarning("Warning", "Please set the username!")  # Show a warning if the username is not set

from tkinter import filedialog, messagebox, ttk
import tkinter as tk
from config import load_config, save_config

def select_svn_folder(button):
    folder = filedialog.askdirectory(title="Select SVN Folder")
    if folder:
        config = load_config()
        config["svn_path"] = folder
        save_config(config)
        button.config(background="SystemButtonFace")

def select_instant_client_folder(button):
    folder = filedialog.askdirectory(title="Select INSTANT_CLIENT Folder")
    if folder:
        config = load_config()
        config["instant_client"] = folder
        save_config(config)
        button.config(background="SystemButtonFace")


def set_username(username_entry):
    username = username_entry.get()
    if username:
        config = load_config()
        config["username"] = username
        save_config(config)
        username_entry.config(highlightthickness=0)
        messagebox.showinfo("Info", "Username saved!")
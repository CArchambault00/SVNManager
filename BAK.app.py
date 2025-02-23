import os
import subprocess
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import shutil

CONFIG_FILE = "svn_config.json"
LOCKED_FILES_FILE = "locked_files.json"
TORTOISE_SVN = r"C:\Program Files\TortoiseSVN\bin\TortoiseProc.exe"
PATCH_DIR = "D:/cyframe/jtdev/Patches/Current"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"svn_path": "", "username": ""}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

def load_locked_files():
    if os.path.exists(LOCKED_FILES_FILE):
        with open(LOCKED_FILES_FILE, "r") as f:
            return json.load(f)
    return []

def save_locked_files(data):
    with open(LOCKED_FILES_FILE, "w") as f:
        json.dump(data, f)

def select_svn_folder():
    folder = filedialog.askdirectory(title="Select SVN Folder")
    if folder:
        config = load_config()
        config["svn_path"] = folder
        save_config(config)
        #refresh_file_list()

def set_username():
    username = username_entry.get()
    if username:
        config = load_config()
        config["username"] = username
        save_config(config)
        messagebox.showinfo("Info", "Username saved!")

def add_files(event):
    files = root.tk.splitlist(event.data)
    for file in files:
        patch_listbox.insert("", "end", values=(file,))

def lock_unlock_files(lock=True):
    selected = [patch_listbox.item(item, "values")[0] for item in patch_listbox.selection()]
    if not selected:
        messagebox.showwarning("Warning", "No files selected!")
        return
    config = load_config()
    username = config.get("username", "")
    command = "lock" if lock else "unlock"
    args = [TORTOISE_SVN, f"/command:{command}", f"/path:{'*'.join(selected)}", "/closeonend:1", f"/lockmessage:{username}"]
    subprocess.run(args, shell=True)
    
    locked_files = load_locked_files()
    if lock:
        locked_files.extend(selected)
    else:
        locked_files = [file for file in locked_files if file not in selected]
    save_locked_files(list(set(locked_files)))  # Remove duplicates
    #refresh_file_list()

def generate_patch():
    os.makedirs(PATCH_DIR, exist_ok=True)
    selected = [patch_listbox.item(item, "values")[0] for item in patch_listbox.get_children()]
    if not selected:
        messagebox.showwarning("Warning", "No files selected for patch!")
        return
    for file in selected:
        dest_path = os.path.join(PATCH_DIR, os.path.relpath(file, load_config()["svn_path"]))
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy(file, dest_path)
    messagebox.showinfo("Success", "Patch generated successfully!")
    
def switch_menu(menu):
    if menu == "Lock":
        lock_frame.pack(fill="both", expand=True)
        patch_frame.pack_forget()
        refresh_locked_files()  # Refresh the list when switching to Lock/Unlock
    else:
        patch_frame.pack(fill="both", expand=True)
        lock_frame.pack_forget()

def refresh_locked_files():
    patch_listbox.delete(*patch_listbox.get_children())
    locked_files = load_locked_files()
    for file in locked_files:
        patch_listbox.insert("", "end", values=(file,))
    
    config = load_config()
    if not config["username"]:
        messagebox.showwarning("Warning", "Please set the username!")
    else:
        username_entry.insert(0, config["username"])

root = TkinterDnD.Tk()
root.title("SVN Manager")
root.geometry("700x500")

menu_frame = tk.Frame(root)
menu_frame.pack(fill="x")
tk.Button(menu_frame, text="Lock/Unlock", command=lambda: switch_menu("Lock")).pack(side="left", padx=5, pady=5)
tk.Button(menu_frame, text="Patch", command=lambda: switch_menu("Patch")).pack(side="left", padx=5, pady=5)
tk.Button(menu_frame, text="Select SVN Folder", command=select_svn_folder).pack(side="right", padx=5, pady=5)

username_frame = tk.Frame(root)
tk.Label(username_frame, text="Username:").pack(side="left", padx=5, pady=5)
username_entry = tk.Entry(username_frame)
username_entry.pack(side="left", padx=5, pady=5)
tk.Button(username_frame, text="Save", command=set_username).pack(side="left", padx=5, pady=5)
username_frame.pack(fill="x")

lock_frame = tk.Frame(root)
patch_listbox = ttk.Treeview(lock_frame, columns=("File Path",), show="headings")
patch_listbox.heading("File Path", text="File Path")
patch_listbox.pack(side="left", fill="both", expand=True)

scrollbar = tk.Scrollbar(lock_frame, orient="vertical", command=patch_listbox.yview)
patch_listbox.configure(yscroll=scrollbar.set)
scrollbar.pack(side="right", fill="y")

tk.Button(lock_frame, text="Lock Selected", command=lambda: lock_unlock_files(True)).pack(side="left", padx=5, pady=5)
tk.Button(lock_frame, text="Unlock Selected", command=lambda: lock_unlock_files(False)).pack(side="left", padx=5, pady=5)
lock_frame.pack(fill="both", expand=True)

patch_frame = tk.Frame(root)
patch_listbox.drop_target_register(DND_FILES)
patch_listbox.dnd_bind('<<Drop>>', add_files)
tk.Button(patch_frame, text="Select Files", command=lambda: add_files({"data": filedialog.askopenfilenames()})).pack(pady=5)
tk.Button(patch_frame, text="Generate Patch", command=generate_patch).pack(pady=5)
patch_frame.pack_forget()

refresh_locked_files()
root.mainloop()
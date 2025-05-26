import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
from svn_operations import refresh_locked_files
from patches_operations import refresh_patches, refresh_patch_files
from create_component import create_patches_treeview, create_file_listbox, create_top_frame
from create_buttons import create_button_frame, create_button_frame_patch, create_button_frame_modify_patch, create_button_frame_patches
from config import load_config, get_unset_var
from native_topbar import initialize_native_topbar
import urllib.request
import random
import sys
import os
import webbrowser

APP_VERSION = "1.0.18"

def create_main_layout(root):
    root.grid_rowconfigure(1, weight=1)

    # Ratio 2:1 (left: 2/3, right: 1/3)
    root.grid_columnconfigure(0, weight=2)  # Bottom left frame
    root.grid_columnconfigure(1, weight=1)  # Bottom right frame

    top_frame = tk.Frame(root, height=80, relief=tk.RIDGE, borderwidth=2)
    top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    bottom_left_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_left_frame.grid(row=1, column=0, sticky="nsew")

    bottom_right_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_right_frame.grid(row=1, column=1, sticky="nsew")

    # Empêcher bottom_left_frame de dépasser 2/3 de la largeur
    def enforce_ratio(event=None):
        total_width = root.winfo_width()
        max_left_width = int(total_width * (2 / 3))
        bottom_left_frame.config(width=max_left_width)
        bottom_left_frame.update_idletasks()

    root.bind("<Configure>", enforce_ratio)

    return top_frame, bottom_left_frame, bottom_right_frame


def check_requirements():
    config = load_config()
    messages = []
    
    if not config.get("username"):
        messages.append("Please set your username in the Config menu")
    if not config.get("active_profile"):
        messages.append("Please select or create a profile in the Profile menu")
        
    if messages:
        messagebox.showwarning("Setup Required", "\n".join(messages))
        return False
    return True

def switch_to_lock_unlock_menu():
    if not check_requirements():
        return
        
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "lock_unlock")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame(bottom_right_frame, files_listbox)
    refresh_locked_files(files_listbox)

def switch_to_patch_menu():
    if not check_requirements():
        return
        
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "patch")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame_patch(bottom_right_frame, files_listbox)
    refresh_locked_files(files_listbox)

def switch_to_patches_menu():
    if not check_requirements():
        return
        
    config = load_config()
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu,  "patches")
    
    # Create a Treeview to display patches
    patches_listbox = create_patches_treeview(bottom_left_frame)
    create_button_frame_patches(bottom_right_frame, patches_listbox, switch_to_modify_patch_menu)
    username = config.get("username")
    refresh_patches(patches_listbox, False, "S", username)  # Populate the Treeview with patches

def switch_to_modify_patch_menu(patch_details):
    if not check_requirements():
        return
        
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "modify_patch")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame_modify_patch(bottom_right_frame, files_listbox, patch_details,switch_to_modify_patch_menu)
    refresh_patch_files(files_listbox, patch_details)

def check_latest_version(root):
    random_number = random.randint(1, 1000000)
    url = f"https://raw.githubusercontent.com/CArchambault00/SVNManager/main/latest_version.txt?nocache={random_number}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "User-Agent": "SVNManager"
            }
        )

        with urllib.request.urlopen(req) as response:
            latest_version = response.read().decode("utf-8").strip()

        if latest_version != APP_VERSION:
            if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available.\nDo you want to open the download page?"):
                release_url = f"https://github.com/CArchambault00/SVNManager/releases/tag/{latest_version}"
                webbrowser.open(release_url)
            sys.exit(0)

    except Exception as e:
        print(f"Failed to check for latest version: {e}")
        messagebox.showerror("Error", f"Failed to check for latest version:\n{e}")

def setup_gui():
    global root
    root = TkinterDnD.Tk()  # Initialize TkinterDnD root window 
    if getattr(sys, 'frozen', False):  # Running as a PyInstaller bundle
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.abspath(".")

    icon_path = os.path.join(bundle_dir, "SVNManagerIcon.ico")
        
    root.iconbitmap(icon_path)
    root.title("SVN Manager")
    root.geometry("900x600")

    #Add to check for the latest version
    check_latest_version(root)

    initialize_native_topbar(root)
    
    # Check configuration before switching to initial menu
    config = load_config()
    if not config.get("username"):
        messagebox.showwarning("Setup Required", "Please set your username in the Config menu")
    elif not config.get("active_profile"):
        messagebox.showwarning("Setup Required", "Please select or create a profile in the Profile menu")
    else:
        switch_to_lock_unlock_menu()
    
    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()

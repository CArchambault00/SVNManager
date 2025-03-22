import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
from svn_operations import refresh_locked_files
from patches_operations import refresh_patches, refresh_patch_files
from create_component import create_patches_treeview, create_file_listbox, create_top_frame
from create_buttons import create_button_frame, create_button_frame_patch, create_button_frame_modify_patch, create_button_frame_patches
from config import load_config, get_unset_var
from native_topbar import initialize_native_topbar


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


def switch_to_lock_unlock_menu():
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "lock_unlock")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame(bottom_right_frame, files_listbox)
    refresh_locked_files(files_listbox)
    neededVar = get_unset_var()
    if neededVar:
        messagebox.showwarning("Warning", f"You must set the following variables: {neededVar}")

def switch_to_patch_menu():
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "patch")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame_patch(bottom_right_frame, files_listbox)
    refresh_locked_files(files_listbox)
    neededVar = get_unset_var()
    if neededVar:
        messagebox.showwarning("Warning", f"You must set the following variables: {neededVar}")

def switch_to_patches_menu():
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

    neededVar = get_unset_var()
    if neededVar:
        messagebox.showwarning("Warning", f"You must set the following variables: {neededVar}")

def switch_to_modify_patch_menu(patch_details):
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "modify_patch")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame_modify_patch(bottom_right_frame, files_listbox, patch_details,switch_to_modify_patch_menu)
    refresh_patch_files(files_listbox, patch_details)

    neededVar = get_unset_var()
    if neededVar:
        messagebox.showwarning("Warning", f"You must set the following variables: {neededVar}")


def setup_gui():
    global root
    root = TkinterDnD.Tk()  # Initialize TkinterDnD root window
    root.iconbitmap("SVNManagerIcon.ico")
    root.title("SVN Manager")
    root.geometry("900x600")

    initialize_native_topbar(root)

    # Switch to the initial menu
    switch_to_lock_unlock_menu()
    
    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()

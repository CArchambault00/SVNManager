import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from svn_operations import lock_files, unlock_files, refresh_locked_files
from buttons_function import lock_selected_files, unlock_selected_files
from file_operations import generate_patch
from buttons_function import insert_next_version, update_patch, modify_patch
from patches_operations import refresh_patches
from config import load_config, save_config

def create_button_frame(parent, files_listbox):
    tk.Button(parent, text="Refresh lock files", command=lambda: refresh_locked_files(files_listbox)).pack(side="top", pady=10)

    tk.Button(parent, text="Lock All", command=lambda: lock_files([files_listbox.item(item, "values")[1] for item in files_listbox.get_children()], files_listbox, files_listbox)).pack(side="top", pady=0)
    tk.Button(parent, text="Unlock All", command=lambda: unlock_files([files_listbox.item(item, "values")[1] for item in files_listbox.get_children()], files_listbox, files_listbox)).pack(side="top", pady=10)

    tk.Button(parent, text="Lock Selected", command=lambda: lock_selected_files(files_listbox)).pack(side="top", pady=5)
    tk.Button(parent, text="Unlock Selected", command=lambda: unlock_selected_files(files_listbox)).pack(side="top", pady=5)

def create_button_frame_patch(parent, files_listbox):
    ## Patch Version entry
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    patch_version_label = tk.Label(patch_version_frame, text="Patch Version:")
    patch_version_label.pack(side="left", padx=5)

    # Dropdown for patch letter
    patch_version_letter = ttk.Combobox(patch_version_frame, values=["J", "S", "V", "W"], width=3)
    patch_version_letter.set("S")  # default value
    patch_version_letter.pack(side="left", padx=5)

    patch_version_entry = tk.Entry(patch_version_frame, width=14)
    patch_version_entry.pack(side="left", padx=5)

    ## Next Version Button
    tk.Button(patch_version_frame, text="Next Version", command=lambda: insert_next_version(patch_version_letter.get(), patch_version_entry)).pack(side="left", padx=5)

    ## Add a section to write the patch description
    patch_description_frame = tk.Frame(parent)
    patch_description_frame.pack(side="top", pady=5, fill="both", expand=True)

    patch_description_label = tk.Label(patch_description_frame, text="Patch Description:")
    patch_description_label.pack(side="top", padx=5)

    patch_description_entry = tk.Text(patch_description_frame, height=10, width=40)  # Changed to Text widget
    patch_description_entry.pack(side="top", padx=5, fill="both", expand=True)

    tk.Button(parent, text="Generate Patch", command=lambda: generate_patch([files_listbox.item(item, "values")[1] for item in files_listbox.selection()], patch_version_letter.get(), patch_version_entry.get(), patch_description_entry.get("1.0", tk.END).strip())).pack(side="top", pady=5)

def create_button_frame_modify_patch(parent, files_listbox, patch_details):
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    patch_version_label = tk.Label(patch_version_frame, text="Patch Version:")
    patch_version_label.pack(side="left", padx=5)

    patch_version_letter = ttk.Combobox(patch_version_frame, values=["J", "S", "V", "W"], width=3)
    patch_letter = patch_details[0][0]  # Extract the letter from the selected patch's version
    patch_version_letter.set(patch_letter)  # Set to the selected patch's version
    patch_version_letter.pack(side="left", padx=5)

    patch_version_entry = tk.Entry(patch_version_frame, width=14)
    patch_version_entry.insert(0, patch_details[0])  # Set to the selected patch's version number
    patch_version_entry.pack(side="left", padx=5)

    tk.Button(patch_version_frame, text="Next Version", command=lambda: insert_next_version(patch_version_letter.get(), patch_version_entry)).pack(side="left", padx=5)

    patch_description_frame = tk.Frame(parent)
    patch_description_frame.pack(side="top", pady=5, fill="both", expand=True)

    patch_description_label = tk.Label(patch_description_frame, text="Patch Description:")
    patch_description_label.pack(side="top", padx=5)

    patch_description_entry = tk.Text(patch_description_frame, height=10, width=40)
    patch_description_entry.insert("1.0", patch_details[1])  # Set to the selected patch's description
    patch_description_entry.pack(side="top", padx=5, fill="both", expand=True)

    tk.Button(parent, text="Update Patch", command=lambda: update_patch([files_listbox.item(item, "values")[0] for item in files_listbox.selection()], patch_version_letter.get(), patch_version_entry.get(), patch_description_entry.get("1.0", tk.END).strip())).pack(side="top", pady=5)

def create_button_frame_patches(parent, patches_listbox, switch_to_modify_patch_menu):
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    patch_version_letter = ttk.Combobox(patch_version_frame, values=["J", "S", "V", "W"], width=3)
    patch_version_letter.set("S")  # default value
    patch_version_letter.pack(side="left", padx=5)

    # On patch version change, refresh the patches
    patch_version_letter.bind("<<ComboboxSelected>>", lambda event: refresh_patches(patches_listbox, False, patch_version_letter.get(), load_config().get("username")))

    tk.Button(parent, text="Refresh Patches", command=lambda: refresh_patches(patches_listbox, False, patch_version_letter.get(), load_config().get("username"))).pack(side="top", pady=5)

    # Add a button to modify the selected patch
    tk.Button(parent, text="Modify Patch", command=lambda: modify_patch([patches_listbox.item(item, "values") for item in patches_listbox.selection()], switch_to_modify_patch_menu)).pack(side="top", pady=5)

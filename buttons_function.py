import tkinter as tk
from tkinter import ttk
from svn_operations import lock_files, unlock_files, refresh_locked_files
from version_operation import next_version

def lock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[0] for item in files_listbox.selection()]
    lock_files(selected_files, files_listbox, files_listbox)

def unlock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[0] for item in files_listbox.selection()]
    unlock_files(selected_files, files_listbox, files_listbox)

def insert_next_version(module, patch_version_entry):
    new_version = next_version(module)
    if new_version:
        patch_version_entry.config(state="normal")
        patch_version_entry.delete(0, tk.END)
        patch_version_entry.insert(0, new_version)
        patch_version_entry.config(state="normal")

def update_patch(selected_files, patch_version_letter, patch_version_entry, patch_description):
    # Implement the logic to update the patch with the new details
    pass

def modify_patch(selected_patch, switch_to_modify_patch_menu):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        switch_to_modify_patch_menu(patch_details)
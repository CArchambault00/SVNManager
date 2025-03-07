import tkinter as tk
from tkinter import ttk
from svn_operations import lock_files, unlock_files, refresh_locked_files
from version_operation import next_version
from patches_operations import get_full_patch_info, set_selected_patch
from db_handler import dbClass
from utils import get_md5_checksum
import os
from svn_operations import get_file_revision
from config import load_config


def lock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[1] for item in files_listbox.selection()]
    lock_files(selected_files, files_listbox, files_listbox)

def unlock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[1] for item in files_listbox.selection()]
    unlock_files(selected_files, files_listbox, files_listbox)

def insert_next_version(module, patch_version_entry):
    new_version = next_version(module)
    if new_version:
        patch_version_entry.config(state="normal")
        patch_version_entry.delete(0, tk.END)
        patch_version_entry.insert(0, new_version)
        patch_version_entry.config(state="normal")

def deselect_all_files(event, files_listbox):
    if not files_listbox.identify_row(event.y):  # Check if click is on an empty area
        files_listbox.selection_remove(files_listbox.selection())


def select_all_files(event, files_listbox):
    for item in files_listbox.get_children():
        files_listbox.selection_add(item)

def handle_drop(event, listbox):
    files = listbox.tk.splitlist(event.data)
    for file in files:
        listbox.insert('', 'end', values=('unlocked', file))

def update_patch(selected_files, patch_id, patch_version_letter, patch_version_entry, patch_description):
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    db.update_patch_header(patch_id, patch_version_letter, patch_version_entry, patch_description)
    db.delete_patch_detail(patch_id)
    for file in selected_files:
        file_folder = os.path.dirname(file)
        if file.startswith("webpage"):
            file_fullname = file.replace("webpage\\", "")
            file_folder = file_folder.replace("webpage\\", "")
        elif file.startswith("Database"):
            file_fullname = file.replace("Database\\", "")
            file_folder = file_folder.replace("Database\\", "")
        file_fullname = file_fullname.upper()
        file_id = db.create_patch_detail(patch_id, file_folder, file_fullname, get_file_revision(file))
        
        md5checksum = get_md5_checksum(svn_path + "/" + file)
        db.set_md5(patch_id, file_id, md5checksum)

def modify_patch(selected_patch, switch_to_modify_patch_menu):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        full_patch_info = get_full_patch_info(patch_details[0])
        set_selected_patch(full_patch_info)
        switch_to_modify_patch_menu(full_patch_info)
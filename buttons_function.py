import tkinter as tk
from tkinter import ttk
from svn_operations import lock_files, unlock_files, refresh_locked_files
from version_operation import next_version
from patches_operations import get_full_patch_info, set_selected_patch, build_patch
from db_handler import dbClass
from utils import get_md5_checksum
import os
from svn_operations import get_file_revision, commit_files
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
    config = load_config()
    svn_path = config.get("svn_path")
    files_outside_svn = []
    for file in files:
        if os.path.isfile(file):
            if file.startswith(svn_path):
                file = file.replace("\\", "/")
                file = file.replace(svn_path + "/", "")
                listbox.insert('', 'end', values=('unlocked', file))
            else:
                files_outside_svn.append(file)
        if os.path.isdir(file):
            for root, dirs, files in os.walk(file):
                for file in files:
                    file = os.path.join(root, file)
                    if file.startswith(svn_path):
                        file = file.replace("\\", "/")
                        file = file.replace(svn_path + "/", "")
                        listbox.insert('', 'end', values=('unlocked', file))
                    else:
                        files_outside_svn.append(file)
    if files_outside_svn:
        tk.messagebox.showerror("Error", "The following files are not in the SVN repository and will not be added to the patch: \n" + "\n".join(files_outside_svn))
        

def update_patch(selected_files, patch_id, patch_version_letter, patch_version_entry, patch_description):
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    commit_files(selected_files)
    db.update_patch_header(patch_id, patch_version_letter, patch_version_entry, patch_description)
    db.delete_patch_detail(patch_id)
    for file in selected_files:
        fake_path = '$/Projects/SVN/' + file
        filename = os.path.basename(file)
        file_id = db.create_patch_detail(patch_id, fake_path, filename, get_file_revision(file))
        
        md5checksum = get_md5_checksum(svn_path + "/" + file)
        db.set_md5(patch_id, file_id, md5checksum)

def modify_patch(selected_patch, switch_to_modify_patch_menu):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        full_patch_info = get_full_patch_info(patch_details[0])
        set_selected_patch(full_patch_info)
        switch_to_modify_patch_menu(full_patch_info)

def build_existing_patch(selected_patch):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        full_patch_info = get_full_patch_info(patch_details[0])
        build_patch(full_patch_info)
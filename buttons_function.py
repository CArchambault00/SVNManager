import tkinter as tk
from svn_operations import lock_files, unlock_files
from version_operation import next_version
from patches_operations import get_full_patch_info, set_selected_patch, build_patch
import os
from svn_operations import get_file_info
from config import load_config

PATCH_DIR = "D:/cyframe/jtdev/Patches/Current"

def lock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[2] for item in files_listbox.selection()]
    lock_files(selected_files, files_listbox)

def unlock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[2] for item in files_listbox.selection()]
    unlock_files(selected_files, files_listbox)

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

def check_files_is_present(files_listbox, files):
    for file in files:
        for item in files_listbox.get_children():
            if files_listbox.item(item, "values")[2] == file:
                return True

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
                if not check_files_is_present(listbox, [file]):
                    lock_by_user, lock_owner, revision = get_file_info(file)
                    if lock_by_user:
                        listbox.insert('', 'end', values=('locked',revision, file))
                    elif lock_by_user== False and lock_owner == "":
                        listbox.insert('', 'end', values=('unlocked',revision, file))
                    else:
                        add_file = tk.messagebox.askyesno("File is locked", f"The file {file} is locked by {lock_owner}. Do you want to add it to the patch anyway?")
                        if add_file:
                            listbox.insert('', 'end', values=('@locked',revision, file))
            else:
                files_outside_svn.append(file)
        if os.path.isdir(file):
            for root, dirs, files in os.walk(file):
                for file in files:
                    file = os.path.join(root, file)
                    if file.startswith(svn_path):
                        file = file.replace("\\", "/")
                        file = file.replace(svn_path + "/", "")
                        if not check_files_is_present(listbox, [file]):
                            lock_by_user, lock_owner,revision = get_file_info(file)
                            if lock_by_user:
                                listbox.insert('', 'end', values=('locked',revision, file))
                            elif lock_by_user== False and lock_owner == "":
                                listbox.insert('', 'end', values=('unlocked',revision, file))
                            else:
                                add_file = tk.messagebox.askyesno("File is locked", f"The file {file} is locked by {lock_owner}. Do you want to add it to the patch anyway?")
                                if add_file:
                                    listbox.insert('', 'end', values=('@locked',revision, file))
                    else:
                        files_outside_svn.append(file)
    if files_outside_svn:
        tk.messagebox.showerror("Error", "The following files are not in the SVN repository and will not be added to the patch: \n" + "\n".join(files_outside_svn))

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
        
# patches_operation.py
from db_handler import dbClass
from svn_operations import get_file_specific_version, get_file_info, commit_files, get_file_revision
import os
from config import load_config, verify_config, log_error
from patch_generation import create_patch_files
import tkinter as tk
import time
from patch_utils import get_md5_checksum, cleanup_files, create_depend_txt, create_readme_file, setup_patch_folder, create_main_sql_file
from tkinter import messagebox
import datetime as date

patch_info_dict = {}

selected_patch = None

def refresh_patches(treeview, temp, application_id, username):
    """
    Refresh the patches displayed in the Treeview.
    """
    
    db = dbClass()
    
    # Clear existing items
    for item in treeview.get_children():
        treeview.delete(item)

    patch_info_dict.clear()
    
    # Fetch patches from the database
    patches = db.get_patch_list(temp, application_id)
    # Insert patches into the Treeview
    for patch in patches:

        patch_info_dict[patch["NAME"]] = patch

        treeview.insert("", "end", values=(
            patch["NAME"], 
            patch["COMMENTS"], 
            patch["PATCH_SIZE"], 
            patch["USER_ID"], 
            patch["CREATION_DATE"], 
            patch["CHECK_LIST_COUNT"]
        ))

def refresh_patches_dict(temp, application_id):
    """
    Refresh the patches displayed in the Treeview.
    """
    
    db = dbClass()

    patch_info_dict.clear()
    
    # Fetch patches from the database
    patches = db.get_patch_list(temp, application_id)
    # Insert patches into the Treeview
    for patch in patches:
        patch_info_dict[patch["NAME"]] = patch


def get_full_patch_info(patch_name):
    """
    Retrieve the full patch information from the dictionary.
    """
    return patch_info_dict.get(patch_name, None)


def set_selected_patch(patch):
    global selected_patch
    selected_patch = patch

def get_selected_patch():
    return selected_patch

def build_patch(patch_info):
    config = load_config()
    patch_version_folder = os.path.join(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), patch_info["NAME"])
    os.makedirs(patch_version_folder, exist_ok=True)
    try:
        db = dbClass()
        verify_config()
        svn_path = config.get("svn_path")
        
        patch_id = patch_info["PATCH_ID"]
        files = db.get_patch_file_list(patch_id)
        
        
        
        for file in files:
            if file["FOLDER_TYPE"] == '1':
                file_path = file["PATH"]
                file_location = f"{svn_path}/webpage{file['PATH']}"
                destination_folder = f"{patch_version_folder}/Web"
            else:
                file_path = file["PATH"].replace("StoredProcedures", "SP")
                file_location = f"{svn_path}/Database{file['PATH']}"
                destination_folder = f"{patch_version_folder}/DB"
            
            get_file_specific_version(file_location, file_path, file["NAME"], 
                                    file["VERSION"], destination_folder)
        
        create_readme_file(patch_version_folder, patch_info["NAME"], 
                          patch_info["USER_ID"], str(patch_info["CREATION_DATE"]), 
                          patch_info["COMMENTS"], files)
        
        create_main_sql_file(patch_version_folder, files, patch_name=patch_info["NAME"])
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        tk.messagebox.showinfo("Info", "Patch built successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        tk.messagebox.showerror("Error", f"Failed to build patch: {e}")
        log_error(f"Failed to build patch: {str(e)}")
        log_error(f"Date:" + date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        log_error(f"------------------------------")

def refresh_patch_files(treeview, patch_info):
    """
    Refresh the files in the patch.
    """
    db = dbClass()
    
    # Clear existing items
    for item in treeview.get_children():
        treeview.delete(item)

    patch_id = patch_info["PATCH_ID"]
    files = db.get_patch_file_list(patch_id)
    for file in files:
        if file["FOLDER_TYPE"] == '1':
            file_path = "webpage" + file["PATH"]
        else:
            file_path = 'Database' + file["PATH"]
        lock_by_user,lock_owner,svn_revision, lock_date = get_file_info(file_path)
        if lock_by_user:
            treeview.insert('', 'end', values=('locked',file["VERSION"], file_path, lock_date))
        elif lock_by_user== False and lock_owner == "":
            treeview.insert('', 'end', values=('unlocked',file["VERSION"], file_path, lock_date))
        else:
            treeview.insert('', 'end', values=(f'@locked - {lock_owner}',file["VERSION"], file_path, lock_date))

def update_patch(selected_files, patch_id, patch_version_letter, patch_version_entry, 
                patch_description, switch_to_modify_patch_menu, unlock_files):
    verify_config()
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    username = config.get("username")

    patch_version_entry = patch_version_entry.upper()
    
    patch_name = patch_version_letter + patch_version_entry
    patch_version_folder = os.path.join(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), patch_name)
    try:
        if not selected_files or len(selected_files) == 0:
            if not messagebox.askyesno("No Files Selected", 
                                     "No files selected. Do you want to modify the patch to remove the files?"):
                return
        
        os.makedirs(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), exist_ok=True)
        commit_files(selected_files,unlock_files)
        
        db.conn.begin()
        db.update_patch_header(patch_id, patch_version_letter, patch_version_entry, patch_description)
        db.delete_patch_detail(patch_id)
        
        os.makedirs(patch_version_folder, exist_ok=True)
        
        for file in selected_files:
            fake_path = '$/Projects/SVN/' + file
            filename = os.path.basename(file)
            file_id = db.create_patch_detail(patch_id, fake_path, filename, get_file_revision(file))
            md5checksum = get_md5_checksum(f"{svn_path}/{file}")
            db.set_md5(patch_id, file_id, md5checksum)
            create_patch_files(file, svn_path, patch_version_folder)
        
        create_readme_file(patch_version_folder, patch_name, username, 
                         time.strftime("%Y-%m-%d %H:%M:%S"), patch_description, selected_files)
        
        create_main_sql_file(patch_version_folder, selected_files,
                           patch_name=patch_name)
        
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        db.conn.commit()
        refresh_patches_dict(False, patch_version_letter)
        full_patch_info = get_full_patch_info(patch_name)
        switch_to_modify_patch_menu(full_patch_info)
        tk.messagebox.showinfo("Success", "Patch updated successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        tk.messagebox.showerror("Error", f"Failed to update patch: {e}")
        log_error(f"Failed to update patch: {str(e)}")
        log_error(f"Date:" + date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        log_error(f"------------------------------")
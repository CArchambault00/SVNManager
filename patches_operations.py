# patches_operation.py
from db_handler import dbClass
from svn_operations import get_file_specific_version, get_file_info, commit_files, get_file_head_revision
import os
from config import load_config, verify_config, log_error, log_success
from patch_generation import create_patch_files_batch
import tkinter as tk
import time
from patch_utils import get_md5_checksum, cleanup_files, create_depend_txt, create_readme_file, setup_patch_folder, create_main_sql_file
from tkinter import messagebox
import datetime as date
from dialog import display_patch_files

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
        # Replace None or empty fields with ""
        name = patch.get("NAME") or ""
        comments = patch.get("COMMENTS") or ""
        patch_size = patch.get("PATCH_SIZE") or 0
        user_id = patch.get("USER_ID") or ""
        creation_date = patch.get("CREATION_DATE") or ""
        checklist_count = patch.get("CHECK_LIST_COUNT") or ""

        patch_info_dict[name] = patch

        treeview.insert("", "end", values=(
            name,
            comments,
            patch_size,
            user_id,
            creation_date,
            checklist_count
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
            
            # Get the specific version of the file from SVN
            get_file_specific_version(
                file_location,
                file_path,
                file["NAME"],
                file["VERSION"],  # Use the version stored in the database
                destination_folder
            )
        
        # Create supporting files with the correct file versions
        create_readme_file(
            patch_version_folder,
            patch_info["NAME"],
            patch_info["USER_ID"],
            str(patch_info["CREATION_DATE"]),
            patch_info["COMMENTS"],
            files  # Pass the files with their versions from the database
        )
        
        create_main_sql_file(patch_version_folder, files, patch_name=patch_info["NAME"])
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        tk.messagebox.showinfo("Info", "Patch built successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        tk.messagebox.showerror("Error", f"Failed to build patch: {e}")
        print(f"Failed to build patch: {str(e)}")
        print(f"Date:" + date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print(f"------------------------------")
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
            item = treeview.insert('', 'end', values=('locked',file["VERSION"], file_path, lock_date))
            treeview.selection_add(item)
        elif lock_by_user== False and lock_owner == "":
            item = treeview.insert('', 'end', values=('unlocked',file["VERSION"], file_path, lock_date))
            treeview.selection_add(item)
        else:
            item = treeview.insert('', 'end', values=(f'@locked - {lock_owner}',file["VERSION"], file_path, lock_date))
            treeview.selection_add(item)

def update_patch(selected_files, patch_id, patch_version_prefixe, patch_version_entry, 
                patch_description, switch_to_modify_patch_menu, unlock_files):
    verify_config()
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    username = config.get("username")

    patch_version_entry = patch_version_entry.upper()
    patch_name = patch_version_prefixe + patch_version_entry
    
    # Add old patch folder path to handle cleanup
    old_patch_name = patch_info_dict.get(patch_name, {}).get("NAME")
    if old_patch_name:
        old_patch_folder = os.path.join(config.get("current_patches"), old_patch_name)
        cleanup_files(old_patch_folder)  # Clean up old patch folder
        
    patch_version_folder = os.path.join(config.get("current_patches"), patch_name)
    # Clean up target folder as well
    cleanup_files(patch_version_folder)
    
    try:
        if not patch_version_entry:
            messagebox.showerror("Error", "Patch version is required!")
            return
        
        if not patch_description:
            messagebox.showerror("Error", "Patch description is required!")
            return

        if not selected_files or len(selected_files) == 0:
            if not messagebox.askyesno("No Files Selected", 
                                     "No files selected. Do you want to modify the patch to have no files?"):
                return
        
        os.makedirs(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), exist_ok=True)
        commit_files(selected_files,unlock_files)
        
        db.conn.begin()
        db.update_patch_header(patch_id, patch_version_prefixe, patch_version_entry, patch_description)
        db.delete_patch_detail(patch_id)
        
        os.makedirs(patch_version_folder, exist_ok=True)
        
        for file in selected_files:
            fake_path = '$/Projects/SVN/' + file
            filename = os.path.basename(file)
            file_id = db.create_patch_detail(patch_id, fake_path, filename, get_file_head_revision(file))
            md5checksum = get_md5_checksum(f"{svn_path}/{file}")
            db.set_md5(patch_id, file_id, md5checksum)
            
        create_patch_files_batch(selected_files, svn_path, patch_version_folder)
        
        create_readme_file(patch_version_folder, patch_name, username, 
                         time.strftime("%Y-%m-%d %H:%M:%S"), patch_description, selected_files)
        
        create_main_sql_file(patch_version_folder, selected_files,
                           patch_name=patch_name)
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        db.conn.commit()
        
        # Refresh patches dictionary and update global state
        refresh_patches_dict(False, patch_version_prefixe)
        full_patch_info = get_full_patch_info(patch_name)
        
        # Update the selected patch state
        set_selected_patch(full_patch_info)
        
        # Clear and update current state before switching menus
        from state_manager import state_manager
        state_manager.clear_state("modify_patch")
        state_manager.current_menu = "modify_patch"
        
        # Get fresh state and update it with new values
        modify_patch_state = state_manager.get_state("modify_patch")
        modify_patch_state["patch_details"] = full_patch_info
        modify_patch_state["original_patch_details"] = full_patch_info.copy()
        
        # Switch to modify patch menu with updated info
        switch_to_modify_patch_menu(full_patch_info)
        
        success_details = f"Patch: {patch_name}\nFiles: {len(selected_files)}\nDescription: {patch_description}"
        log_success("Patch Update", success_details)
        tk.messagebox.showinfo("Success", "Patch updated successfully!")
        
    except Exception as e:
        db.conn.rollback()
        # Clean up any partially created files on error
        cleanup_files(patch_version_folder)
        error_msg = f"Failed to update patch: {str(e)}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        tk.messagebox.showerror("Error", error_msg)

def view_files_from_patch(patch_info):
    ## Show files from the patch in a dialog
    db = dbClass()
    
    patch_id = patch_info["PATCH_ID"]
    files = db.get_patch_file_list(patch_id)
    file_list = []

    for file in files:
        if file["FOLDER_TYPE"] == '1':
            file_path = "webpage" + file["PATH"]
        else:
            file_path = 'Database' + file["PATH"]
        lock_by_user,lock_owner,svn_revision, lock_date = get_file_info(file_path)
        if lock_by_user:
            file_list.append(f'locked || VERSION: {file["VERSION"]} || {file_path} || LOCKDATE: {lock_date}')
        elif lock_by_user== False and lock_owner == "":
            file_list.append(f'unlocked || VERSION: {file["VERSION"]} || {file_path}')
        else:
            file_list.append(f'@locked - {lock_owner} || VERSION: {file["VERSION"]} || {file_path} || LOCKDATE: {lock_date}')

    display_patch_files(file_list, patch_info["NAME"], patch_info["COMMENTS"], 
                        patch_info["USER_ID"], str(patch_info["CREATION_DATE"]))

def remove_patch(patch_info):
    """
    Remove a patch from the database.
    
    Args:
        patch_info: Dictionary containing patch details
    """
    try:
        db = dbClass()
        verify_config()
        
        patch_id = patch_info["PATCH_ID"]
        patch_name = patch_info["NAME"]
        
        # Ask for confirmation before removing the patch
        if not messagebox.askyesno("Confirm Removal", 
                                f"Are you sure you want to remove patch '{patch_name}'?\nThis action cannot be undone."):
            return
        
        # Remove the patch from the database
        db.conn.begin()
        db.remove_patch(patch_id)
        # db.remove_patch_details(patch_id)
        db.conn.commit()
        
        # Log the successful removal
        success_details = f"Patch: {patch_name}\nID: {patch_id}"
        log_success("Patch Removal", success_details)
        
        messagebox.showinfo("Success", f"Patch '{patch_name}' removed successfully!")
        return True
    except Exception as e:
        db.conn.rollback()
        error_msg = f"Failed to remove patch: {str(e)}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        messagebox.showerror("Error", error_msg)
        return False


# patches_operation.py
from db_handler import dbClass
from svn_operations import get_file_specific_version, get_file_info, commit_files, revert_files, get_file_revision
from patch_generation import PATCH_DIR, write_sql_commands
import os
from config import load_config
from patch_generation import create_patch_files
import tkinter as tk
import time
from utils import get_md5_checksum, cleanup_files

patch_info_dict = {}

selected_patch = None

def refresh_patches(treeview, temp, module, username):
    """
    Refresh the patches displayed in the Treeview.
    """
    
    db = dbClass()
    
    # Clear existing items
    for item in treeview.get_children():
        treeview.delete(item)

    patch_info_dict.clear()
    
    # Fetch patches from the database
    patches = db.get_patch_list(temp, module)
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

def refresh_patches_dict(temp, module):
    """
    Refresh the patches displayed in the Treeview.
    """
    
    db = dbClass()

    patch_info_dict.clear()
    
    # Fetch patches from the database
    patches = db.get_patch_list(temp, module)
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

    db = dbClass()
    
    patch_id = patch_info["PATCH_ID"]
    
    os.makedirs(PATCH_DIR, exist_ok=True)
    files = db.get_patch_file_list(patch_id)
    config = load_config()
    svn_path = config.get("svn_path")
   
    patch_version_folder = os.path.join(PATCH_DIR, patch_info["NAME"])
    os.makedirs(patch_version_folder, exist_ok=True)
    for file in files:
        if file["FOLDER_TYPE"] == '1':
            file_path = file["PATH"]
            file_location = svn_path + "/webpage" + file["PATH"]
            destination_folder = patch_version_folder + "/Web"
        else:
            file_path = file["PATH"]
            file_path = file_path.replace("StoredProcedures", "SP")
            file_location = svn_path + "/Database" + file["PATH"]
            destination_folder = patch_version_folder + "/DB"
        get_file_specific_version(file_location, file_path, file["NAME"], file["VERSION"], destination_folder)

    with open(os.path.join(patch_version_folder, "ReadMe.txt"), "w") as readme:
        readme.write("Patch " + patch_info["NAME"] + "\n")
        readme.write(patch_info["USER_ID"] + "\n")
        readme.write(str(patch_info["CREATION_DATE"]) + "\n")
        readme.write("\n")
        readme.write(patch_info["COMMENTS"])
        readme.write("\n")
        readme.write("\n")
        readme.write("Patch Content:\n")
        readme.write("\n")
        for file in files:
            readme.write(file["PATH"] + "\n")

    with open(os.path.join(patch_version_folder, "MainSQL.sql"), "w") as main_sql:
        main_sql.write("promp &&HOST\n")
        main_sql.write("promp &&PERSON\n")
        main_sql.write("set echo on\n\n")
        for file in files:
            if file["FOLDER_TYPE"] == '2':
                schema = file["PATH"].split("/")[1]
                file_path = 'DB'
                file_path += file["PATH"].replace("Database", "DB")
                file_path = file_path.replace("StoredProcedures", "SP")
                write_sql_commands(main_sql, file_path, schema)

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
        lock_by_user,lock_owner,svn_revision = get_file_info(file_path)
        if lock_by_user:
            treeview.insert('', 'end', values=('locked',file["VERSION"], file_path))
        elif lock_by_user== False and lock_owner == "":
            treeview.insert('', 'end', values=('unlocked',file["VERSION"], file_path))
        else:
            add_file = tk.messagebox.askyesno("File is locked", f"The file {file_path} is locked by {lock_owner}. Do you want to add it to the patch anyway?")
            if add_file:
                treeview.insert('', 'end', values=('@locked',file["VERSION"], file_path))

def update_patch(selected_files, patch_id, patch_version_letter, patch_version_entry, patch_description, switch_to_modify_patch_menu):
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    username = config.get("username")
    try:
        os.makedirs(PATCH_DIR, exist_ok=True)
        commit_files(selected_files)
        db.conn.begin()
        db.update_patch_header(patch_id, patch_version_letter, patch_version_entry, patch_description)
        db.delete_patch_detail(patch_id)
        for file in selected_files:
            fake_path = '$/Projects/SVN/' + file
            filename = os.path.basename(file)
            file_id = db.create_patch_detail(patch_id, fake_path, filename, get_file_revision(file))
            
            md5checksum = get_md5_checksum(svn_path + "/" + file)
            db.set_md5(patch_id, file_id, md5checksum)
        patch_version_folder = os.path.join(PATCH_DIR, (patch_version_letter + patch_version_entry))
        os.makedirs(patch_version_folder, exist_ok=True)
        with open(os.path.join(patch_version_folder, "ReadMe.txt"), "w") as readme:
            readme.write("Patch " + patch_version_letter + patch_version_entry + "\n")
            readme.write(username + "\n")
            readme.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
            readme.write("\n")
            readme.write(patch_description)
            readme.write("\n")
            readme.write("\n")
            readme.write("Patch Content:\n")
            readme.write("\n")
            for file in selected_files:
                readme.write(file + "\n")
        with open(os.path.join(patch_version_folder, "MainSQL.sql"), "w") as main_sql:
            main_sql.write("promp &&HOST\n")
            main_sql.write("promp &&PERSON\n")
            main_sql.write("set echo on\n\n")
            for file in selected_files:
                # create a copy of the file in the patch directory in the patch version folder
                create_patch_files(file, svn_path, patch_version_folder, main_sql)
        db.conn.commit()
        refresh_patches_dict(False, patch_version_letter)
        full_patch_info = get_full_patch_info(patch_version_letter+patch_version_entry)
        switch_to_modify_patch_menu(full_patch_info)
        tk.messagebox.showinfo("Success", "Patch updated successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        revert_files(selected_files)
        tk.messagebox.showerror("Error", f"Failed to update patch: {e}")
    
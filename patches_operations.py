# patches_operation.py
from db_handler import dbClass
from svn_operations import get_file_specific_version
from patch_generation import PATCH_DIR
import os
from config import load_config
import shutil
from patch_generation import write_sql_commands

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
    print(patch_info) 
    print(patch_id)
    
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
                schema = file["PATH"].split("\\")[1]
                file_path = 'DB'
                file_path += file["PATH"].replace("Database", "DB")
                file_path = file_path.replace("StoredProcedures", "SP")
                write_sql_commands(main_sql, file_path, schema)
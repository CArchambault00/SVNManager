# file_operations.py
import os
import shutil
from svn_operations import commit_files
from tkinter import messagebox
from config import load_config
import time

PATCH_DIR = "D:/cyframe/jtdev/Patches/Current"

def generate_patch(selected_files, patch_letter, patch_version, patch_description):
    config = load_config()
    svn_path = config.get("svn_path")
    os.makedirs(PATCH_DIR, exist_ok=True)
    commit_files(selected_files)
    if not patch_version:
        messagebox.showerror("Error", "Patch version is required!")
        return
    patch_version_folder = os.path.join(PATCH_DIR, (patch_letter + patch_version))
    os.makedirs(patch_version_folder, exist_ok=True)
    with open(os.path.join(patch_version_folder, "ReadMe.txt"), "w") as readme:
        readme.write("Patch " + patch_letter + patch_version + "\n")
        readme.write(config.get("username") + "\n")
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
    
def create_patch_files(file, svn_path, patch_version_folder, main_sql):
    file_path_no_svn = file
    if file_path_no_svn.startswith("webpage"):
        dest_file = file_path_no_svn.replace("webpage", "Web")
        dest_file = os.path.join(patch_version_folder, dest_file)
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        file_location = svn_path + "/" + file_path_no_svn
        shutil.copy2(file_location, dest_file)
    elif file_path_no_svn.startswith("Database"):
            sql_path = file_path_no_svn.replace("Database", "DB")
            sql_path = sql_path.replace("StoredProcedures", "SP")
            dest_file = os.path.join(patch_version_folder, sql_path)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            file_location = svn_path + "/" + file_path_no_svn
            shutil.copy2(file_location, dest_file)
            schema = file_path_no_svn.split("\\")[1]
            write_sql_commands(main_sql, sql_path, schema)

def write_sql_commands(sql_file, file_path, schema):
    sql_file.write("set scan on\n")
    if schema:
        sql_file.write(f"connect {schema}/{schema}@&&HOST\n")
    else:
        sql_file.write("#WARNING connect schema/schema@&&HOST\n")
    sql_file.write("set scan off\n")
    sql_file.write("set echo off\n")
    sql_file.write(f"prompt Loading \"{file_path}\" ...\n")
    sql_file.write(f"@@\"{file_path}\"\n")
    sql_file.write("show error\n")
    sql_file.write("set echo on\n\n")
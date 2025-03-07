import os
import shutil
from svn_operations import commit_files, get_file_revision
from tkinter import messagebox
import time
import version_operation as vo
from db_handler import dbClass
from utils import get_md5_checksum
from config import load_config

PATCH_DIR = "D:/cyframe/jtdev/Patches/Current"

def generate_patch(selected_files, patch_letter, patch_version, patch_description):
    
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    username = config.get("username")
    os.makedirs(PATCH_DIR, exist_ok=True)
    commit_files(selected_files)
    tempYN = False
    patch_id = db.create_patch_header(patch_letter, patch_version, patch_description, username, tempYN, vo.major, vo.minor, vo.revision)
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
        
    if not patch_version:
        messagebox.showerror("Error", "Patch version is required!")
        return
    patch_version_folder = os.path.join(PATCH_DIR, (patch_letter + patch_version))
    os.makedirs(patch_version_folder, exist_ok=True)
    with open(os.path.join(patch_version_folder, "ReadMe.txt"), "w") as readme:
        readme.write("Patch " + patch_letter + patch_version + "\n")
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
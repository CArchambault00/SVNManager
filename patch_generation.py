import os
import shutil
from svn_operations import commit_files, get_file_revision, revert_files, copy_InstallConfig, copy_RunScript, copy_UnderTestInstallConfig
from tkinter import messagebox
import time
import version_operation as vo
from db_handler import dbClass
from utils import get_md5_checksum, cleanup_files, create_depend_txt
from config import load_config

PATCH_DIR = "D:/cyframe/jtdev/Patches/Current"

def generate_patch(selected_files, patch_letter, patch_version, patch_description):
    
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    username = config.get("username")
    try:
        if not patch_version:
            messagebox.showerror("Error", "Patch version is required!")
            return
        if selected_files is None or len(selected_files) == 0:
            # Confirmation dialog for no files selected
            if messagebox.askyesno("No Files Selected", "No files selected. Do you want to create an empty patch?"):
                selected_files = []
            else:
                return
        os.makedirs(PATCH_DIR, exist_ok=True)
        commit_files(selected_files)

        db.conn.begin()

        tempYN = False
        patch_id = db.create_patch_header(patch_letter, patch_version, patch_description, username, tempYN, vo.major, vo.minor, vo.revision)
        for file in selected_files:
            fake_path = '$/Projects/SVN/' + file
            filename = os.path.basename(file)
            file_id = db.create_patch_detail(patch_id, fake_path, filename, get_file_revision(file))
            
            md5checksum = get_md5_checksum(svn_path + "/" + file)
            db.set_md5(patch_id, file_id, md5checksum)
        
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
            webpage_files = [file for file in selected_files if file.startswith("webpage")]
            database_files = [file for file in selected_files if not file.startswith("webpage")]
            readme.write("Webpage Files:\n")
            for file in webpage_files:
                readme.write(file + " (" + get_file_revision(file) + ")" + "\n")
            readme.write("\n")
            readme.write("Database Files:\n")
            for file in database_files:
                readme.write(file + " (" + get_file_revision(file) + ")" + "\n")
        with open(os.path.join(patch_version_folder, "MainSQL.sql"), "w") as main_sql:
            main_sql.write("prompt &&HOST\n")
            main_sql.write("prompt &&PERSON\n")
            main_sql.write("set echo on\n\n")
            for file in selected_files:
                # create a copy of the file in the patch directory in the patch version folder
                create_patch_files(file, svn_path, patch_version_folder, main_sql)
            main_sql.write("set echo on\n")
            main_sql.write("connect CMATC/CMATC@&&HOST\n")
            main_sql.write("CALL CMATC.PKG_VERSION_CONTROL.SETCURRENTVERSION('CORE_SVN'," + vo.major + "," + vo.minor + "," + vo.revision + ",'&&PERSON' );\n")
            main_sql.write("commit;\n")
            main_sql.write("\n")
            main_sql.write("exit;\n")
        copy_InstallConfig(patch_version_folder)
        copy_RunScript(patch_version_folder)
        copy_UnderTestInstallConfig(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        db.conn.commit()
        messagebox.showinfo("Info", "Patch created successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        revert_files(selected_files)
        messagebox.showerror("Error", "Failed to create patch! " + str(e))
    
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
            schema = file_path_no_svn.split("/")[1]
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
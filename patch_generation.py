import os
from svn_operations import commit_files, get_file_revision
from tkinter import messagebox
import time
import datetime as date
import version_operation as vo
from db_handler import dbClass
from patch_utils import get_md5_checksum, cleanup_files, create_depend_txt, create_readme_file, setup_patch_folder, create_main_sql_file, create_patch_files
from config import load_config, verify_config, log_error

def generate_patch(selected_files, patch_letter, patch_version, patch_description, unlock_files):
    db = dbClass()

    try:
        verify_config()
        config = load_config()

        patch_name = patch_letter + patch_version
        patch_version_folder = os.path.join(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), patch_name)

        svn_path = config.get("svn_path")
        username = config.get("username")

        if not patch_version:
            messagebox.showerror("Error", "Patch version is required!")
            return
        
        if not selected_files or len(selected_files) == 0:
            if not messagebox.askyesno("No Files Selected", "No files selected. Do you want to create an empty patch?"):
                return
        
        os.makedirs(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), exist_ok=True)
        commit_files(selected_files, unlock_files)
        
        db.conn.begin()
        patch_id = db.create_patch_header(patch_letter, patch_version, patch_description, username, 
                                        False, vo.major, vo.minor, vo.revision)
        
        os.makedirs(patch_version_folder, exist_ok=True)
        application_id = db.get_application_id(patch_letter)
        
        for file in selected_files:
            fake_path = '$/Projects/SVN/' + file
            filename = os.path.basename(file)
            file_id = db.create_patch_detail(patch_id, fake_path, filename, get_file_revision(file))
            md5checksum = get_md5_checksum(f"{svn_path}/{file}")
            db.set_md5(patch_id, file_id, md5checksum)
            create_patch_files(file, svn_path, patch_version_folder)
        
        create_readme_file(patch_version_folder, patch_name, username, 
                         time.strftime("%Y-%m-%d %H:%M:%S"), patch_description, selected_files)
        
        create_main_sql_file(patch_version_folder, selected_files, version_info=(vo.major, vo.minor, vo.revision), application_id=application_id)
        
            
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        db.conn.commit()
        messagebox.showinfo("Info", "Patch created successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        messagebox.showerror("Error", f"Failed to create patch! {str(e)}")
        log_error(f"Failed to create patch: {str(e)}")
        log_error(f"Date:" + date.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        log_error(f"------------------------------")
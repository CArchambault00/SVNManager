import os
from svn_operations import commit_files, get_file_head_revision_batch, get_relative_path
from tkinter import messagebox
import time
import datetime as date
import version_operation as vo
from db_handler import dbClass
from patch_utils import get_md5_checksum_batch, cleanup_files, create_depend_txt, create_readme_file, setup_patch_folder, create_main_sql_file, create_patch_files_batch
from config import load_config, verify_config, log_error, log_success
import subprocess

def generate_patch(selected_files, patch_prefixe, patch_version, patch_description, unlock_files):
    db = dbClass()

    try:
        verify_config()
        config = load_config()
        
        patch_version = patch_version.upper()
        patch_name = patch_prefixe + patch_version
        patch_version_folder = os.path.join(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), patch_name)

        svn_path = config.get("svn_path")
        username = config.get("username")

        if not '-' in patch_version or patch_version.count('-') != 1 or patch_version.split('-')[1] == '':
            messagebox.showerror("Error", "Invalid patch version format! Must contain '-*'\n" \
            "Following those patterns (Can be combined):\n" \
            "Web changes :\n" \
            "*-W0 -> web page, change function, logic(not visible for user)\n" \
            "*-W1 -> add/change elements on the web page..\n" \
            "*-W2 -> add/change business logic.. *Breaking change*\n\n" \
            "Server/Database changes :\n" \
            "*-S0 -> min. logical Change; New Label; System Parameter; New type report.\n" \
            "*-S1 -> new function, new param\n" \
            "*-S2 -> add Param; delete Param; alter table; change column size;\n" \
            "")
            return

        if not patch_version:
            messagebox.showerror("Error", "Patch version is required!")
            return
        
        if not patch_description:
            messagebox.showerror("Error", "Patch description is required!")
            return
        
        if not selected_files or len(selected_files) == 0:
            if not messagebox.askyesno("No Files Selected", "No files selected. Do you want to create an empty patch?"):
                return
        
        db.conn.begin()

        patchAlreadyExists = db.check_patch_exists(patch_prefixe, patch_version.split("-")[0])
        if patchAlreadyExists:
            raise ValueError(f"Patch with prefix '{patch_prefixe}' and version '{patch_version.split('-')[0]}' already exists. "
                            "You might want to update the existing patch or use the next version.")

        os.makedirs(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), exist_ok=True)
        
        # Commit files in batches
        BATCH_SIZE = 50
        for i in range(0, len(selected_files), BATCH_SIZE):
            batch = selected_files[i:i + BATCH_SIZE]
            commit_files(batch, unlock_files)
        
        
        patch_id = db.create_patch_header(patch_prefixe, patch_version, patch_description, username, 
                                        False, vo.major, vo.minor, vo.revision)
        
        os.makedirs(patch_version_folder, exist_ok=True)
        
        application_id = db.get_application_id(patch_prefixe)

        wc_root = subprocess.run(
            ["svn", "info", "--show-item", "wc-root", svn_path],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).stdout.strip().replace("\\", "/")

        # Process files in batches for better performance
        for i in range(0, len(selected_files), BATCH_SIZE):
            batch = selected_files[i:i + BATCH_SIZE]
            
            # Get file HEAD revisions in batch
            revisions = get_file_head_revision_batch(batch)
            
            # Calculate MD5 checksums in batch
            md5_checksums = get_md5_checksum_batch([f"{wc_root}/{file}" for file in batch])
            
            # Create patch details in batch
            for file in batch:
                fake_path = '$/Projects/SVN/' + file
                filename = os.path.basename(file)
                clean_path = file.replace(filename, "")

                parts = file.replace("\\", "/").split("/")
                if file.startswith('Projects/'):
                    soft_path = "/".join(parts[:4])
                else:
                    soft_path = "/".join(parts[:1])
                # Get relative folder which is 
                folder_id = db.get_folder_id(soft_path)
                file_id = db.create_patch_detail(patch_id, fake_path, clean_path, filename, revisions.get(file, ""), folder_id)
                md5checksum = md5_checksums.get(f"{wc_root}/{file}")
                if md5checksum:
                    db.set_md5(patch_id, file_id, md5checksum)

        # Create patch files in optimized batches
        create_patch_files_batch(selected_files, svn_path, patch_version_folder)
        
        # Create supporting files
        create_readme_file(patch_version_folder, patch_name, username, 
                         time.strftime("%Y-%m-%d %H:%M:%S"), patch_description, selected_files)
        
        create_main_sql_file(patch_version_folder, selected_files, version_info=(vo.major, vo.minor, vo.revision), application_id=application_id)
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        db.conn.commit()
        success_details = f"Patch: {patch_name}\nFiles: {len(selected_files)}\nDescription: {patch_description}"
        log_success("Patch Creation", success_details)
        messagebox.showinfo("Info", "Patch created successfully!")
    except Exception as e:
        db.conn.rollback()
        cleanup_files(patch_version_folder)
        error_msg = f"Failed to create patch: {str(e)}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        messagebox.showerror("Error", error_msg)
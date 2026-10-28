# patches_operation.py
from db_handler import dbClass
from svn_operations import get_file_specific_version, get_file_info_batch, commit_files, get_file_head_revision_batch, get_wc_root
import os
from config import load_config, verify_config, log_error, log_success, log_action
from patch_utils import (
    get_md5_checksum_batch, cleanup_files, create_depend_txt, create_readme_file,
    setup_patch_folder, create_main_sql_file, get_managed_dest_paths,
    backup_extra_patch_files, restore_extra_patch_files, backup_existing_main_sql,
    create_patch_files_batch,
)
import tkinter as tk
import time
from tkinter import messagebox
import datetime as date
from version_operation import parse_version
import subprocess
import shutil
from dialog import display_patch_files
from cyra_release import (
    classify_files as classify_cyra_files,
    normalize_rel as cyra_normalize_rel,
    is_cyra_path,
    files_for_patch_package,
    build_update_plan as build_cyra_update_plan,
    find_release_for_patch as find_cyra_release_for_patch,
    apply_version_bump as apply_cyra_version_bump,
    build_and_commit_release as build_and_commit_cyra_release,
    record_cyra_link,
)

patch_info_dict = {}

selected_patch = None

def refresh_patches(treeview, temp, application_id, username):
    """
    Refresh the patches displayed in the Treeview (synchronous).
    Prefer busy_ops.load_patches_busy for UI entry points.
    """
    from busy_ops import apply_patches_to_tree, fetch_patches

    patches = fetch_patches(temp, application_id)
    apply_patches_to_tree(treeview, patches)

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
    log_action("Patch build started", patch=patch_info.get("NAME"), patch_id=patch_info.get("PATCH_ID"))
    
    patch_version_folder = os.path.join(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), patch_info["NAME"])
    os.makedirs(patch_version_folder, exist_ok=True)
    try:
        db = dbClass()
        verify_config()
        svn_path = config.get("svn_path")
        
        patch_id = patch_info["PATCH_ID"]
        files = db.get_patch_file_list_new(patch_id)

        wc_root = get_wc_root(svn_path)
        for file in files:
            if file["FOLDER_TYPE"] == '1':
                file_path = file["PATH"].replace(file["SVN_PATH"], "Web")
                file_path = file_path.replace("webpage", "Web")
                file_location = f"{wc_root}/{file['PATH']}"
            else:
                file_path = file["PATH"].replace(file["SVN_PATH"], "DB")
                file_path = file_path.replace("StoredProcedures", "SP")
                file_path = file_path.replace("Database", "DB")
                file_location = f"{wc_root}/{file['PATH']}"
            get_file_specific_version(
                file_location,
                file_path,
                file["NAME"],
                file["VERSION"],  # Use the version stored in the database
                patch_version_folder
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
    Refresh the files in the patch (synchronous).
    Prefer busy_ops.load_patch_files_busy / load_modify_patch_screen_busy for UI.
    """
    from busy_ops import apply_patch_file_rows, fetch_patch_file_rows

    rows = fetch_patch_file_rows(patch_info)
    apply_patch_file_rows(treeview, rows)

def update_patch(selected_files, patch_id, patch_version_prefixe, patch_version_entry, 
                patch_description, switch_to_modify_patch_menu, unlock_files, status_callback=None):
    def status(msg):
        if status_callback:
            status_callback(msg)

    verify_config()
    db = dbClass()
    config = load_config()
    svn_path = config.get("svn_path")
    username = config.get("username")
    current_patches = config.get("current_patches", "D:/cyframe/jtdev/Patches/Current")

    patch_version_entry = patch_version_entry.upper()
    patch_name = patch_version_prefixe + patch_version_entry
    log_action(
        "Patch update started",
        patch=patch_name,
        patch_id=patch_id,
        file_count=len(selected_files or []),
        unlock=unlock_files,
    )
    patch_version_folder = os.path.join(current_patches, patch_name)
    extras_backup = None

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

        # Cyra release automation (modification): Cyra files in the updated
        # patch rebuild the Cyra release already linked to this patch (same
        # version, no bump), or create the next release linked to it.
        cyra_groups = classify_cyra_files(selected_files)
        has_cyra = bool(cyra_groups["cyra"])
        cyra_plan = None
        cyra_note = ""
        wc_root_pre = get_wc_root(svn_path)
        if has_cyra:
            cyra_plan = build_cyra_update_plan(db, wc_root_pre, patch_name)
            action = (f"Rebuild Cyra release {cyra_plan['release_version']} (same version, "
                      "committed over the existing release in CyraReleases SVN)"
                      if cyra_plan.get("rebuild") else
                      f"Create Cyra release {cyra_plan['release_version']} "
                      "(cyra/VERSION + core/__init__.py updated, built and committed to CyraReleases SVN)")
            summary = (
                f"Files: {len(cyra_groups['cyra'])} Cyra, {len(cyra_groups['web'])} web, "
                f"{len(cyra_groups['db'])} database, {len(cyra_groups['other'])} other.\n\n"
                f"Update patch {patch_name}\n{action}\n"
                f"Link: Cyra {cyra_plan['release_version']} requires patch "
                f"{cyra_plan['link_patch_name']} ({cyra_plan['link_source']})\n\nContinue?"
            )
            if not messagebox.askyesno("Cyra release", summary):
                return
            if not cyra_plan.get("rebuild"):
                status("Updating Cyra version files…")
                for rel in apply_cyra_version_bump(wc_root_pre, cyra_plan["release_version"], username):
                    if not any(cyra_normalize_rel(f) == rel for f in selected_files):
                        selected_files.append(rel)
        else:
            linked = find_cyra_release_for_patch(db, patch_name)
            if linked is not None:
                cyra_note = (f"\nNote: Cyra {linked['VERSION']} is linked to this patch, but no Cyra "
                             "files were included -- the release was NOT rebuilt.")

        status("Backing up extra patch files…")
        # Preserve manually-added files (e.g. DB scripts dropped into the patch folder)
        # that are not part of the locked/unlocked SVN file list.
        old_files = db.get_patch_file_list_new(patch_id)
        managed_dests = get_managed_dest_paths(old_files, svn_path)

        old_patch_folder = None
        for name, info in patch_info_dict.items():
            if info.get("PATCH_ID") == patch_id:
                old_patch_folder = os.path.join(current_patches, name)
                break
        if old_patch_folder is None:
            old_patch_folder = patch_version_folder

        # Keep the current MainSQL.sql as MainSQL (N).sql before the folder is rebuilt.
        backup_existing_main_sql(old_patch_folder)
        extras_backup = backup_extra_patch_files(old_patch_folder, managed_dests)

        if old_patch_folder and os.path.normpath(old_patch_folder) != os.path.normpath(patch_version_folder):
            cleanup_files(old_patch_folder)
        cleanup_files(patch_version_folder)
        
        os.makedirs(current_patches, exist_ok=True)
        status(f"Committing {len(selected_files)} file(s) to SVN…")
        commit_files(selected_files,unlock_files)

        # Web/DB patch package only — cyra/ is committed above and ships via CyraReleases.
        patch_files = files_for_patch_package(selected_files)

        wc_root = get_wc_root(svn_path)

        db.conn.begin()
        parsed_version = parse_version(patch_version_entry)
        if parsed_version:
            db.update_patch_header(patch_id, patch_version_prefixe, patch_version_entry, patch_description,
                                   parsed_version.major, parsed_version.minor, parsed_version.revision)
        else:
            db.update_patch_header(patch_id, patch_version_prefixe, patch_version_entry, patch_description)
        db.delete_patch_detail(patch_id)
        
        os.makedirs(patch_version_folder, exist_ok=True)

        BATCH_SIZE = 50
        folder_id_cache = {}
        total = len(patch_files)
        for i in range(0, len(patch_files), BATCH_SIZE):
            batch = patch_files[i:i + BATCH_SIZE]
            status(f"Recording file details ({min(i + BATCH_SIZE, total)}/{total})…")
            revisions = get_file_head_revision_batch(batch)
            md5_checksums = get_md5_checksum_batch([f"{wc_root}/{file}" for file in batch])

            for file in batch:
                if is_cyra_path(file):
                    continue
                fake_path = '$/Projects/SVN/' + file
                filename = os.path.basename(file)
                clean_path = file.replace(filename, "")

                parts = file.replace("\\", "/").split("/")
                if file.startswith('Projects/'):
                    soft_path = "/".join(parts[:4])
                else:
                    soft_path = "/".join(parts[:1])
                if soft_path == "cyra":
                    continue
                if soft_path not in folder_id_cache:
                    folder_id_cache[soft_path] = db.get_folder_id(soft_path)
                folder_id = folder_id_cache[soft_path]
                file_id = db.create_patch_detail(
                    patch_id, fake_path, clean_path, filename,
                    revisions.get(file, ""), folder_id,
                )
                md5checksum = md5_checksums.get(f"{wc_root}/{file}")
                if md5checksum:
                    db.set_md5(patch_id, file_id, md5checksum)
            
        status("Copying files into patch folder…")
        create_patch_files_batch(patch_files, svn_path, patch_version_folder)
        
        status("Writing ReadMe / MainSQL / depend…")
        create_readme_file(patch_version_folder, patch_name, username, 
                         time.strftime("%Y-%m-%d %H:%M:%S"), patch_description, patch_files)
        
        create_main_sql_file(patch_version_folder, patch_files,
                           patch_name=patch_name)
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)

        # Put back manually-added files that were not part of the SVN file list
        restore_extra_patch_files(extras_backup, patch_version_folder)
        extras_backup = None
        
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
        
        release_note = ""
        if cyra_plan is not None:
            # Patch update is committed at this point; a release failure must
            # not roll it back. The link can be fixed on the Cyra Releases page.
            try:
                result = build_and_commit_cyra_release(
                    wc_root, cyra_plan, username, patch_description, status_callback=status)
                record_cyra_link(db, cyra_plan)
                verb = "rebuilt" if cyra_plan.get("rebuild") else "built"
                release_note = (f"\nCyra {cyra_plan['release_version']} release {verb} and committed "
                                f"(SVN r{result['revision']}), linked to patch {patch_name}.")
            except Exception as rel_err:
                release_note = (f"\n\nWARNING: the patch was updated, but the Cyra release failed:\n{rel_err}\n"
                                "Rebuild the release manually, or link it on the Cyra Releases page.")
                log_error(f"Cyra release after patch update {patch_name} failed: {rel_err}", include_stack=True)

        success_details = f"Patch: {patch_name}\nFiles: {len(selected_files)}\nDescription: {patch_description}"
        log_success("Patch Update", success_details + release_note)
        tk.messagebox.showinfo("Success", "Patch updated successfully!" + release_note + cyra_note)
        
    except Exception as e:
        db.conn.rollback()
        # Clean up any partially created files on error
        cleanup_files(patch_version_folder)
        if extras_backup and os.path.exists(extras_backup):
            shutil.rmtree(extras_backup, ignore_errors=True)
        error_msg = f"Failed to update patch: {str(e)}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        tk.messagebox.showerror("Error", error_msg)

def view_files_from_patch(patch_info):
    ## Show files from the patch in a dialog
    db = dbClass()
    
    patch_id = patch_info["PATCH_ID"]
    files = db.get_patch_file_list_new(patch_id)
    file_list = []
    file_paths = [file["PATH"] for file in files]
    info_results = get_file_info_batch(file_paths) if file_paths else {}

    for file in files:
        file_path = file["PATH"]
        lock_by_user, lock_owner, svn_revision, lock_date = info_results.get(
            file_path, (False, "", "", "")
        )
        if lock_by_user:
            file_list.append(f'locked || VERSION: {file["VERSION"]} || {file_path} || LOCKDATE: {lock_date}')
        elif lock_owner == "":
            file_list.append(f'unlocked || VERSION: {file["VERSION"]} || {file_path}')
        else:
            file_list.append(f'@locked - {lock_owner} || VERSION: {file["VERSION"]} || {file_path} || LOCKDATE: {lock_date}')

    display_patch_files(file_list, patch_info["NAME"], patch_info["COMMENTS"], 
                        patch_info["USER_ID"], str(patch_info["CREATION_DATE"]))

def remove_patch(patch_info, confirm=True):
    """
    Remove a patch from the database.
    
    Args:
        patch_info: Dictionary containing patch details
        confirm: If True, ask for confirmation before removing
    """
    try:
        db = dbClass()
        verify_config()
        
        patch_id = patch_info["PATCH_ID"]
        patch_name = patch_info["NAME"]
        
        # Ask for confirmation before removing the patch
        if confirm:
            if not messagebox.askyesno(
                "Confirm Removal",
                f"Are you sure you want to remove patch '{patch_name}'?\nThis action cannot be undone.",
            ):
                log_action("Patch removal cancelled", patch=patch_name)
                return False

        log_action("Patch removal started", patch=patch_name, patch_id=patch_id)
        
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


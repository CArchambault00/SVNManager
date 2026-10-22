import os
from svn_operations import commit_files, get_file_head_revision_batch, get_wc_root
from tkinter import messagebox
import time
import datetime as date
import version_operation as vo
from db_handler import dbClass
from patch_utils import get_md5_checksum_batch, cleanup_files, create_depend_txt, create_readme_file, setup_patch_folder, create_main_sql_file, create_patch_files_batch
from config import load_config, verify_config, log_error, log_success, log_action
from cyra_release import (
    classify_files as classify_cyra_files,
    normalize_rel as cyra_normalize_rel,
    build_cyra_plan,
    apply_version_bump as apply_cyra_version_bump,
    build_and_commit_release as build_and_commit_cyra_release,
    record_cyra_link,
)

def generate_patch(selected_files, patch_prefixe, patch_version, patch_description, unlock_files, status_callback=None):
    def status(msg):
        if status_callback:
            status_callback(msg)

    db = dbClass()
    patch_version_folder = None

    try:
        verify_config()
        config = load_config()
        
        patch_version = patch_version.upper()
        patch_name = patch_prefixe + patch_version
        log_action(
            "Patch creation started",
            patch=patch_name,
            file_count=len(selected_files or []),
            unlock=unlock_files,
        )
        patch_version_folder = os.path.join(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), patch_name)

        svn_path = config.get("svn_path")
        username = config.get("username")

        # Cyra release automation: cyra/ files ship a Cyra release. A patch
        # is created only when web/db files are present (or no cyra/ at all).
        groups = classify_cyra_files(selected_files)
        has_cyra = bool(groups["cyra"])
        create_patch = bool(groups["web"] or groups["db"]) or not has_cyra
        cyra_plan = None

        if create_patch and (not '-' in patch_version or patch_version.count('-') != 1 or patch_version.split('-')[1] == ''):
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

        if create_patch and not patch_version:
            messagebox.showerror("Error", "Patch version is required!")
            return

        if create_patch and not patch_description:
            messagebox.showerror("Error", "Patch description is required!")
            return

        if not selected_files or len(selected_files) == 0:
            if not messagebox.askyesno("No Files Selected", "No files selected. Do you want to create an empty patch?"):
                return

        parsed_version = None
        if create_patch:
            parsed_version = vo.parse_version(patch_version)
            if not parsed_version:
                messagebox.showerror("Error", "Invalid patch version format! Expected major.minor.revision-suffix\n"
                                     "Example: 1.0.0956-W0")
                return
            vo.set_current_version(parsed_version)

        if has_cyra:
            wc_root_plan = get_wc_root(svn_path)
            cyra_plan = build_cyra_plan(
                db, wc_root_plan,
                patch_name=patch_name if create_patch else None,
                patch_number=parsed_version.revision if create_patch else None,
            )
            patch_line = f"Create patch {patch_name}" if create_patch else "No patch (no web/db files)"
            summary = (
                f"Files: {len(groups['cyra'])} Cyra, {len(groups['web'])} web, "
                f"{len(groups['db'])} database, {len(groups['other'])} other.\n\n"
                f"{patch_line}\n"
                f"Create Cyra release {cyra_plan['release_version']} "
                f"(cyra/VERSION + core/__init__.py updated, built and committed to CyraReleases SVN)\n"
                f"Link: Cyra {cyra_plan['release_version']} requires patch "
                f"{cyra_plan['link_patch_name']} ({cyra_plan['link_source']})\n\nContinue?"
            )
            if not messagebox.askyesno("Cyra release", summary):
                return
            status("Updating Cyra version files…")
            for rel in apply_cyra_version_bump(wc_root_plan, cyra_plan["release_version"], username):
                if not any(cyra_normalize_rel(f) == rel for f in selected_files):
                    selected_files.append(rel)

        if has_cyra and not create_patch:
            # Cyra only: commit the files, build + commit the release, link it
            # to the previous release's patch. No patch header/folder.
            status(f"Committing {len(selected_files)} file(s) to SVN…")
            commit_files(selected_files, unlock_files)
            result = build_and_commit_cyra_release(
                wc_root_plan, cyra_plan, username, patch_description, status_callback=status)
            record_cyra_link(db, cyra_plan)
            details = (f"Cyra {cyra_plan['release_version']} release created "
                       f"(SVN r{result['revision']}), linked to patch {cyra_plan['link_patch_name']} "
                       f"({cyra_plan['link_source']}).\nNo patch created (no web/db files).")
            log_success("Cyra Release Creation", details)
            messagebox.showinfo("Info", details)
            return

        db.conn.begin()

        patchAlreadyExists = db.check_patch_exists(patch_prefixe, patch_version.split("-")[0])
        if patchAlreadyExists:
            raise ValueError(f"Patch with prefix '{patch_prefixe}' and version '{patch_version.split('-')[0]}' already exists. "
                            "You might want to update the existing patch or use the next version.")

        os.makedirs(config.get("current_patches", "D:/cyframe/jtdev/Patches/Current"), exist_ok=True)

        status(f"Committing {len(selected_files)} file(s) to SVN…")
        commit_files(selected_files, unlock_files)
        
        
        status("Creating patch header…")
        patch_id = db.create_patch_header(patch_prefixe, patch_version, patch_description, username, 
                                        False, parsed_version.major, parsed_version.minor, parsed_version.revision)
        
        os.makedirs(patch_version_folder, exist_ok=True)
        
        application_id = db.get_application_id(patch_prefixe)

        wc_root = get_wc_root(svn_path)

        # Process files in batches for better performance
        BATCH_SIZE = 50
        folder_id_cache = {}
        total = len(selected_files)
        for i in range(0, len(selected_files), BATCH_SIZE):
            batch = selected_files[i:i + BATCH_SIZE]
            status(f"Recording file details ({min(i + BATCH_SIZE, total)}/{total})…")
            
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
                if soft_path not in folder_id_cache:
                    folder_id_cache[soft_path] = db.get_folder_id(soft_path)
                folder_id = folder_id_cache[soft_path]
                file_id = db.create_patch_detail(patch_id, fake_path, clean_path, filename, revisions.get(file, ""), folder_id)
                md5checksum = md5_checksums.get(f"{wc_root}/{file}")
                if md5checksum:
                    db.set_md5(patch_id, file_id, md5checksum)

        # Create patch files in optimized batches
        status("Copying files into patch folder…")
        create_patch_files_batch(selected_files, svn_path, patch_version_folder)
        
        # Create supporting files
        status("Writing ReadMe / MainSQL / depend…")
        create_readme_file(patch_version_folder, patch_name, username, 
                         time.strftime("%Y-%m-%d %H:%M:%S"), patch_description, selected_files)
        
        create_main_sql_file(patch_version_folder, selected_files, version_info=(parsed_version.major, parsed_version.minor, parsed_version.revision), application_id=application_id)
        
        setup_patch_folder(patch_version_folder)
        create_depend_txt(db, patch_version_folder, patch_id)
        
        status("Finalizing…")
        db.conn.commit()
        success_details = f"Patch: {patch_name}\nFiles: {len(selected_files)}\nDescription: {patch_description}"

        release_note = ""
        if cyra_plan is not None:
            # Patch is committed at this point; a release failure must not
            # roll it back. The link can be fixed on the Cyra Releases page.
            try:
                result = build_and_commit_cyra_release(
                    wc_root, cyra_plan, username, patch_description, status_callback=status)
                record_cyra_link(db, cyra_plan)
                release_note = (f"\nCyra {cyra_plan['release_version']} release built and committed "
                                f"(SVN r{result['revision']}), linked to patch {patch_name}.")
            except Exception as rel_err:
                release_note = (f"\n\nWARNING: the patch was created, but the Cyra release failed:\n{rel_err}\n"
                                "Rebuild the release manually, or link it on the Cyra Releases page.")
                log_error(f"Cyra release after patch {patch_name} failed: {rel_err}", include_stack=True)
            success_details += release_note
        log_success("Patch Creation", success_details)
        messagebox.showinfo("Info", "Patch created successfully!" + release_note)
    except Exception as e:
        try:
            if db.conn is not None:
                db.conn.rollback()
        except Exception:
            pass
        if patch_version_folder:
            cleanup_files(patch_version_folder)
        error_msg = f"Failed to create patch: {str(e)}"
        print(error_msg)
        log_error(error_msg, include_stack=True)
        messagebox.showerror("Error", error_msg)

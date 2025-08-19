import tkinter as tk
from svn_operations import lock_files, unlock_files
from version_operation import next_version
from patches_operations import get_full_patch_info, set_selected_patch, build_patch, view_files_from_patch
import os
from svn_operations import get_file_info, get_file_info_batch
from config import load_config
from tkinter import messagebox
import subprocess

def lock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[2] for item in files_listbox.selection()]
    lock_files(selected_files, files_listbox)

def unlock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[2] for item in files_listbox.selection()]
    unlock_files(selected_files, files_listbox)

def insert_next_version(application_id, patch_version_entry):
    new_version = next_version(application_id)
    if new_version:
        patch_version_entry.config(state="normal")
        patch_version_entry.delete(0, tk.END)
        patch_version_entry.insert(0, new_version)
        patch_version_entry.config(state="normal")

def deselect_all_rows(event, files_listbox):
    if not files_listbox.identify_row(event.y):  # Check if click is on an empty area
        files_listbox.selection_remove(files_listbox.selection())


def select_all_rows(event, files_listbox):
    for item in files_listbox.get_children():
        files_listbox.selection_add(item)

def check_files_is_present(files_listbox, files):
    # Create a set of existing files for O(1) lookup
    existing_files = {files_listbox.item(item, "values")[2] for item in files_listbox.get_children()}
    return any(file in existing_files for file in files)

def handle_drop(event, listbox):
    """Handle drag and drop of files/directories onto the listbox."""
    from svn_operations import get_relative_path
    
    files = listbox.tk.splitlist(event.data)
    config = load_config()
    svn_path = config.get("svn_path")
    
    if not svn_path:
        messagebox.showerror("Error", "SVN path not configured")
        return
    
    files_outside_svn = []
    files_to_process = []

    # Get SVN working copy root
    try:
        wc_root = subprocess.run(
            ["svn", "info", "--show-item", "wc-root", svn_path],
            capture_output=True,
            text=True,
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        ).stdout.strip().replace("\\", "/")
    except subprocess.SubprocessError as e:
        messagebox.showerror("Error", f"Failed to get SVN working copy root: {e}")
        return
    
    svn_relative_path = get_relative_path(svn_path)
    
    def is_file_in_svn_scope(file_path):
        """Check if a file is within the SVN scope."""
        file_relative_path = get_relative_path(file_path)
        
        # If SVN path is at root level, exclude 'Projects' directory
        if svn_relative_path == "":
            return not file_relative_path.startswith("Projects")
        
        # If SVN path is in a subdirectory, file must be within that path
        return file_relative_path.startswith(svn_relative_path)
    
    def normalize_file_path(file_path):
        """Normalize file path for SVN operations."""
        return file_path.replace("\\", "/").replace(wc_root + "/", "")
    
    def process_file(file_path):
        """Process a single file for inclusion in the patch."""
        if is_file_in_svn_scope(file_path):
            normalized_path = normalize_file_path(file_path)
            files_to_process.append(normalized_path)
        else:
            files_outside_svn.append(file_path)
    
    def process_directory(dir_path):
        """Process all files in a directory recursively."""
        try:
            for root, dirs, dir_files in os.walk(dir_path):
                for dir_file in dir_files:
                    full_path = os.path.join(root, dir_file)
                    process_file(full_path)
        except OSError as e:
            messagebox.showerror("Error", f"Failed to process directory {dir_path}: {e}")
    
    # Process dropped files and directories
    for item in files:
        if os.path.isfile(item):
            process_file(item)
        elif os.path.isdir(item):
            process_directory(item)
        else:
            files_outside_svn.append(item)  # Invalid path

    # Filter out files that already exist in the listbox
    existing_files = {listbox.item(item, "values")[2] for item in listbox.get_children()}
    new_files = [f for f in files_to_process if f not in existing_files]
    
    if not new_files and not files_outside_svn:
        messagebox.showinfo("Info", "No new files to add - all selected files are already in the list.")
        return
    
    if new_files:
        # Process all files in one batch call for better performance
        try:
            file_info_results = get_file_info_batch(new_files)
            
            # Insert files in batches to update UI periodically and avoid freezing
            BATCH_SIZE = 50
            total_files = len(new_files)
            
            for i in range(0, total_files, BATCH_SIZE):
                batch = new_files[i:i + BATCH_SIZE]
                
                for file in batch:
                    info = file_info_results.get(file, (False, "", "", ""))
                    lock_by_user, lock_owner, revision, lock_date = info
                    
                    # Determine file status
                    if lock_by_user:
                        status = 'locked'
                    elif lock_owner == "":
                        status = 'unlocked'
                    else:
                        status = f'@locked - {lock_owner}'
                    
                    listbox.insert('', 'end', values=(status, revision, file, lock_date))
                
                # Update UI periodically to show progress
                listbox.update()
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process files: {e}")
            return

    # Report files that couldn't be added
    if files_outside_svn:
        _show_files_outside_svn_error(files_outside_svn)

def _show_files_outside_svn_error(files_outside_svn):
    """Show error message for files outside SVN scope."""
    MAX_FILES_TO_SHOW = 20
    files_to_show = files_outside_svn[:MAX_FILES_TO_SHOW]
    remaining = len(files_outside_svn) - len(files_to_show)
    
    error_message = (
        "The following files are not in the SVN repository scope and will not be added to the patch:\n"
        "Your current profile may not include these files.\n\n"
    )
    error_message += "\n".join(f"• {file}" for file in files_to_show)
    
    if remaining > 0:
        error_message += f"\n\n...and {remaining} more files"
    
    messagebox.showerror("Files Outside SVN Scope", error_message)

def modify_patch(selected_patch, switch_to_modify_patch_menu):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        full_patch_info = get_full_patch_info(patch_details[0])
        if full_patch_info:
            # Always update the globally selected patch with the new selection
            set_selected_patch(full_patch_info)
            # Pass the full patch info to the modify function
            switch_to_modify_patch_menu(full_patch_info)
        else:
            messagebox.showerror("Error", f"Could not find details for patch {patch_details[0]}")
    else:
        messagebox.showwarning("No Selection", "Please select a patch to modify")

def build_existing_patch(selected_patch):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        full_patch_info = get_full_patch_info(patch_details[0])
        build_patch(full_patch_info)
        
def view_patch_files(selected_patch):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        full_patch_info = get_full_patch_info(patch_details[0])
        view_files_from_patch(full_patch_info)

def view_selected_file_native_diff(files_listbox):
    """
    View the differences between the working copy and the repository version
    of the selected file using native SVN diff tool.
    """
    selected_items = files_listbox.selection()
    if len(selected_items) != 1:
        messagebox.showwarning("Selection Error", "Please select exactly one file to view differences.")
        return
        
    # Get the file path from the selected item
    file_path = files_listbox.item(selected_items[0], "values")[2]
    from svn_operations import view_file_native_diff
    view_file_native_diff(file_path)

def remove_selected_patch(patches_listbox):
    """
    Remove the selected patch from the database.
    
    Args:
        patches_listbox: The treeview containing the patches
    """
    selected_items = patches_listbox.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select a patch to remove")
        return
    
    # Get the selected patch details
    patch_name = patches_listbox.item(selected_items[0], "values")[0]
    full_patch_info = get_full_patch_info(patch_name)
    
    if not full_patch_info:
        messagebox.showerror("Error", f"Could not find details for patch {patch_name}")
        return
    
    # Call the remove_patch function
    from patches_operations import remove_patch
    result = remove_patch(full_patch_info)
    
    # If removal was successful, remove the item from the treeview
    if result:
        patches_listbox.delete(selected_items[0])
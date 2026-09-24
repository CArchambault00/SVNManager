import tkinter as tk
from version_operation import next_version
from patches_operations import get_full_patch_info, set_selected_patch, build_patch, view_files_from_patch
import os
from config import load_config
from tkinter import messagebox
import subprocess

def lock_selected_files(files_listbox):
    from busy_ops import lock_unlock_busy

    selected_files = [files_listbox.item(item, "values")[2] for item in files_listbox.selection()]
    lock_unlock_busy(files_listbox.winfo_toplevel(), selected_files, files_listbox, lock=True)

def unlock_selected_files(files_listbox):
    from busy_ops import lock_unlock_busy

    selected_files = [files_listbox.item(item, "values")[2] for item in files_listbox.selection()]
    lock_unlock_busy(files_listbox.winfo_toplevel(), selected_files, files_listbox, lock=False)

def insert_next_version(application_id, patch_version_entry):
    new_version = next_version(application_id)
    if new_version:
        patch_version_entry.config(state="normal")
        patch_version_entry.delete(0, tk.END)
        patch_version_entry.insert(0, new_version)
        patch_version_entry.config(state="normal")

def deselect_all_rows(event, files_listbox):
    # Heading clicks must not be treated as empty-area clicks (they sort columns).
    if files_listbox.identify_region(event.x, event.y) == "heading":
        return
    if not files_listbox.identify_row(event.y):  # Check if click is on an empty area
        files_listbox.selection_remove(files_listbox.selection())


def select_all_rows(event, files_listbox):
    children = files_listbox.get_children()
    if children:
        files_listbox.selection_set(children)

def check_files_is_present(files_listbox, files):
    # Create a set of existing files for O(1) lookup
    existing_files = {files_listbox.item(item, "values")[2] for item in files_listbox.get_children()}
    return any(file in existing_files for file in files)

# Keep sync implementation for tests that call handle_drop internals via busy_ops.
def _handle_drop_sync(event, listbox):
    """Synchronous drop handler used by tests; production uses handle_drop_busy."""
    from svn_operations import get_wc_root, relative_to_wc_root, get_file_info_batch
    import os
    import subprocess

    files = listbox.tk.splitlist(event.data)
    config = load_config()
    svn_path = config.get("svn_path")

    if not svn_path:
        messagebox.showerror("Error", "SVN path not configured")
        return

    files_outside_svn = []
    files_to_process = []

    try:
        wc_root = get_wc_root(svn_path)
    except subprocess.SubprocessError as e:
        messagebox.showerror("Error", f"Failed to get SVN working copy root: {e}")
        return

    wc_root_n = wc_root.replace("\\", "/").rstrip("/")
    svn_path_n = svn_path.replace("\\", "/").rstrip("/")
    try:
        svn_relative_path = relative_to_wc_root(svn_path_n, wc_root_n)
    except ValueError:
        svn_relative_path = ""

    def is_file_in_svn_scope(file_path):
        file_n = file_path.replace("\\", "/")
        if not (file_n == wc_root_n or file_n.startswith(wc_root_n + "/")):
            return False
        file_relative_path = file_n[len(wc_root_n):].lstrip("/")
        if svn_relative_path == "":
            return not file_relative_path.startswith("Projects")
        return (
            file_relative_path == svn_relative_path
            or file_relative_path.startswith(svn_relative_path + "/")
        )

    def normalize_file_path(file_path):
        return file_path.replace("\\", "/").replace(wc_root_n + "/", "")

    def process_file(file_path):
        if is_file_in_svn_scope(file_path):
            files_to_process.append(normalize_file_path(file_path))
        else:
            files_outside_svn.append(file_path)

    for item in files:
        if os.path.isfile(item):
            process_file(item)
        elif os.path.isdir(item):
            try:
                for root, _dirs, dir_files in os.walk(item):
                    for dir_file in dir_files:
                        process_file(os.path.join(root, dir_file))
            except OSError as e:
                messagebox.showerror("Error", f"Failed to process directory {item}: {e}")
        else:
            files_outside_svn.append(item)

    existing_files = {listbox.item(item, "values")[2] for item in listbox.get_children()}
    new_files = [f for f in files_to_process if f not in existing_files]

    if not new_files and not files_outside_svn:
        messagebox.showinfo("Info", "No new files to add - all selected files are already in the list.")
        return

    if new_files:
        try:
            file_info_results = get_file_info_batch(new_files)
            BATCH_SIZE = 50
            total_files = len(new_files)
            for i in range(0, total_files, BATCH_SIZE):
                batch = new_files[i:i + BATCH_SIZE]
                for file in batch:
                    info = file_info_results.get(file, (False, "", "", ""))
                    lock_by_user, lock_owner, revision, lock_date = info
                    if lock_by_user:
                        status = 'locked'
                    elif lock_owner == "":
                        status = 'unlocked'
                    else:
                        status = f'@locked - {lock_owner}'
                    listbox.insert('', 'end', values=(status, revision, file, lock_date))
                listbox.update_idletasks()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to process files: {e}")
            return

    if files_outside_svn:
        _show_files_outside_svn_error(files_outside_svn)

def handle_drop(event, listbox):
    """Handle drag and drop of files/directories onto the listbox."""
    from busy_ops import handle_drop_busy

    handle_drop_busy(listbox.winfo_toplevel(), event, listbox)

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
        from busy_dialog import run_with_busy_dialog
        import tkinter as tk

        patch_details = selected_patch[0]
        full_patch_info = get_full_patch_info(patch_details[0])
        if not full_patch_info:
            return

        def work(set_status):
            set_status(f"Building patch {full_patch_info.get('NAME', '')}…")
            build_patch(full_patch_info)

        root = tk._default_root
        if root is not None:
            run_with_busy_dialog(root, "Building patch", work, initial_status="Preparing…")
        else:
            build_patch(full_patch_info)
        
def view_patch_files(selected_patch):
    if selected_patch:
        from busy_dialog import run_with_busy_dialog
        import tkinter as tk

        patch_details = selected_patch[0]
        full_patch_info = get_full_patch_info(patch_details[0])
        if not full_patch_info:
            return

        def work(set_status):
            set_status("Loading patch files…")
            view_files_from_patch(full_patch_info)

        root = tk._default_root
        if root is not None:
            run_with_busy_dialog(root, "Viewing patch files", work, initial_status="Loading…")
        else:
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
    from busy_ops import remove_patch_busy

    selected_items = patches_listbox.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select a patch to remove")
        return
    
    patch_name = patches_listbox.item(selected_items[0], "values")[0]
    full_patch_info = get_full_patch_info(patch_name)
    
    if not full_patch_info:
        messagebox.showerror("Error", f"Could not find details for patch {patch_name}")
        return
    
    item_id = selected_items[0]
    remove_patch_busy(
        patches_listbox.winfo_toplevel(),
        full_patch_info,
        on_success=lambda: patches_listbox.delete(item_id),
    )

def open_file_location(files_listbox):
    """
    Open the file location of the selected file in Windows File Explorer.
    
    Args:
        files_listbox: The treeview containing the files
    """
    selected_items = files_listbox.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select a file to open its location")
        return
    
    if len(selected_items) > 1:
        messagebox.showwarning("Multiple Selection", "Please select only one file to open its location")
        return
    
    # Get the file path from the selected item (assuming it's in column index 2)
    relative_file_path = files_listbox.item(selected_items[0], "values")[2]
    
    # Get the SVN path from config to build the full path
    config = load_config()
    svn_path = config.get("svn_path")
    
    if not svn_path:
        messagebox.showerror("Error", "SVN path not configured")
        return
    
    # Get SVN working copy root to build correct path
    try:
        from svn_operations import get_wc_root, resolve_wc_relative_path
        wc_root = get_wc_root(svn_path)
        relative_file_path = resolve_wc_relative_path(wc_root, relative_file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to get SVN working copy root: {e}")
        return
    
    # Build the full file path using working copy root
    full_file_path = os.path.join(wc_root, relative_file_path).replace("/", "\\")
    
    # Check if the file exists
    if not os.path.exists(full_file_path):
        messagebox.showerror("Error", f"File not found: {full_file_path}")
        return
    
    try:
        # Alternative approach: Use subprocess.Popen with proper argument handling
        import sys
        
        # Normalize the path for Windows
        normalized_path = os.path.normpath(full_file_path)
        
        # Use subprocess.Popen with list arguments to avoid shell parsing issues
        subprocess.Popen([
            'explorer.exe', 
            '/select,', 
            normalized_path
        ], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        
    except Exception as e:
        try:
            # Fallback: Just open the directory containing the file
            directory = os.path.dirname(full_file_path)
            os.startfile(directory)
        except Exception as fallback_error:
            messagebox.showerror("Error", f"Failed to open file location: {e}\nFallback also failed: {fallback_error}")
    
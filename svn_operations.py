# svn_operations.py
import subprocess
from config import load_config
from shared_operations import load_locked_files


TORTOISE_SVN = r"C:\Program Files\TortoiseSVN\bin\TortoiseProc.exe"

def lock_files(selected_files, patch_listbox, patch_listbox_patch):
    _lock_unlock_files(selected_files, patch_listbox, patch_listbox_patch, lock=True)

def unlock_files(selected_files, patch_listbox, patch_listbox_patch):
    _lock_unlock_files(selected_files, patch_listbox, patch_listbox_patch, lock=False)

def _lock_unlock_files(selected_files, patch_listbox, patch_listbox_patch, lock=True):
    config = load_config()
    username = config.get("username", "")
    svn_path = config.get("svn_path", "")
    command = "lock" if lock else "unlock"
    
    # Ensure lock message is properly formatted
    lock_message = f"Locking by {username}" if lock else f"Unlocking by {username}"
    
    # Ensure selected files are correctly formatted in the command
    files_str = '*'.join(selected_files)
    
    # Prepare the command arguments
    args = [
        TORTOISE_SVN, f"/command:{command}",
        f"/path:{files_str}", "/closeonend:1", f"/lockmessage:{lock_message}"
    ]
    
    # Run the subprocess command
    subprocess.run(args, cwd=svn_path, shell=True)

    # Update the list of locked files
    locked_files = load_locked_files()
    if lock:
        locked_files.extend(selected_files)
    else:
        locked_files = [file for file in locked_files if file not in selected_files]
    
    refresh_locked_files(patch_listbox)
    refresh_locked_files(patch_listbox_patch)

def refresh_locked_files(files_listbox):
    svn_path = load_config().get("svn_path")
    svn_path = svn_path.replace("/", "\\")
    files_listbox.delete(*files_listbox.get_children())
    for file in load_locked_files():
        file_name = file.split(svn_path + "\\")[1]
        files_listbox.insert("", "end", values=("locked", file_name), tags=("unchecked",))

def commit_files(selected_files):
    config = load_config()
    username = config.get("username", "")
    args = [TORTOISE_SVN, "/command:commit", f"/path:{'*'.join(selected_files)}", "/closeonend:1", f"/logmsg:{username}"]
    subprocess.run(args, shell=True)
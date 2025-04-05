import hashlib
from tkinter import messagebox
import shutil
import os

def get_md5_checksum(file_path):
    """Returns the MD5 checksum of a given file."""
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):  # Read in chunks of 4KB
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except FileNotFoundError:
        messagebox.showerror("Error", f"File not found: {file_path}")
        return None
    
def cleanup_files(patch_version_folder):
    if os.path.exists(patch_version_folder):
        shutil.rmtree(patch_version_folder)

def create_depend_txt(db_handler, patch_version_folder, patch_id):
    patch_files = db_handler.get_patch_file_list(patch_id)
    depend_content = ""
    for file_info in patch_files:
        folder_path = file_info['PATH']
        file_name = file_info['NAME']
        current_version = file_info['VERSION']
        
        # Get previous versions of this file from other patches
        previous_versions = db_handler.get_folder_patch_list(folder_path)
        
        # Filter for this specific file with versions < current version
        previous_versions = [pv for pv in previous_versions 
                           if pv['NAME'] == file_name 
                           and pv['VERSION'] < current_version 
                           and pv['DELETED_YN'] == 'N']
        
        for pv in previous_versions:
            # Extract build number from patch name
            build_number = extract_build_number(pv['PATCH_NAME'])
            if build_number != "'ERROR',3,0,0":
                depend_content += f"{build_number}\n"
                # Original VB6 code also included MD5 checksum in comments:
                # depend_content += f"{build_number},'{pv['MD5_CHECKSUM']}',{pv['FILE_ID']}\n"
    print(depend_content)
    if depend_content:
        with open(patch_version_folder + "/depend.txt", 'w') as f:
            f.write(depend_content)

def extract_build_number(patch_name):
    """
    Replicates the ExtractBuildNumber function from VB6 code.
    Converts patch names like "J2.1.1234" to "'CORE',2,1,1234"
    """
    if not patch_name:
        return "'ERROR',3,0,0"
    
    # Remove any suffix after hyphen
    if '-' in patch_name:
        patch_name = patch_name.split('-')[0]
    
    parts = patch_name.split('.')
    
    # Determine application code
    first_char = patch_name[0].upper()
    if first_char == 'V':
        app_code = 'BT'
        version_part = patch_name[1:]
    elif first_char in ['J', 'C']:
        app_code = 'CORE'
        version_part = patch_name[1:]
    elif first_char == 'S':
        app_code = 'CORE_SVN'
    elif first_char == 'E':
        app_code = 'EXT'
        version_part = patch_name[1:]
    elif first_char == 'D':
        app_code = 'DIE'
        version_part = patch_name[1:]
    else:
        if patch_name[0].isdigit():
            app_code = 'CORE'
            version_part = patch_name
        else:
            app_code = patch_name
            version_part = '3'
    
    # Split version components
    version_parts = version_part.split('.')
    
    if len(version_parts) == 1:
        # Only major version
        major = version_parts[0]
        minor = '0'
        revision = '0'
    elif len(version_parts) == 2:
        # Major and minor
        major = version_parts[0]
        minor = version_parts[1]
        revision = '0'
    else:
        # All three components
        major = version_parts[0]
        minor = version_parts[1]
        revision = '.'.join(version_parts[2:])  # In case revision has dots
    
    # Clean up revision if it has letters
    if revision and not revision[-1].isdigit():
        revision = revision[:-1]
    
    return f"'{app_code}',{major},{minor},{revision}"
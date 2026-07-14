import hashlib
from tkinter import messagebox
import shutil
import os
import tempfile
from svn_operations import copy_InstallConfig, copy_RunScript, copy_UnderTestInstallConfig, get_file_revision, get_file_revision_batch, get_file_head_revision, get_file_head_revision_batch, get_relative_path
from db_handler import dbClass
import time
from config import log_error, load_config

# Auto-generated / scaffolding files at the patch folder root — always rebuilt.
GENERATED_PATCH_ROOT_FILES = frozenset({
    "ReadMe.txt",
    "MainSQL.sql",
    "depend.txt",
    "InstallConfig.exe",
    "RunScript.bat",
    "UNDERTEST_InstallConfig.exe",
})

def get_md5_checksum(file_path):
    """Returns the MD5 checksum of a given file."""
    md5_hash = hashlib.md5()
    
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):  # Read in chunks of 4KB
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    except Exception as e:
        raise Exception(f"Error calculating MD5 checksum for {file_path}: {e}")

def map_svn_file_to_patch_dest(file_path, svn_path=None):
    """Map an SVN-relative path to its destination path inside the patch folder."""
    file_path_no_svn = file_path.replace("\\", "/")
    if svn_path:
        rel = get_relative_path(svn_path)
        if rel and file_path_no_svn.startswith(rel):
            file_path_no_svn = file_path_no_svn.replace(rel, "", 1).lstrip("/")

    if file_path_no_svn.startswith("webpage"):
        return file_path_no_svn.replace("webpage", "Web", 1)
    if file_path_no_svn.startswith("Database"):
        return file_path_no_svn.replace("Database", "DB", 1).replace("StoredProcedures", "SP")
    return None

def map_db_file_to_patch_dest(file_info):
    """Map a get_patch_file_list_new row to its destination path inside the patch folder."""
    path = file_info["PATH"].replace("\\", "/")
    svn_path = (file_info.get("SVN_PATH") or "").replace("\\", "/")

    if file_info["FOLDER_TYPE"] == '1':
        if svn_path:
            path = path.replace(svn_path, "Web")
        path = path.replace("webpage", "Web")
    else:
        if svn_path:
            path = path.replace(svn_path, "DB")
        path = path.replace("StoredProcedures", "SP").replace("Database", "DB")
    return path

def get_managed_dest_paths(files, svn_path=None):
    """Return the set of relative destination paths managed by the patch build."""
    managed = set()
    for file in files:
        if isinstance(file, dict):
            dest = map_db_file_to_patch_dest(file)
        else:
            dest = map_svn_file_to_patch_dest(file, svn_path)
        if dest:
            managed.add(dest.replace("\\", "/"))
    return managed

def backup_extra_patch_files(patch_version_folder, managed_dest_paths):
    """
    Back up files that were manually added to the patch folder (not from
    locked/unlocked SVN files and not auto-generated scaffolding).

    Returns a temp directory path containing the extras, or None if there are none.
    """
    if not patch_version_folder or not os.path.exists(patch_version_folder):
        return None

    managed = {p.replace("\\", "/") for p in managed_dest_paths}
    temp_dir = None

    for root, _dirs, files in os.walk(patch_version_folder):
        for name in files:
            abs_path = os.path.join(root, name)
            rel_path = os.path.relpath(abs_path, patch_version_folder).replace("\\", "/")

            # Skip auto-generated root scaffolding
            if "/" not in rel_path and name in GENERATED_PATCH_ROOT_FILES:
                continue
            # Skip files that come from the patch's managed SVN file list
            if rel_path in managed:
                continue

            if temp_dir is None:
                temp_dir = tempfile.mkdtemp(prefix="patch_extras_")

            dest = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(abs_path, dest)

    return temp_dir

def restore_extra_patch_files(temp_dir, patch_version_folder):
    """Restore manually-added patch files from a backup temp directory."""
    if not temp_dir or not os.path.exists(temp_dir):
        return

    try:
        for root, _dirs, files in os.walk(temp_dir):
            for name in files:
                abs_path = os.path.join(root, name)
                rel_path = os.path.relpath(abs_path, temp_dir)
                dest = os.path.join(patch_version_folder, rel_path)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(abs_path, dest)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def cleanup_files(patch_version_folder):
    """Clean up patch files with retry logic and proper error handling."""
    if not os.path.exists(patch_version_folder):
        return
        
    def handle_error(func, path, exc_info):
        """Error handler for shutil.rmtree."""
        import stat
        import time
        
        # If permission error, try to make file writable and retry
        if isinstance(exc_info[1], PermissionError):
            try:
                # Make file writable
                os.chmod(path, stat.S_IWRITE)
                # Wait a moment
                time.sleep(0.1)
                # Try again
                func(path)
            except Exception as e:
                print(f"Warning: Could not remove {path}: {e}")
                log_error(f"Warning: Could not remove {path}: {e}")
        else:
            print(f"Warning: Could not remove {path}: {exc_info[1]}")
            log_error(f"Warning: Could not remove {path}: {exc_info[1]}")
    
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    for attempt in range(max_retries):
        try:
            shutil.rmtree(patch_version_folder, onerror=handle_error)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1}/{max_retries} cleaning up {patch_version_folder}: {e}")
                log_error(f"Retry {attempt + 1}/{max_retries} cleaning up {patch_version_folder}: {e}")
                time.sleep(retry_delay)
            else:
                print(f"Warning: Could not fully clean up {patch_version_folder}: {e}")
                log_error(f"Warning: Could not fully clean up {patch_version_folder}: {e}")

def create_depend_txt(db_handler, patch_version_folder, patch_id):
    try:
        patch_files = db_handler.get_patch_file_list_new(patch_id)
        depend_content = set()  # Use a set to avoid duplicates
        
        for file_info in patch_files:
            folder_path = ""

            folder_path = file_info['PATH'].replace(file_info['NAME'], "")

            file_name = file_info['NAME']
            current_version = file_info.get('VERSION')
            if current_version is None:
                continue
            # Get previous versions of this file from other patches
            previous_versions = db_handler.get_folder_patch_list_new(folder_path)
            # Filter for this specific file with versions < current version
            for pv in previous_versions:
                if (pv['NAME'] == file_name and 
                    pv['DELETED_YN'] == 'N' and 
                    pv.get('VERSION') is not None and 
                    current_version is not None and
                    float(pv['VERSION']) < float(current_version)):
                    
                    # Extract build number from patch name
                    build_number = extract_build_number(pv['PATCH_NAME'])
                    if build_number != "'ERROR',3,0,0":
                        depend_content.add(build_number)
        
        if depend_content:
            with open(os.path.join(patch_version_folder, "depend.txt"), 'w') as f:
                f.write('\n'.join(sorted(depend_content)))
                
    except Exception as e:
        raise Exception(f"Error creating depend.txt: {e}")

def extract_build_number(patch_name):
    """
    Replicates the ExtractBuildNumber function from VB6 code.
    Converts patch names like "J2.1.1234" to "'CORE',2,1,1234"
    """
    db = dbClass()
    try:
        if not patch_name:
            return "'ERROR',0,0,0"
        
        # Remove any suffix after hyphen
        if '-' in patch_name:
            patch_name = patch_name.split('-')[0]
        
        # Determine application code
        prefix = patch_name[0].upper()
        application_id = db.get_application_id(prefix)
        version_part = patch_name[1:]

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
        
        # Clean up revision if it has prefixes
        if revision and not revision[-1].isdigit():
            revision = revision[:-1]
        
        return f"'{application_id}',{major},{minor},{revision}"
    except Exception as e:
        raise Exception(f"Error extracting build number from {patch_name}: {e}")

def write_sql_commands(sql_file, file_path, schema):
    """Write SQL commands to execute a script file."""
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

def create_patch_files(file, svn_path, patch_version_folder):
    """Create patch files in the appropriate locations."""
    try:
        file_path_no_svn = file
        if file_path_no_svn.startswith("webpage"):
            dest_file = file_path_no_svn.replace("webpage", "Web")
            dest_file = os.path.join(patch_version_folder, dest_file)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            file_location = f"{svn_path}/{file_path_no_svn}"
            shutil.copy2(file_location, dest_file)
        elif file_path_no_svn.startswith("Database"):
            sql_path = file_path_no_svn.replace("Database", "DB")
            sql_path = sql_path.replace("StoredProcedures", "SP")
            dest_file = os.path.join(patch_version_folder, sql_path)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            file_location = f"{svn_path}/{file_path_no_svn}"
            shutil.copy2(file_location, dest_file)
    except Exception as e:
        raise Exception(f"Error creating patch files for {file}: {e}")

def create_readme_file(patch_version_folder, patch_name, username, creation_date, patch_description, files):
    """Create a ReadMe.txt file with patch information."""
    try:
        # Pre-process files to avoid multiple iterations
        webpage_files = []
        database_files = []
        svn_path = load_config().get("svn_path", "")
        for file in files:
            if isinstance(file, dict):
                # Files from database already have their versions
                if file["FOLDER_TYPE"] == '1':
                    webpage_files.append(f"{file["PATH"]} ({file['VERSION']})")
                else:
                    database_files.append(f"{file["PATH"]} ({file['VERSION']})")
            else:
                revision = get_file_head_revision(file)
                filePathWithoutProjects = file

                if get_relative_path(svn_path) != "" and filePathWithoutProjects.startswith(get_relative_path(svn_path)):
                    filePathWithoutProjects = filePathWithoutProjects.replace(get_relative_path(svn_path), "")[1:]

                if filePathWithoutProjects.startswith("webpage"):
                    webpage_files.append(f"{file} ({revision})")
                else:
                    database_files.append(f"{file} ({revision})")

        # Write everything in one go
        content = [
            f"Patch {patch_name}",
            username,
            creation_date,
            "",
            patch_description,
            "\nPatch Content:\n",
            "\nWebpage Files:",
            *webpage_files,
            "\nDatabase Files:",
            *database_files
        ]
        
        with open(os.path.join(patch_version_folder, "ReadMe.txt"), "w") as readme:
            readme.write("\n".join(content))
            
    except Exception as e:
        raise Exception(f"Error creating ReadMe.txt: {e}")

def create_main_sql_file(patch_version_folder, files, patch_name=None, version_info=None, application_id=None):
    """Create MainSQL.sql file with SQL commands."""
    try:
        # Start with header commands
        sql_commands = ["prompt &&HOST", "prompt &&PERSON", "set echo on\n"]
        
        # Group files by schema
        schema_files = {}

        svn_path = load_config().get("svn_path", "")

        # Process and organize files by schema
        for file in files:
            if isinstance(file, dict):
                filePathWithoutProjects = file["PATH"]
                filePathWithoutProjects = filePathWithoutProjects.replace(file["SVN_PATH"], "")
            elif isinstance(file, str):
                filePathWithoutProjects = file
                if get_relative_path(svn_path) != "" and isinstance(filePathWithoutProjects, str) and filePathWithoutProjects.startswith(get_relative_path(svn_path)):
                    filePathWithoutProjects = filePathWithoutProjects.replace(get_relative_path(svn_path), "")[1:]
            

            if isinstance(file, dict) and file["FOLDER_TYPE"] == '2':
                filePathWithoutProjects = "Database" + filePathWithoutProjects
                schema = filePathWithoutProjects.split("/")[1]
                file_path = filePathWithoutProjects.replace("Database", "DB").replace("StoredProcedures", "SP")
                if schema not in schema_files:
                    schema_files[schema] = []
                schema_files[schema].append(file_path)
            elif isinstance(file, str) and filePathWithoutProjects.startswith("Database"):
                file_path = filePathWithoutProjects.replace("Database", "DB").replace("StoredProcedures", "SP")
                schema = filePathWithoutProjects.split("/")[1]
                if schema not in schema_files:
                    schema_files[schema] = []
                schema_files[schema].append(file_path)
        
        # Generate SQL commands - group PKS and PKB files together per schema, but execute all PKS before PKB within each schema
        for schema, paths in schema_files.items():
            # Filter files by type (case-insensitive)
            pks_files = [path for path in paths if path.upper().endswith('.PKS')]
            pkb_files = [path for path in paths if path.upper().endswith('.PKB')]
            other_files = [path for path in paths if not path.upper().endswith('.PKS') and not path.upper().endswith('.PKB')]
            
            # Execute PKS and PKB files together for this schema (if any exist)
            if pks_files or pkb_files:
                # Add schema connection block for PKS and PKB files
                sql_commands.extend([
                    "set scan on",
                    f"connect {schema}/{schema}@&&HOST",
                    "set scan off",
                    "set echo off"
                ])
                
                # Add all PKS files first
                for file_path in pks_files:
                    sql_commands.extend([
                        f'prompt Loading "{file_path}" ...',
                        f'@@"{file_path}"'
                    ])
                
                # Add all PKB files after PKS files
                for file_path in pkb_files:
                    sql_commands.extend([
                        f'prompt Loading "{file_path}" ...',
                        f'@@"{file_path}"'
                    ])
                
                # Add show error and end the schema block
                sql_commands.extend([
                    "show error",
                    "set echo on\n"
                ])
            
            # Execute other SQL files for this schema (if any exist)
            if other_files:
                # Add schema connection block for other files
                sql_commands.extend([
                    "set scan on",
                    f"connect {schema}/{schema}@&&HOST",
                    "set scan off",
                    "set echo off"
                ])
                
                # Add each other file in this schema block
                for file_path in other_files:
                    sql_commands.extend([
                        f'prompt Loading "{file_path}" ...',
                        f'@@"{file_path}"'
                    ])
                
                # Add show error and end the schema block
                sql_commands.extend([
                    "show error",
                    "set echo on\n"
                ])
        
        # Add version control commands
        sql_commands.extend([
            "set scan on",
            "connect CMATC/CMATC@&&HOST"
        ])
        
        if version_info:
            major, minor, revision = version_info
            # Ensure revision is always 4 digits, zero-padded
            revision = str(revision).zfill(4)
            sql_commands.append(
                f"CALL CMATC.PKG_VERSION_CONTROL.SETCURRENTVERSION('{application_id}',{major},{minor},{revision},'&&PERSON');"
            )
        elif patch_name:
            version = extract_build_number(patch_name)
            application_id, major, minor, revision = version.split(",")
            revision = str(revision).zfill(4)
            sql_commands.append(
                f"CALL CMATC.PKG_VERSION_CONTROL.SETCURRENTVERSION({application_id},{major},{minor},{revision},'&&PERSON');"
            )
        
        sql_commands.extend(["commit;", "\nexit;"])
        
        # Write commands to file
        with open(os.path.join(patch_version_folder, "MainSQL.sql"), "w") as main_sql:
            main_sql.write("\n".join(sql_commands))
            
    except Exception as e:
        raise Exception(f"Error creating MainSQL.sql: {e}")

def _generate_sql_commands(file_path, schema):
    """Helper function to generate SQL commands for a file."""
    return [
        "set scan on",
        f"connect {schema}/{schema}@&&HOST" if schema else "#WARNING connect schema/schema@&&HOST",
        "set scan off",
        "set echo off",
        f'prompt Loading "{file_path}" ...',
        f'@@"{file_path}"',
        "show error",
        "set echo on\n"
    ]

def setup_patch_folder(patch_version_folder):
    """Set up the patch folder with required files."""
    try:
        copy_InstallConfig(patch_version_folder)
        copy_RunScript(patch_version_folder)
        copy_UnderTestInstallConfig(patch_version_folder)
    except Exception as e:
        raise e

def get_md5_checksum_batch(files):
    """Returns MD5 checksums for multiple files in a batch."""
    results = {}
    for file_path in files:
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            results[file_path] = md5_hash.hexdigest()
        except Exception as e:
            results[file_path] = None
            print(f"Error calculating MD5 for {file_path}: {e}")
            log_error(f"Error calculating MD5 for {file_path}: {e}")
    return results

def create_patch_files_batch(files, svn_path, patch_version_folder):
    """Create patch files in batches with proper error handling."""
    web_files = []
    db_files = []
    
    # First, categorize files
    for file in files:
        file_path_no_svn = file
        if get_relative_path(svn_path) != "" and file_path_no_svn.startswith(get_relative_path(svn_path)):
            file_path_no_svn = file_path_no_svn.replace(get_relative_path(svn_path), "")[1:]
        if file_path_no_svn.startswith("webpage"):
            web_files.append((
                file_path_no_svn,
                file_path_no_svn.replace("webpage", "Web"),
                f"{svn_path}/{file_path_no_svn}"
            ))
        elif file_path_no_svn.startswith("Database"):
            sql_path = file_path_no_svn.replace("Database", "DB").replace("StoredProcedures", "SP")
            db_files.append((
                file_path_no_svn,
                sql_path,
                f"{svn_path}/{file_path_no_svn}"
            ))
    # Create directories with error handling
    directories = set()
    for _, dest_path, _ in web_files + db_files:
        directories.add(os.path.dirname(os.path.join(patch_version_folder, dest_path)))
    
    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            # Verify write permissions
            test_file = os.path.join(directory, ".write_test")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                raise PermissionError(f"No write permission in directory: {directory}")
        except Exception as e:
            raise Exception(f"Failed to create/verify directory {directory}: {e}")

    # Copy files with retries
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    for file_info in web_files + db_files:
        org_path, dest_path, src_location = file_info
        dest_file = os.path.join(patch_version_folder, dest_path)
        
        for attempt in range(max_retries):
            try:
                # Ensure destination directory exists and is writable
                dest_dir = os.path.dirname(dest_file)
                if not os.path.exists(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                
                # If file exists, ensure it's writable
                if os.path.exists(dest_file):
                    os.chmod(dest_file, 0o666)
                
                # Copy the file
                shutil.copy2(src_location, dest_file)
                break
            except PermissionError as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Permission denied accessing {dest_file} after {max_retries} attempts")
                time.sleep(retry_delay)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to copy {org_path} to {dest_file}: {e}")
                time.sleep(retry_delay)
import hashlib
from tkinter import messagebox
import shutil
import os
from svn_operations import copy_InstallConfig, copy_RunScript, copy_UnderTestInstallConfig, get_file_revision, get_file_revision_batch, get_file_head_revision, get_file_head_revision_batch
from db_handler import dbClass
import time

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
        else:
            print(f"Warning: Could not remove {path}: {exc_info[1]}")
    
    max_retries = 3
    retry_delay = 0.5  # seconds
    
    for attempt in range(max_retries):
        try:
            shutil.rmtree(patch_version_folder, onerror=handle_error)
            break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Retry {attempt + 1}/{max_retries} cleaning up {patch_version_folder}: {e}")
                time.sleep(retry_delay)
            else:
                print(f"Warning: Could not fully clean up {patch_version_folder}: {e}")

def create_depend_txt(db_handler, patch_version_folder, patch_id):
    try:
        patch_files = db_handler.get_patch_file_list(patch_id)
        depend_content = set()  # Use a set to avoid duplicates
        
        for file_info in patch_files:
            folder_path = ""

            if file_info['FOLDER_TYPE'] == '1':
                folder_path = "$/Projects/SVN/webpage" + file_info['PATH']
            elif file_info['FOLDER_TYPE'] == '2':
                folder_path = "$/Projects/SVN/Database" + file_info['PATH']

            file_name = file_info['NAME']
            current_version = file_info.get('VERSION')
            if current_version is None:
                continue
                
            # Get previous versions of this file from other patches
            previous_versions = db_handler.get_folder_patch_list(folder_path)
            
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
        
        for file in files:
            if isinstance(file, dict):
                # Files from database already have their versions
                if file["FOLDER_TYPE"] == '1':
                    webpage_files.append(f"webpage{file['PATH']} ({file['VERSION']})")
                else:
                    database_files.append(f"Database{file['PATH']} ({file['VERSION']})")
            else:
                # For string file paths, get the HEAD revision
                revision = get_file_head_revision(file)
                if file.startswith("webpage"):
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
        
        # Process and organize files by schema
        for file in files:
            if isinstance(file, dict) and file["FOLDER_TYPE"] == '2':
                schema = file["PATH"].split("/")[1]
                file_path = 'DB' + file["PATH"].replace("Database", "DB").replace("StoredProcedures", "SP")
                if schema not in schema_files:
                    schema_files[schema] = []
                schema_files[schema].append(file_path)
            elif isinstance(file, str) and file.startswith("Database"):
                file_path = file.replace("Database", "DB").replace("StoredProcedures", "SP")
                schema = file.split("/")[1]
                if schema not in schema_files:
                    schema_files[schema] = []
                schema_files[schema].append(file_path)
        
        # Generate SQL commands for each schema
        for schema, paths in schema_files.items():
            # Sort files to ensure PKS before PKB
            paths.sort(key=lambda x: 0 if x.endswith('.PKS') else (1 if x.endswith('.PKB') else 2))
            
            # Add schema connection block
            sql_commands.extend([
                "set scan on",
                f"connect {schema}/{schema}@&&HOST",
                "set scan off",
                "set echo off"
            ])
            
            # Add each file in this schema block
            for file_path in paths:
                sql_commands.extend([
                    f'prompt Loading "{file_path}" ...',
                    f'@@"{file_path}"',
                    "show error"
                ])
            
            # End the schema block
            sql_commands.append("set echo on\n")
        
        # Add version control commands
        sql_commands.extend([
            "set scan on",
            "connect CMATC/CMATC@&&HOST"
        ])
        
        if version_info:
            major, minor, revision = version_info
            sql_commands.append(
                f"CALL CMATC.PKG_VERSION_CONTROL.SETCURRENTVERSION('{application_id}',{major},{minor},{revision},'&&PERSON');"
            )
        elif patch_name:
            version = extract_build_number(patch_name)
            application_id, major, minor, revision = version.split(",")
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
    return results

def create_patch_files_batch(files, svn_path, patch_version_folder):
    """Create patch files in batches to optimize I/O operations."""
    web_files = []
    db_files = []
    
    # First, categorize files
    for file in files:
        file_path_no_svn = file
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

    # Create directories in bulk
    directories = set()
    for _, dest_path, _ in web_files + db_files:
        directories.add(os.path.dirname(os.path.join(patch_version_folder, dest_path)))
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # Copy files in batches
    for file_info in web_files + db_files:
        try:
            _, dest_path, src_location = file_info
            dest_file = os.path.join(patch_version_folder, dest_path)
            shutil.copy2(src_location, dest_file)
        except Exception as e:
            raise Exception(f"Error creating patch files for {file_info[0]}: {e}")
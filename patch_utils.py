import hashlib
from tkinter import messagebox
import shutil
import os
from svn_operations import copy_InstallConfig, copy_RunScript, copy_UnderTestInstallConfig, get_file_revision
from db_handler import dbClass

PATCH_DIR = "D:/cyframe/jtdev/Patches/Current"

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
    if os.path.exists(patch_version_folder):
        shutil.rmtree(patch_version_folder)

def create_depend_txt(db_handler, patch_version_folder, patch_id):
    try:
        patch_files = db_handler.get_patch_file_list(patch_id)
        depend_content = ""
        for file_info in patch_files:
            folder_path = ""

            if file_info['FOLDER_TYPE'] == '1':
                folder_path = "$/Projects/SVN/webpage" + file_info['PATH']
            elif file_info['FOLDER_TYPE'] == '2':
                folder_path = "$/Projects/SVN/Database" + file_info['PATH']

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
        if depend_content:
            with open(patch_version_folder + "/depend.txt", 'w') as f:
                f.write(depend_content)
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
        
        # Clean up revision if it has letters
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
        with open(os.path.join(patch_version_folder, "ReadMe.txt"), "w") as readme:
            readme.write(f"Patch {patch_name}\n")
            readme.write(f"{username}\n")
            readme.write(f"{creation_date}\n\n")
            readme.write(patch_description)
            readme.write("\n\nPatch Content:\n\n")
            
            webpage_files = [file for file in files if isinstance(file, dict) and file["FOLDER_TYPE"] == '1' or 
                            isinstance(file, str) and file.startswith("webpage")]
            database_files = [file for file in files if isinstance(file, dict) and file["FOLDER_TYPE"] == '2' or 
                            isinstance(file, str) and not file.startswith("webpage")]
            
            readme.write("Webpage Files:\n")
            for file in webpage_files:
                if isinstance(file, dict):
                    readme.write(f"webpage{file['PATH']} ({file['VERSION']})\n")
                else:
                    readme.write(f"{file} ({get_file_revision(file)})\n")
            
            readme.write("\nDatabase Files:\n")
            for file in database_files:
                if isinstance(file, dict):
                    readme.write(f"Database{file['PATH']} ({file['VERSION']})\n")
                else:
                    readme.write(f"{file} ({get_file_revision(file)})\n")
    except Exception as e:
        raise Exception(f"Error creating ReadMe.txt: {e}")

def create_main_sql_file(patch_version_folder, files, patch_name=None, version_info=None, application_id=None):
    """Create MainSQL.sql file with SQL commands."""
    try:
        with open(os.path.join(patch_version_folder, "MainSQL.sql"), "w") as main_sql:
            main_sql.write("prompt &&HOST\n")
            main_sql.write("prompt &&PERSON\n")
            main_sql.write("set echo on\n\n")
            
            for file in files:
                if isinstance(file, dict) and file["FOLDER_TYPE"] == '2':
                    schema = file["PATH"].split("/")[1]
                    file_path = 'DB' + file["PATH"].replace("Database", "DB").replace("StoredProcedures", "SP")
                    write_sql_commands(main_sql, file_path, schema)
                elif isinstance(file, str) and file.startswith("Database"):
                    file_path = file.replace("Database", "DB")
                    file_path = file_path.replace("StoredProcedures", "SP")
                    schema = file.split("/")[1]
                    write_sql_commands(main_sql, file_path, schema)
            
            main_sql.write("set echo on\n")
            main_sql.write("connect CMATC/CMATC@&&HOST\n")
            
            if version_info:
                major, minor, revision = version_info
                main_sql.write(f"CALL CMATC.PKG_VERSION_CONTROL.SETCURRENTVERSION('{application_id}',{major},{minor},{revision},'&&PERSON');\n")
            elif patch_name:
                version = extract_build_number(patch_name)
                application_id, major, minor, revision = version.split(",") # Application_id is already in the format 'APP_ID'
                main_sql.write(f"CALL CMATC.PKG_VERSION_CONTROL.SETCURRENTVERSION({application_id},{major},{minor},{revision},'&&PERSON');\n")
            
            main_sql.write("commit;\n\nexit;\n")
    except Exception as e:
        raise Exception(f"Error creating MainSQL.sql: {e}")

def setup_patch_folder(patch_version_folder):
    """Set up the patch folder with required files."""
    try:
        copy_InstallConfig(patch_version_folder)
        copy_RunScript(patch_version_folder)
        copy_UnderTestInstallConfig(patch_version_folder)
    except Exception as e:
        raise e
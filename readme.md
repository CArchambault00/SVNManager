# SVN Manager

## Purpose

The SVN Manager application is a graphical user interface (GUI) tool designed to simplify the management of SVN (Subversion) repositories. It provides functionalities to lock and unlock files, generate patches, and manage SVN configurations. The application is built using Python and Tkinter for the GUI, and it integrates with TortoiseSVN for SVN operations.

## Features

- **Lock/Unlock Files**: Lock or unlock selected files in the SVN repository.
- **Generate Patches**: Create patches for selected files and organize them in a specified directory.
- **Manage SVN Configurations**: Set and save SVN repository paths and usernames.
- **Drag-and-Drop Support**: Easily add files to the list using drag-and-drop functionality.
- **Version Management**: Automatically generate the next version for patches.

## How It Works

### Setup

1. **Install Dependencies**:
   - Ensure you have Python installed.
   - Install the required Python packages:
     ```sh
     pip install tkinterdnd2 oracledb
     ```

2. **Configure TortoiseSVN**:
   - Make sure TortoiseSVN is installed on your system.
   - Update the `TORTOISE_SVN` path in the code if necessary.

### Running the Application

1. **Start the Application**:
   - Run the [app.py](http://_vscodecontentref_/0) file:
     ```sh
     python app.py
     ```

2. **Main Window**:
   - The main window provides buttons to switch between different menus: Lock/Unlock Menu, Patch Menu, and Patches Menu.

### Lock/Unlock Menu

1. **Select SVN Folder**:
   - Click the "Select SVN Folder" button to choose the SVN repository folder.

2. **Set Username**:
   - Enter your SVN username and click "Save".

3. **Lock/Unlock Files**:
   - Use the "Lock All", "Unlock All", "Lock Selected", and "Unlock Selected" buttons to manage file locks.
   - Refresh the list of locked files using the "Refresh lock files" button.

### Patch Menu

1. **Select Files**:
   - Drag and drop files into the listbox or use the "Select Files" button to add files.

2. **Generate Patch**:
   - Enter the patch version and click "Generate Patch" to create a patch for the selected files.

3. **Next Version**:
   - Click the "Next Version" button to automatically generate the next patch version.

### Patches Menu

- This menu is reserved for future enhancements related to managing existing patches.

## Configuration Files

- **`svn_config.json`**: Stores the SVN repository path and username.
- **`locked_files.json`**: Stores the list of locked files.

## File Structure

- [app.py](http://_vscodecontentref_/1): Main application file.
- [config.py](http://_vscodecontentref_/2): Handles loading and saving of configuration data.
- [shared_operations.py](http://_vscodecontentref_/3): Contains shared operations like loading locked files.
- [file_operations.py](http://_vscodecontentref_/4): Handles file operations related to patch generation.
- [svn_operations.py](http://_vscodecontentref_/5): Manages SVN operations like locking and unlocking files.
- [version_operation.py](http://_vscodecontentref_/6): Manages versioning for patches.
- [BAK.app.py](http://_vscodecontentref_/7): Backup of the main application file.
- [get_locked_files.sh](http://_vscodecontentref_/8): Shell script to get locked files from the SVN repository.

## Notes

- Ensure the [svn_config.json](http://_vscodecontentref_/9) file is included in the [.gitignore](http://_vscodecontentref_/10) to avoid committing sensitive information.
- The application assumes the presence of TortoiseSVN and Oracle database client for certain operations. Adjust paths and configurations as needed.
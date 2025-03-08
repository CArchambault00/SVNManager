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
   - Ensure you have `Python` installed.
   - Install the required Python packages:
     ```sh
     pip install tkinterdnd2 oracledb
     ```

2. **Configure TortoiseSVN**:
   - Download TurtoiseSVN [Download](https://tortoisesvn.net/)
   - Make sure TortoiseSVN is installed on your system.
   - Remember where you install `TortoiseSVN` for later

3. **Configure Oracle Instant Client**:
   - Unzip [`instantclient-basic-windows.x64-12.1.0.2.0.zip`]
   - Copy the folder `instantclient_12_1` anywhere like `D:\app\product\instantclient_12_1`
   - Download and install the Oracle Instant Client 12.1.0. 
   - [Instant Client Download Page](https://www.oracle.com/ca-en/database/technologies/instant-client/winx64-64-downloads.html#license-lightbox)
   - Remember where you install `instantclient_12_1` for later

### Running the Application

1. **Start the Application**:
   - Run the [app.py](./app.py) file:
     ```sh
     python app.py
     ```
   - OR run the executable file [SVNManager.exe](./SVNManager.exe)

2. **Configure the config for the app**
   - Red button and square will appear if `svn_path`, `username` and `instant_client` isn't define
   - `svn_path` click on the red button and give the correct path to your checkouted repository
   - `instant_client` click on the red button and give the correct path to instant client
   - `username` simply type you username and click **SAVE**!!!

3. **Main Window**:
   - The main window provides buttons to switch between different menus: Lock/Unlock Menu, Patch Menu, Patches Menu, Modify Patch.

### Landing Page / *Lock/Unlock Menu*
1. **Lock/Unlock Files**:
   
   - Refresh the list of locked files using the "Refresh lock files" button.

   - Drag and drop files into the files listbox.

   - Use the "Lock All", "Unlock All", "Lock Selected", and "Unlock Selected" buttons to manage file locks.

   - `CTRL+A` select every files

   - `Click on nothing` Deselect all files
### Patch Menu

1. **Select Files**:
   - ***ONLY LOCKED FILES UNDER YOUR NAME WILL APPEAR***

   - `CTRL+A` select every files
   
   - `Click one by one` to select specific file
   
   - `Click on nothing` Deselect all files

2. **Next Version**:
   - Click the "Next Version" button to automatically generate the next patch version.

   - `PATCH USAGE` after **1.0.1-** type W1S0 or W1 depending what kind of patch you do

3. **Patch Description**
   - Enter in the big white space your patch description.
   - I.E : 
   ```
   CS-13471 - Jose Gracia - BH

   Fix duplicated rows in RPT_OEE_REPORT table which lead to ORA-06512 in PKG_MACHINERY ProcessOEEReport and GetOEEReport
   ```

4. **Generate Patch**:
   - Be sure that your needed file for the patch are `SELECTED IN BLUE`
   - If no file are selected the patch will be empty
   - ALL SELECTED FILES FOR PATCH WILL BE UNLOCK AFTER GENERATION


### Patches Menu

- This menu is to see previous patches

1. **Modify**
   - You can select a patch and click on modify patch to switch to the `Modify Patch` Section

2. **Build**
   - Regenerate the existing patch into `D:\cyframe\jtdev\Patches\Current`

## Configuration Files

- **`svn_config.json`**: Stores the SVN repository path, Instant Client path and username.

## File Structure

- [app.py](http://_vscodecontentref_/2): Main application file.
- [config.py](http://_vscodecontentref_/3): Handles loading and saving of configuration data.
- [create_buttons.py](http://_vscodecontentref_/5): Handles button creation and their functionalities.
- [create_component.py](http://_vscodecontentref_/6): Handles the creation of GUI components.
- [svn_operations.py](http://_vscodecontentref_/7): Manages SVN operations like locking and unlocking files.
- [version_operation.py](http://_vscodecontentref_/8): Manages versioning for patches.
- [patch_generation.py](http://_vscodecontentref_/9): Handles patch generation.
- [patches_operations.py](http://_vscodecontentref_/10): Manages operations related to patches.
- [buttons_function.py](http://_vscodecontentref_/11): Contains functions for button actions.
- [utils.py](http://_vscodecontentref_/12): Utility functions like generating MD5 checksums.
- [dialog.py](http://_vscodecontentref_/13): Handles dialog operations for selecting folders and setting usernames.

## Notes

- Ensure the [svn_config.json](http://_vscodecontentref_/14) file is included in the [.gitignore](http://_vscodecontentref_/15) to avoid committing sensitive information.
- The application assumes the presence of TortoiseSVN and Oracle database client for certain operations. Adjust paths and configurations as needed.
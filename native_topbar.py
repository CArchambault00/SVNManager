import tkinter as tk
from tkinter import messagebox
from config import load_config, get_unset_var
from dialog import set_username, set_svn_folder, set_currentpatches, set_dsn_name

def initialize_native_topbar(root):
# Create the menu bar
    menu_bar = tk.Menu(root)
    
    config_menu = tk.Menu(menu_bar, tearoff=0)

    config = load_config()
    unset_var = get_unset_var()

    menu_bar.add_cascade(
        label="Config ❌" if unset_var else "Config ✔️",
        menu=config_menu
    )

    config_menu.add_command(
        label="Username ❌" if "username" in unset_var else "Username ✔️",
        command=lambda: set_username(config_menu, menu_bar)
    )
   
    # config_menu.add_command(
    #     label="Instant client ❌" if "instant_client" in unset_var else "Instant client ✔️",
    #     command=lambda: set_instantclient(config_menu, menu_bar)
    # )
    
    config_menu.add_command(
        label="SVN folder ❌" if "svn_path" in unset_var else "SVN folder ✔️",
        command=lambda: set_svn_folder(config_menu, menu_bar))
    
    config_menu.add_command(
    label="Current Patches Folder ❌" if "current_patches" in unset_var else "Current Patches Folder ✔️",
    command=lambda: set_currentpatches(config_menu, menu_bar))

    config_menu.add_command(
    label="DSN name ❌" if "dsn_name" in unset_var else "DSN name ✔️",
    command=lambda: set_dsn_name(config_menu, menu_bar))

    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(
        label="About",
        command=lambda: messagebox.showinfo("About", "SVN Manager v1.0")
    )
    # Add a section command to explain how to use the application
    help_menu.add_command(
        label="How to use",
        command=lambda: messagebox.showinfo("How to use", "To use this application, you must first set the required variables in the Config menu.\n"
        "If variables are not set, you should see a warning message and at the top left application Config ❌.\n"
        "Once all variables are set, you can use the Lock/Unlock, Patch, and Patches menus to manage your SVN repository and see Config ✔️ at the top left of the application.")
    )

    help_menu.add_command(
        label="Lock/Unlock",
        command=lambda: messagebox.showinfo("Lock/Unlock", "This menu allows you to lock and unlock files in your SVN repository.\n"
        "You can select multiple files to lock or unlock at once.\n"
        "You can also drag and drop files from your file explorer to the listbox to lock/unlock them.\n"
        "All files that have the status 'Locked' are under the username you set in the Config menu.")
    )

    help_menu.add_command(
        label="Patch",
        command=lambda: messagebox.showinfo("Patch", "This menu allows you to create a patch from your SVN repository.\n "
        "Your locked files will be automatically be in the listbox for files\n"
        "You can select multiple files to include in the patch at once.\n"
        "You can do CTRL+A to select all files or click on a file to deselect all files.\n"
        "You can alse SHIFT+click to select multiple files.\n"
        "**You can also drag and drop files from your file explorer to the listbox to add them to the patch**\n"
        "(Files should always be locked under your name to do a patch)."
        )
    )

    help_menu.add_command(
        label="Patches",
        command=lambda: messagebox.showinfo("Patches", "This menu allows you to see all the patches the team have created.\n "
        "You can also modify a patch by selecting it and clicking on the 'Modify Patch' button.\n"
        "You can build a patch from the patches menu by selecting a patch and clicking on the 'Build Patch' button.\n"
        "The built patches will end up in D:/cyframe/patches/current/"
        )
    )

    help_menu.add_command(
        label="Modify Patch",
        command=lambda: messagebox.showinfo("Modify Patch", "This menu allows you to modify a patch.\n"
        "You can add or remove files from the patch.\n"
        "You can also drag and drop files from your file explorer to the listbox to add them to the patch.\n"
        "!!(Files should always be locked under your name to do a modify a patch).\n"
        "You can also drag and drop files from the listbox to your file explorer to remove them from the patch.\n"
        "You can modify the patch name and description.\n"
        "Once you are done modifying the patch, you can click on the 'Save Patch' button to save the patch."
        )
    )

    menu_bar.add_cascade(
        label="Help",
        menu=help_menu
    )
    menu_bar.add_cascade(
        label="Exit", 
        command=root.quit
    )
    # Attach the menu to the root window
    root.config(menu=menu_bar)
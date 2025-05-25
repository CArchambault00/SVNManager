from tkinter import filedialog, messagebox, simpledialog
from config import load_config, save_config, get_unset_var
import subprocess
import os
import tkinter as tk


def update_menu_labels(config_menu, menu_bar, index, label, unset_var):
    """Helper function to update menu labels."""
    config_menu.entryconfig(index, label=label)
    menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")


def show_messagebox(type, title, message):
    if type == "info":
        messagebox.showinfo(title, message)
    elif type == "warning":
        messagebox.showwarning(title, message)
    elif type == "error":
        messagebox.showerror(title, message)


def handle_path_selection(title, validation_func, success_callback, error_message):
    """Helper function to handle folder path selection and validation."""
    while True:
        selected_path = filedialog.askdirectory(title=title)
        if selected_path:
            if validation_func(selected_path):
                success_callback(selected_path)
                return True
            else:
                show_messagebox("error", "Error", error_message)
        else:
            return False


def set_username(config_menu, menu_bar):
    config = load_config()
    username = config.get("username", "")

    if username:
        show_messagebox("info", "Info", f"Username is already set to: {username}")
        if not messagebox.askyesno("Change Username", "Do you want to change the username?"):
            return

    username = simpledialog.askstring("Username", "Enter your username")
    if username:
        config["username"] = username
        save_config(config)
        
        # Update menu labels based on correct conditions
        for i in range(menu_bar.index('end') + 1):
            try:
                if 'Profile' in menu_bar.entrycget(i, 'label'):
                    # Profile status depends on having an active profile
                    menu_bar.entryconfig(i, label=f"Profile {'✔️' if config.get('active_profile') else '❌'}")
                elif 'Config' in menu_bar.entrycget(i, 'label'):
                    # Config status depends only on username
                    menu_bar.entryconfig(i, label=f"Config ✔️")  # Username is set, so always ✔️
            except tk.TclError:
                continue
                
        # Update the username entry in config menu
        config_menu.entryconfig(0, label="Username ✔️")
        show_messagebox("info", "Info", "Username saved successfully!")
    else:
        show_messagebox("warning", "Warning", "Username not set. Some features may not work correctly.")
        # Update menu labels for failure case
        for i in range(menu_bar.index('end') + 1):
            try:
                if 'Config' in menu_bar.entrycget(i, 'label'):
                    menu_bar.entryconfig(i, label="Config ❌")  # No username, so ❌
            except tk.TclError:
                continue
        config_menu.entryconfig(0, label="Username ❌")


# def validate_instant_client(path):
#     """Validation function for Instant Client folder."""
#     required_files = ["oci.dll"]
#     return all(os.path.exists(os.path.join(path, file)) for file in required_files)


# def set_instantclient(config_menu, menu_bar):
#     config = load_config()
#     instant_client = config.get("instant_client", "")

#     if instant_client:
#         show_messagebox("info", "Info", f"Instant Client path set to: {instant_client}")
#         if not messagebox.askyesno("Change Instant Client Path", "Do you want to change the Instant Client path?"):
#             return

#     def success_callback(path):
#         config["instant_client"] = path
#         save_config(config)
#         unset_var = get_unset_var()
#         update_menu_labels(config_menu, menu_bar, 1, "Instant client ✔️", unset_var)
#         show_messagebox("info", "Info", "Instant Client path changed successfully!")

#     if not handle_path_selection(
#         "Select INSTANT_CLIENT Folder", validate_instant_client, success_callback,
#         "The selected folder is not a valid Instant Client 12.1.0 folder"
#     ):
#         show_messagebox("warning", "Warning", "Instant Client path not changed.")


def validate_svn_folder(path):
    """Validation function for SVN folder."""
    args = ["svn", "info", path]
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

def validate_current_patches(path):
    return os.path.exists(path) and os.path.isdir(path)

def validate_dsn_name(dsn_name):
    """Validation function for DSN name."""
    return bool(dsn_name)  # Check if the DSN name is not empty

def set_svn_folder(config_menu, menu_bar):
    config = load_config()
    svn_path = config.get("svn_path", "")

    if svn_path:
        show_messagebox("info", "Info", f"SVN folder path set to: {svn_path}")
        if not messagebox.askyesno("Change SVN Folder Path", "Do you want to change the SVN folder path?"):
            return

    def success_callback(path):
        config["svn_path"] = path
        save_config(config)
        unset_var = get_unset_var()
        update_menu_labels(config_menu, menu_bar, 1, "SVN folder ✔️", unset_var)
        show_messagebox("info", "Info", "SVN folder path changed successfully!")

    if not handle_path_selection(
        "Select SVN Folder", validate_svn_folder, success_callback,
        "The selected folder is not a valid SVN folder"
    ):
        show_messagebox("warning", "Warning", "SVN folder path not changed.")


def set_currentpatches(config_menu, menu_bar):
    config = load_config()
    current_patches = config.get("current_patches", "")

    if current_patches:
            show_messagebox("info", "Info", f"Current patches folder path set to: {current_patches}")
            if not messagebox.askyesno("Change Current patches folder Path", "Do you want to change the Current patches folder path?"):
                return

    def success_callback(path):
        config["current_patches"] = path
        save_config(config)
        unset_var = get_unset_var()
        update_menu_labels(config_menu, menu_bar, 2, "Current patches folder ✔️", unset_var)
        show_messagebox("info", "Info", "Current patches folder changed successfully!")

    if not handle_path_selection(
        "Select Current patches folder", validate_current_patches, success_callback,
        "The selected folder is not a valid Current patches folder"
    ):
        show_messagebox("warning", "Warning", "Current patches folder path not changed.")

def set_dsn_name(config_menu, menu_bar):
    config = load_config()
    dsn_name = config.get("dsn_name", "")

    if dsn_name:
        show_messagebox("info", "Info", f"DSN name is already set to: {dsn_name}")
        if not messagebox.askyesno("Change DSN Name", "Do you want to change the DSN name?"):
            return

    dsn_name = simpledialog.askstring("DSN Name", "Enter your DSN name")
    if dsn_name:
        config["dsn_name"] = dsn_name
        save_config(config)
        unset_var = get_unset_var()
        update_menu_labels(config_menu, menu_bar, 3, "DSN Name ✔️", unset_var)
        show_messagebox("info", "Info", "DSN name saved successfully!")
    else:
        show_messagebox("warning", "Warning", "DSN name not set. Some features may not work correctly.")
        update_menu_labels(config_menu, menu_bar, 3, "DSN Name ❌", get_unset_var())

def display_patch_files(patche_files, patch_name, patch_description, username, patch_creation_date):
    """Display the patch files in a scrollable window."""
    # Create a new top-level window
    window = tk.Toplevel()
    window.title("Patch Files")
    window.geometry("900x400")  # Set a default size for the window

    window.transient()  # Set the window as a child of the main app
    window.grab_set() 
    
    # Create a Text widget with a vertical scrollbar
    text_frame = tk.Frame(window)
    text_frame.pack(fill="both", expand=True)

    text_widget = tk.Text(text_frame, wrap="word", state="normal")
    text_widget.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
    scrollbar.pack(side="right", fill="y")

    text_widget.config(yscrollcommand=scrollbar.set)

    # Build the message content
    message = f"Patch Name: {patch_name}\n"
    message += f"Description: {patch_description}\n"
    message += f"Created by: {username}\n"
    message += f"Creation Date: {patch_creation_date}\n\n"
    message += "Files:\n"
    for file in patche_files:
        message += f"- {file}\n"

    # Insert the message into the Text widget
    text_widget.insert("1.0", message)
    text_widget.config(state="disabled")  # Make the Text widget read-only

    # Add a close button
    close_button = tk.Button(window, text="Close", command=window.destroy)
    close_button.pack(pady=10)
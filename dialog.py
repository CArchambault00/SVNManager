
from tkinter import filedialog, messagebox, ttk, simpledialog
import tkinter as tk
from config import load_config, save_config, get_unset_var
import subprocess
import os

def select_svn_folder(button):
    folder = filedialog.askdirectory(title="Select SVN Folder")
    # Verify that the selected folder is a valid SVN folder
    if folder:
        args = ["svn", "info", folder]
        result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            config = load_config()
            config["svn_path"] = folder
            save_config(config)
            button.config(background="SystemButtonFace")
        else:
            messagebox.showerror("Error", "The selected folder is not a valid SVN folder")

def select_instant_client_folder(button):
    folder = filedialog.askdirectory(title="Select INSTANT_CLIENT Folder")
    if folder:
        required_files = ["oci.dll"]  # Add other required files if necessary
        if all(os.path.exists(os.path.join(folder, file)) for file in required_files):
            config = load_config()
            config["instant_client"] = folder
            save_config(config)
            button.config(background="SystemButtonFace")
        else:
            messagebox.showerror("Error", "The selected folder is not a valid Instant Client 12.1.0 folder")

        
def set_username(config_menu, menu_bar):
    config = load_config()
    username = config.get("username", "")
    if not username:
        # Open a dialog to set the username
        username = simpledialog.askstring("Username", "Enter your username")
        if username:
            config["username"] = username
            save_config(config)
            unset_var = get_unset_var()
            config_menu.entryconfig(0, label="Username ✔️")  # Correctly update the Username label
            menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")  # Correctly update the Config label
            messagebox.showinfo("Info", "Username saved successfully!")
        else:
            messagebox.showwarning("Warning", "Username not set. Some features may not work correctly.")
            config_menu.entryconfig(0, label="Username ❌")  # Correctly update the Username label
    else:
        messagebox.showinfo("Info", f"Username is already set to: {username}")
        # Ask if the user wants to change the username
        if messagebox.askyesno("Change Username", "Do you want to change the username?"):
            username = simpledialog.askstring("Username", "Enter your username")
            if username:
                config["username"] = username
                save_config(config)
                unset_var = get_unset_var()
                config_menu.entryconfig(0, label="Username ✔️")  # Correctly update the Username label
                menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")  # Correctly update the Config label
                messagebox.showinfo("Info", "Username changed successfully!")
            else:
                messagebox.showwarning("Warning", "Username not changed.")

def set_instantclient(config_menu, menu_bar):
    invalid = True
    config = load_config()
    instant_client = config["instant_client"]
    if not instant_client:
        while (invalid): 
            instant_client = filedialog.askdirectory(title="Select INSTANT_CLIENT Folder")
            if instant_client:
                required_files = ["oci.dll"]
                if all(os.path.exists(os.path.join(instant_client, file)) for file in required_files):
                    config["instant_client"] = instant_client
                    save_config(config)
                    unset_var = get_unset_var()
                    config_menu.entryconfig(1, label="Instant client ✔️")  # Correctly update the Username label
                    menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")  # Correctly update the Config label
                    invalid = False
                    messagebox.showinfo("Info", "Instant Client path changed successfully!")
                else:
                    messagebox.showerror("Error", "The selected folder is not a valid Instant Client 12.1.0 folder")
                    invalid = True
            else:
                messagebox.showwarning("Warning", "Instant Client path not set. Some features may not work correctly.")
                config_menu.entryconfig(1, label="Instant client ❌")  # Correctly update the Username label
                invalid = False
    else:
        messagebox.showinfo("Info", f"Instant Client path set to: {instant_client}")
        # want to change the instant client path
        if messagebox.askyesno("Change Instant Client Path", "Do you want to change the Instant Client path?"):
            while (invalid):
                instant_client = filedialog.askdirectory(title="Select INSTANT_CLIENT Folder")
                if instant_client:
                    required_files = ["oci.dll"]
                    if all(os.path.exists(os.path.join(instant_client, file)) for file in required_files):
                        config["instant_client"] = instant_client
                        save_config(config)
                        messagebox.showinfo("Info", "Instant Client path changed successfully!")
                        unset_var = get_unset_var()
                        config_menu.entryconfig(1, label="Instant client ✔️")  # Correctly update the Username label
                        menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")  # Correctly update the Config label
                        invalid = False
                    else:
                        messagebox.showerror("Error", "The selected folder is not a valid Instant Client 12.1.0 folder")
                        invalid = True
                else:
                    messagebox.showwarning("Warning", "Instant Client path not changed.")
                    invalid = False
        else:
            messagebox.showinfo("Info", "Instant Client path not changed.")

def set_svn_folder(config_menu, menu_bar):
    invalid = True
    config = load_config()
    svn_path = config["svn_path"]
    if not svn_path:
        # Open a dialog to set the SVN folder path
        while (invalid):
            svn_path = filedialog.askdirectory(title="Select SVN Folder")
            if svn_path:
                args = ["svn", "info", svn_path]
                result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    config["svn_path"] = svn_path
                    save_config(config)
                    unset_var = get_unset_var()
                    config_menu.entryconfig(2, label="SVN folder ✔️")  # Correctly update the Username label
                    menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")  # Correctly update the Config label
                    invalid = False
                    messagebox.showinfo("Info", "SVN folder path changed successfully!")
                else:
                    messagebox.showerror("Error", "The selected folder is not a valid SVN folder")
                    invalid = True
            else:
                messagebox.showwarning("Warning", "SVN folder path not set. Some features may not work correctly.")
                config_menu.entryconfig(2, label="SVN folder ❌")  # Correctly update the Username label
                invalid = False
    else:
        messagebox.showinfo("Info", f"SVN folder path set to: {svn_path}")
        # want to change the SVN folder path
        if messagebox.askyesno("Change SVN Folder Path", "Do you want to change the SVN folder path?"):
            while (invalid):
                svn_path = filedialog.askdirectory(title="Select SVN Folder")
                if svn_path:
                    args = ["svn", "info", svn_path]
                    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if result.returncode == 0:
                        config["svn_path"] = svn_path
                        save_config(config)
                        unset_var = get_unset_var()
                        config_menu.entryconfig(2, label="SVN folder ✔️")  # Correctly update the Username label
                        menu_bar.entryconfig(1, label="Config ❌" if unset_var else "Config ✔️")  # Correctly update the Config label
                        invalid = False
                        messagebox.showinfo("Info", "SVN folder path changed successfully!")
                    else:
                        messagebox.showerror("Error", "The selected folder is not a valid SVN folder")
                        invalid = True
                else:
                    messagebox.showwarning("Warning", "SVN folder path not changed.")
                    invalid = False
        else:
            messagebox.showinfo("Info", "SVN folder path not changed.")
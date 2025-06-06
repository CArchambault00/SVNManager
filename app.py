import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
from svn_operations import refresh_locked_files
from patches_operations import refresh_patches, refresh_patch_files
from create_component import create_patches_treeview, create_file_listbox, create_top_frame
from create_buttons import create_button_frame, create_button_frame_patch, create_button_frame_modify_patch, create_button_frame_patches
from config import load_config, get_unset_var
from native_topbar import initialize_native_topbar
import urllib.request
import random
import sys
import os
import webbrowser
from state_manager import state_manager

APP_VERSION = "1.0.20"

def create_main_layout(root):
    root.grid_rowconfigure(1, weight=1)

    # Ratio 2:1 (left: 2/3, right: 1/3)
    root.grid_columnconfigure(0, weight=2)  # Bottom left frame
    root.grid_columnconfigure(1, weight=1)  # Bottom right frame

    top_frame = tk.Frame(root, height=80, relief=tk.RIDGE, borderwidth=2)
    top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    bottom_left_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_left_frame.grid(row=1, column=0, sticky="nsew")

    bottom_right_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_right_frame.grid(row=1, column=1, sticky="nsew")

    # Empêcher bottom_left_frame de dépasser 2/3 de la largeur
    def enforce_ratio(event=None):
        total_width = root.winfo_width()
        max_left_width = int(total_width * (2 / 3))
        bottom_left_frame.config(width=max_left_width)
        bottom_left_frame.update_idletasks()

    root.bind("<Configure>", enforce_ratio)

    return top_frame, bottom_left_frame, bottom_right_frame


def check_requirements():
    config = load_config()
    messages = []
    
    if not config.get("username"):
        messages.append("Please set your username in the Config menu")
    if not config.get("active_profile"):
        messages.append("Please select or create a profile in the Profile menu")
        
    if messages:
        messagebox.showwarning("Setup Required", "\n".join(messages))
        return False
    return True

def switch_to_lock_unlock_menu():
    if not check_requirements():
        return
        
    # Save current state if coming from another menu
    if state_manager.current_menu:
        save_current_state()
    
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "lock_unlock")
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame(bottom_right_frame, files_listbox)
    
    # Restore state if available
    lock_unlock_state = state_manager.get_state("lock_unlock")
    if lock_unlock_state.get("listbox_items"):
        # Repopulate the listbox with saved items
        for item in lock_unlock_state["listbox_items"]:
            files_listbox.insert("", "end", values=item)
        # Restore selection
        if lock_unlock_state.get("selected_files"):
            for item_id in files_listbox.get_children():
                values = files_listbox.item(item_id, "values")
                if values and values[2] in lock_unlock_state["selected_files"]:
                    files_listbox.selection_add(item_id)
    else:
        # No saved state, refresh from SVN
        refresh_locked_files(files_listbox)
    
    # Set the current menu
    state_manager.current_menu = "lock_unlock"

def switch_to_patch_menu():
    if not check_requirements():
        return
        
    # Save current state if coming from another menu
    if state_manager.current_menu:
        save_current_state()
    
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "patch")
    files_listbox = create_file_listbox(bottom_left_frame)
    buttons_frame = create_button_frame_patch(bottom_right_frame, files_listbox)
    
    # Restore state if available
    patch_state = state_manager.get_state("patch")
    if patch_state.get("listbox_items"):
        # Repopulate the listbox with saved items
        for item in patch_state["listbox_items"]:
            files_listbox.insert("", "end", values=item)
        # Restore selection
        if patch_state.get("selected_files"):
            for item_id in files_listbox.get_children():
                values = files_listbox.item(item_id, "values")
                if values and values[2] in patch_state["selected_files"]:
                    files_listbox.selection_add(item_id)
                    
        # Restore other input values
        if "patch_version_entry" in buttons_frame and patch_state.get("patch_version"):
            buttons_frame["patch_version_entry"].delete(0, tk.END)
            buttons_frame["patch_version_entry"].insert(0, patch_state["patch_version"])
        
        if "patch_description_entry" in buttons_frame and patch_state.get("patch_description"):
            buttons_frame["patch_description_entry"].delete("1.0", tk.END)
            buttons_frame["patch_description_entry"].insert("1.0", patch_state["patch_description"])
            
        if "unlock_files" in buttons_frame and patch_state.get("unlock_files") is not None:
            buttons_frame["unlock_files"].set(patch_state["unlock_files"])
    else:
        # No saved state, refresh from SVN
        refresh_locked_files(files_listbox)
    
    # Set the current menu
    state_manager.current_menu = "patch"

def switch_to_patches_menu():
    if not check_requirements():
        return
        
    # Save current state if coming from another menu
    if state_manager.current_menu:
        save_current_state()
    
    config = load_config()
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu,  "patches")
    
    # Create a Treeview to display patches
    patches_listbox = create_patches_treeview(bottom_left_frame)
    buttons_frame = create_button_frame_patches(bottom_right_frame, patches_listbox, switch_to_modify_patch_menu)
    username = config.get("username")
    
    # Restore state if available
    patches_state = state_manager.get_state("patches")
    selected_prefix = patches_state.get("selected_prefix", "S")
    
    if "patch_version_prefixe" in buttons_frame:
        buttons_frame["patch_version_prefixe"].set(selected_prefix)
    
    # Refresh patches with the saved prefix
    refresh_patches(patches_listbox, False, selected_prefix, username)
    
    # Restore selected patch if applicable
    if patches_state.get("selected_patch"):
        for item_id in patches_listbox.get_children():
            patch_name = patches_listbox.item(item_id, "values")[0]
            if patch_name == patches_state["selected_patch"]:
                patches_listbox.selection_set(item_id)
                break
    
    # Set the current menu
    state_manager.current_menu = "patches"

def switch_to_modify_patch_menu(patch_details=None):
    if not check_requirements():
        return
        
    # Save current state if coming from another menu
    if state_manager.current_menu:
        save_current_state()
    
    # Get the modify_patch state first
    modify_patch_state = state_manager.get_state("modify_patch")
    
    # If no patch is provided, use the last selected patch from state
    if patch_details is None:
        patch_details = modify_patch_state.get("patch_details")
        if not patch_details:
            messagebox.showwarning("No Patch Selected", "Please select a patch from the Patches List first.")
            switch_to_patches_menu()
            return
    else:
        # A new patch was selected, check if it's different from current one
        current_patch_id = modify_patch_state.get("patch_details", {}).get("PATCH_ID") if modify_patch_state.get("patch_details") else None
        if current_patch_id != patch_details.get("PATCH_ID"):
            state_manager.clear_state("modify_patch")
            # Need to get the state again after clearing
            modify_patch_state = state_manager.get_state("modify_patch")
            # Always update the current patch details in the state manager
            modify_patch_state["patch_details"] = patch_details
    
    # Build the UI
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    menu_button = create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, "modify_patch")
    files_listbox = create_file_listbox(bottom_left_frame)
    buttons_frame = create_button_frame_modify_patch(bottom_right_frame, files_listbox, patch_details, switch_to_modify_patch_menu)
    
    # If we have saved listbox items, restore them
    if modify_patch_state.get("listbox_items"):
        # Repopulate the listbox with saved items
        for item in modify_patch_state["listbox_items"]:
            files_listbox.insert("", "end", values=item)
        # Restore selection
        if modify_patch_state.get("selected_files"):
            for item_id in files_listbox.get_children():
                values = files_listbox.item(item_id, "values")
                if values and values[2] in modify_patch_state["selected_files"]:
                    files_listbox.selection_add(item_id)
                    
        # Restore other input values
        if "patch_version_entry" in buttons_frame and modify_patch_state.get("patch_version"):
            buttons_frame["patch_version_entry"].delete(0, tk.END)
            buttons_frame["patch_version_entry"].insert(0, modify_patch_state["patch_version"])
        
        if "patch_description_entry" in buttons_frame and modify_patch_state.get("patch_description"):
            buttons_frame["patch_description_entry"].delete("1.0", tk.END)
            buttons_frame["patch_description_entry"].insert("1.0", modify_patch_state["patch_description"])
            
        if "unlock_files" in buttons_frame and modify_patch_state.get("unlock_files") is not None:
            buttons_frame["unlock_files"].set(modify_patch_state["unlock_files"])
    else:
        # No saved state, refresh from database
        refresh_patch_files(files_listbox, patch_details)
    
    # Set the current menu
    state_manager.current_menu = "modify_patch"

def save_current_state():
    """Save the current state of the active menu before switching"""
    current_menu = state_manager.current_menu
    if not current_menu:
        return
        
    # Find all widgets in the current menu
    for widget in root.winfo_children():
        if not isinstance(widget, tk.Menu):
            # Look for the files_listbox or patches_listbox
            file_listbox = find_listbox_or_treeview(widget)
            if file_listbox:
                # Save listbox items and selection
                if current_menu in ["lock_unlock", "patch", "modify_patch"]:
                    selected_files = []
                    listbox_items = []
                    
                    for item_id in file_listbox.get_children():
                        values = file_listbox.item(item_id, "values")
                        listbox_items.append(values)
                        if item_id in file_listbox.selection():
                            selected_files.append(values[2])  # File path is at index 2
                    
                    state_manager.save_state(current_menu, 
                                           selected_files=selected_files, 
                                           listbox_items=listbox_items)
                elif current_menu == "patches":
                    selected_patch = None
                    selected_items = file_listbox.selection()
                    if selected_items:
                        selected_patch = file_listbox.item(selected_items[0], "values")[0]
                    
                    # Find the patch prefix combobox
                    patch_prefixe = find_patch_prefix_combobox(widget)
                    selected_prefix = patch_prefixe.get() if patch_prefixe else "S"
                    
                    state_manager.save_state(current_menu, 
                                           selected_patch=selected_patch,
                                           selected_prefix=selected_prefix)
            
            # For patch and modify_patch menus, save more input values
            if current_menu in ["patch", "modify_patch"]:
                patch_version_entry = find_widget_by_class_and_width(widget, tk.Entry, 14)
                patch_description_entry = find_widget_by_class(widget, tk.Text)
                unlock_files_var = find_widget_by_class(widget, tk.BooleanVar)
                
                if patch_version_entry:
                    state_manager.states[current_menu]["patch_version"] = patch_version_entry.get()
                
                if patch_description_entry:
                    state_manager.states[current_menu]["patch_description"] = patch_description_entry.get("1.0", tk.END)
                
                if unlock_files_var:
                    state_manager.states[current_menu]["unlock_files"] = unlock_files_var.get()

def find_listbox_or_treeview(parent):
    """Find a Treeview widget in the given parent widget"""
    from tkinter import ttk
    
    if isinstance(parent, ttk.Treeview):
        return parent
    
    for child in parent.winfo_children():
        result = find_listbox_or_treeview(child)
        if result:
            return result
    
    return None

def find_patch_prefix_combobox(parent):
    """Find the patch prefix combobox in the given parent widget"""
    from tkinter import ttk
    
    if isinstance(parent, ttk.Combobox) and parent.winfo_width() < 50:  # Small combobox is likely the prefix
        return parent
    
    for child in parent.winfo_children():
        result = find_patch_prefix_combobox(child)
        if result:
            return result
    
    return None

def find_widget_by_class_and_width(parent, widget_class, width):
    """Find a widget of specified class and width"""
    if isinstance(parent, widget_class):
        try:
            if parent["width"] == width:
                return parent
        except (tk.TclError, TypeError):
            pass
    
    for child in parent.winfo_children():
        result = find_widget_by_class_and_width(child, widget_class, width)
        if result:
            return result
    
    return None

def find_widget_by_class(parent, widget_class):
    """Find a widget of specified class"""
    if isinstance(parent, widget_class):
        return parent
    
    for child in parent.winfo_children():
        result = find_widget_by_class(child, widget_class)
        if result:
            return result
    
    return None

def check_latest_version(root):
    random_number = random.randint(1, 1000000)
    url = f"https://raw.githubusercontent.com/CArchambault00/SVNManager/main/latest_version.txt?nocache={random_number}"

    try:
        req = urllib.request.Request(
            url,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "User-Agent": "SVNManager"
            }
        )

        with urllib.request.urlopen(req) as response:
            latest_version = response.read().decode("utf-8").strip()

        if latest_version != APP_VERSION:
            if messagebox.askyesno("Update Available", f"A new version ({latest_version}) is available.\nDo you want to open the download page?"):
                release_url = f"https://github.com/CArchambault00/SVNManager/releases/tag/{latest_version}"
                webbrowser.open(release_url)
            sys.exit(0)

    except Exception as e:
        print(f"Failed to check for latest version: {e}")
        messagebox.showerror("Error", f"Failed to check for latest version:\n{e}")

def setup_gui():
    global root
    root = TkinterDnD.Tk()  # Initialize TkinterDnD root window 
    if getattr(sys, 'frozen', False):  # Running as a PyInstaller bundle
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.abspath(".")

    icon_path = os.path.join(bundle_dir, "SVNManagerIcon.ico")
        
    root.iconbitmap(icon_path)
    root.title("SVN Manager")
    root.geometry("900x600")

    #Add to check for the latest version
    check_latest_version(root)

    initialize_native_topbar(root)
    
    # Check configuration before switching to initial menu
    config = load_config()
    if not config.get("username"):
        messagebox.showwarning("Setup Required", "Please set your username in the Config menu")
    elif not config.get("active_profile"):
        messagebox.showwarning("Setup Required", "Please select or create a profile in the Profile menu")
    else:
        switch_to_lock_unlock_menu()
    
    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()

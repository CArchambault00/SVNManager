import os
import sys
import random
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import messagebox
from tkinterdnd2 import TkinterDnD
from typing import Tuple, Optional, Dict, Any, List, Callable

# Local modules
from svn_operations import refresh_locked_files, get_file_info, refresh_file_status_version
from patches_operations import refresh_patches, refresh_patch_files
from create_component import create_patches_treeview, create_file_listbox, create_top_frame
from create_buttons import (
    create_button_frame, create_button_frame_patch, 
    create_button_frame_modify_patch, create_button_frame_patches
)
from context_menu import context_menu_manager
from config import load_config, get_unset_var, log_error
from native_topbar import initialize_native_topbar
from version_operation import next_version
from state_manager import state_manager
from text_widget_utils import get_text_content, ensure_text_widget_visible

APP_VERSION = "1.0.21"

def create_main_layout(root: tk.Tk, left_weight = 2, right_weight = 1) -> Tuple[tk.Frame, tk.Frame, tk.Frame]:
    """
    Create the main application layout with three frames.
    
    Args:
        root: The root tkinter window
        
    Returns:
        Tuple containing top_frame, bottom_left_frame, and bottom_right_frame
    """
    root.grid_rowconfigure(1, weight=1)

    # Ratio 2:1 (left: 2/3, right: 1/3)
    root.grid_columnconfigure(0, weight=left_weight)  # Bottom left frame
    root.grid_columnconfigure(1, weight=right_weight)  # Bottom right frame

    top_frame = tk.Frame(root, height=80, relief=tk.RIDGE, borderwidth=2)
    top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")

    bottom_left_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_left_frame.grid(row=1, column=0, sticky="nsew")

    bottom_right_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_right_frame.grid(row=1, column=1, sticky="nsew")

    # Prevent bottom_left_frame from exceeding 2/3 of the width
    def enforce_ratio(event=None):
        if not bottom_left_frame.winfo_exists() or not bottom_right_frame.winfo_exists():
            root.unbind("<Configure>")  # Unbind if frames no longer exist
            return
        try:
            total_width = root.winfo_width()
            max_left_width = int(total_width * (2 / 3))
            bottom_left_frame.config(width=max_left_width)
            bottom_left_frame.update_idletasks()
        except tk.TclError:
            root.unbind("<Configure>")  # Unbind on error

    # Store the binding ID so we can unbind it later
    binding_id = root.bind("<Configure>", enforce_ratio)
    
    # Store the binding ID in the frames for later cleanup
    bottom_left_frame.enforce_ratio_binding = binding_id
    
    return top_frame, bottom_left_frame, bottom_right_frame


def check_requirements() -> bool:
    """
    Check if the required configuration is set.
    
    Returns:
        bool: True if all requirements are met, False otherwise
    """
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


def save_current_state(root_widget) -> None:
    """Save the current state of the active menu before switching"""
    current_menu = state_manager.current_menu
    if not current_menu:
        return
        
    # Find all widgets in the current menu
    for widget in root_widget.winfo_children():
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
            
            # For patch and modify_patch menus, save more input values directly
            if current_menu in ["patch", "modify_patch"]:
                save_patch_form_state(root_widget, current_menu)  # Save using the root to find all widgets

def save_patch_form_state(widget, menu_name: str) -> None:
    """Save the state of patch form fields (version entry, description, etc.)"""
    patch_version_entry = find_widget_by_class_and_width(widget, tk.Entry, 14)
    patch_description_entry = find_widget_by_class(widget, tk.Text)
    unlock_files_var = find_widget_by_class(widget, tk.BooleanVar)
    
    # Initialize the state dict if it doesn't exist
    if menu_name not in state_manager.states:
        state_manager.states[menu_name] = {}
    
    if patch_version_entry:
        # Get the content directly from the entry widget
        patch_version = patch_version_entry.get()
        state_manager.states[menu_name]["patch_version"] = patch_version
    
    if patch_description_entry:
        state_manager.states[menu_name]["patch_description"] = get_text_content(patch_description_entry)
    
    if unlock_files_var:
        state_manager.states[menu_name]["unlock_files"] = unlock_files_var.get()


def switch_to_lock_unlock_menu(root_widget=None) -> None:
    """Switch to the lock/unlock menu and set up its UI components."""
    if not check_requirements():
        return
    
    root_widget = ensure_root_widget(root_widget)
    if root_widget is None:
        messagebox.showerror("Error", "Could not find application root window")
        return
    
    # Save current state if coming from another menu
    if state_manager.current_menu:
        save_current_state(root_widget)
    
    for widget in root_widget.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
            
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root_widget, left_weight=2, right_weight=0)
    create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, 
                    switch_to_patches_menu, switch_to_modify_patch_menu, "lock_unlock")
    
    files_listbox = create_file_listbox(bottom_left_frame, menu_name='lock_unlock')
    #create_button_frame(bottom_right_frame, files_listbox)
    
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


def switch_to_patch_menu(root_widget=None) -> None:
    """Switch to the patch creation menu and set up its UI components."""
    if not check_requirements():
        return
    
    if state_manager.is_menu_loading():
        return  # Don't allow switch while loading
    
    root_widget = ensure_root_widget(root_widget)
    if root_widget is None:
        messagebox.showerror("Error", "Could not find application root window")
        return

    state_manager.set_loading(True)  # Start loading
    try:
        # Save current state if coming from another menu
        if state_manager.current_menu and state_manager.current_menu != "patch":
            save_current_state(root_widget)

        for widget in root_widget.winfo_children():
            if not isinstance(widget, tk.Menu):
                widget.destroy()
                
        top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root_widget)
        create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, 
                        switch_to_patches_menu, switch_to_modify_patch_menu, "patch")
        
        # Create a vertical split in the left frame to hold both treeviews
        left_frame_container = tk.Frame(bottom_left_frame)
        left_frame_container.pack(side="top", fill="both", expand=True)
        
        # Top section for patch files
        files_frame = tk.LabelFrame(left_frame_container, text="Files for patch")
        files_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        files_listbox = create_file_listbox(files_frame)
        
        # Bottom section for available locked files
        locked_files_frame = tk.LabelFrame(left_frame_container, text="Available locked files")
        locked_files_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        # Get the saved state before creating UI components
        patch_state = state_manager.get_state("patch")
        
        # Create buttons and form in the right frame
        buttons_frame = create_button_frame_patch(bottom_right_frame, files_listbox, locked_files_frame, patch_state)
        
        # Force initial layout update to ensure widgets are mapped
        root_widget.update_idletasks()
        root_widget.update()

        # Restore the files listbox items immediately
        if patch_state.get("listbox_items"):
            for item in patch_state["listbox_items"]:
                files_listbox.insert("", "end", values=item)
            
            # Restore selection
            if patch_state.get("selected_files"):
                for item_id in files_listbox.get_children():
                    values = files_listbox.item(item_id, "values")
                    if values and values[2] in patch_state["selected_files"]:
                        files_listbox.selection_add(item_id)

        refresh_file_status_version(files_listbox)
        
        # Always refresh ONLY the locked files treeview
        if "locked_files_treeview" in buttons_frame:
            context_menu_manager.refresh_available_locked_files(
                buttons_frame["locked_files_treeview"], 
                files_listbox
            )
    
        # Create drag and drop callback
        def on_drop_with_state_preservation(event):
            from buttons_function import handle_drop
            handle_drop(event, files_listbox)
            root = files_listbox.winfo_toplevel()
            save_current_state(root)
            if "locked_files_treeview" in buttons_frame:
                context_menu_manager.refresh_available_locked_files(
                    buttons_frame["locked_files_treeview"],
                    files_listbox
                )

        # Set up DnD safely
        def setup_dnd_safely(listbox, buttons_frame, callback) -> None:
            """
            Safely set up drag and drop binding after ensuring widget is fully ready.
            
            Args:
                listbox: The treeview widget to bind DnD to
                buttons_frame: Dictionary containing UI references
                callback: The callback function to execute on drop
            """
            def schedule_dnd_binding():
                try:
                    if not listbox.winfo_exists():
                        return False
                        
                    # Get root window through widget path traversal
                    try:
                        root = listbox
                        while root.master:
                            root = root.master
                        root.update_idletasks()
                    except (tk.TclError, AttributeError):
                        pass
                        
                    # Bind DnD event
                    listbox.dnd_bind("<<Drop>>", callback)
                    return True
                except (tk.TclError, AttributeError) as e:
                    print(f"DnD binding attempt failed, retrying... ({e})")
                    log_error(f"DnD binding attempt failed, retrying... ({e})")
                    try:
                        listbox.after(100, schedule_dnd_binding)
                    except tk.TclError:
                        pass
                    return False

            # Initial attempt after a short delay
            listbox.after(50, schedule_dnd_binding)

        setup_dnd_safely(files_listbox, buttons_frame, on_drop_with_state_preservation)
        
        # Set the current menu
        state_manager.current_menu = "patch"
    finally:
        state_manager.set_loading(False)  # Always clear loading state


def restore_patch_form_state(buttons_frame: dict, state: dict) -> None:
    """Restore the state of patch form fields (version entry, description, etc.)"""
    try:
        # Restore patch version
        if "patch_version_entry" in buttons_frame and state.get("patch_version"):
            buttons_frame["patch_version_entry"].delete(0, tk.END)
            buttons_frame["patch_version_entry"].insert(0, state["patch_version"])
        
        # Restore unlock files checkbox
        if "unlock_files" in buttons_frame and state.get("unlock_files") is not None:
            buttons_frame["unlock_files"].set(state["unlock_files"])
        
        # Restore patch description
        if ("patch_description_entry" in buttons_frame and 
            state.get("patch_description") and 
            isinstance(buttons_frame["patch_description_entry"], tk.Text)):
            ensure_text_widget_visible(
                buttons_frame["patch_description_entry"], 
                state["patch_description"]
            )
    except Exception as e:
        print(f"Error restoring patch form state: {e}")
        log_error(f"Error restoring patch form state: {e}")


def switch_to_patches_menu(root_widget=None) -> None:
    """Switch to the patches list menu and set up its UI components."""
    if not check_requirements():
        return
    
    root_widget = ensure_root_widget(root_widget)
    if root_widget is None:
        messagebox.showerror("Error", "Could not find application root window")
        return

    # Stop refresh timer when leaving patch/modify_patch menu
    state_manager.stop_refresh_timer(root_widget)
    
    # Save current state if coming from another menu
    if state_manager.current_menu and state_manager.current_menu != "patches":
        save_current_state(root_widget)
    
    config = load_config()
    for widget in root_widget.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
            
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root_widget, left_weight=6, right_weight=1)
    create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, 
                    switch_to_patches_menu, switch_to_modify_patch_menu, "patches")
    
    # Create a Treeview to display patches
    patches_listbox = create_patches_treeview(
        bottom_left_frame,
        lambda patch_info: switch_to_modify_patch_menu(patch_info, root_widget)
    )
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


def switch_to_modify_patch_menu(patch_details: Optional[Dict[str, Any]] = None, root_widget=None) -> None:
    """
    Switch to the modify patch menu and set up its UI components.
    
    Args:
        patch_details: Dictionary containing patch details, or None to use last selected patch
        root_widget: Optional root widget reference, if not provided uses global root
    """
    if not check_requirements():
        return

    root_widget = ensure_root_widget(root_widget)
    if root_widget is None:
        messagebox.showerror("Error", "Could not find application root window")
        return
        
    # Save current state if coming from another menu
    if state_manager.current_menu and state_manager.current_menu != "modify_patch":
        save_current_state(root_widget)
        
    # Get the modify_patch state first
    modify_patch_state = state_manager.get_state("modify_patch")
    
    # If no patch is provided, use the last selected patch from state
    if patch_details is None:
        patch_details = modify_patch_state.get("patch_details")
        if not patch_details:
            messagebox.showwarning("No Patch Selected", "Please select a patch from the Patches List first.")
            switch_to_patches_menu(root_widget)  # Pass root_widget here
            return
    else:
        # A new patch was selected or we're resetting
        current_patch_id = modify_patch_state.get("patch_details", {}).get("PATCH_ID") if modify_patch_state.get("patch_details") else None
        if current_patch_id != patch_details.get("PATCH_ID"):
            state_manager.clear_state("modify_patch")
            modify_patch_state = state_manager.get_state("modify_patch")
            modify_patch_state["patch_details"] = patch_details
            # Store original patch details when first loading the patch
            modify_patch_state["original_patch_details"] = patch_details.copy()

    # Clear existing widgets
    for widget in root_widget.winfo_children():
        if not isinstance(widget, tk.Menu):
            widget.destroy()
            
    # Create layout
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root_widget)
    create_top_frame(top_frame, switch_to_lock_unlock_menu, switch_to_patch_menu, 
                    switch_to_patches_menu, switch_to_modify_patch_menu, "modify_patch")
    
    # Create frames
    left_frame_container = tk.Frame(bottom_left_frame)
    left_frame_container.pack(side="top", fill="both", expand=True)
    
    files_frame = tk.LabelFrame(left_frame_container, text="Files for patch")
    files_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    files_listbox = create_file_listbox(files_frame)
    
    locked_files_frame = tk.LabelFrame(left_frame_container, text="Available locked files")
    locked_files_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    # Create buttons and form
    buttons_frame = create_button_frame_modify_patch(bottom_right_frame, files_listbox, patch_details, 
                                                  switch_to_modify_patch_menu, locked_files_frame)
    
    # Force initial layout update
    root_widget.update_idletasks()
    
    # Restore state if available
    if modify_patch_state.get("listbox_items"):
        for item in modify_patch_state["listbox_items"]:
            files_listbox.insert("", "end", values=item)
        
        if modify_patch_state.get("selected_files"):
            for item_id in files_listbox.get_children():
                values = files_listbox.item(item_id, "values")
                if values and values[2] in modify_patch_state["selected_files"]:
                    files_listbox.selection_add(item_id)
        
        restore_patch_form_state(buttons_frame, modify_patch_state)
    else:
        refresh_patch_files(files_listbox, patch_details)

    
    refresh_file_status_version(files_listbox)
    
    # Update locked files treeview after layout is stable
    if "locked_files_treeview" in buttons_frame:
        root_widget.update()
        context_menu_manager.refresh_available_locked_files(
            buttons_frame["locked_files_treeview"],
            files_listbox
        )
    
    # Create drag and drop callback
    def on_drop_with_state_preservation(event):
        from buttons_function import handle_drop
        handle_drop(event, files_listbox)
        
        if state_manager.current_menu == "modify_patch":
            root = files_listbox.winfo_toplevel()
            save_current_state(root)
            
            if "locked_files_treeview" in buttons_frame:
                context_menu_manager.refresh_available_locked_files(
                    buttons_frame["locked_files_treeview"],
                    files_listbox
                )

    # Set up DnD safely
    def setup_dnd_safely(listbox, buttons_frame, callback) -> None:
        """
        Safely set up drag and drop binding after ensuring widget is fully ready.
        
        Args:
            listbox: The treeview widget to bind DnD to
            buttons_frame: Dictionary containing UI references
            callback: The callback function to execute on drop
        """
        def schedule_dnd_binding():
            try:
                if not listbox.winfo_exists():
                    return False
                    
                # Get root window through widget path traversal
                try:
                    root = listbox
                    while root.master:
                        root = root.master
                    root.update_idletasks()
                except (tk.TclError, AttributeError):
                    pass
                    
                # Bind DnD event
                listbox.dnd_bind("<<Drop>>", callback)
                return True
            except (tk.TclError, AttributeError) as e:
                print(f"DnD binding attempt failed, retrying... ({e})")
                log_error(f"DnD binding attempt failed, retrying... ({e})")
                try:
                    listbox.after(100, schedule_dnd_binding)
                except tk.TclError:
                    pass
                return False

    setup_dnd_safely(files_listbox, buttons_frame, on_drop_with_state_preservation)
    
    # Set menu state
    state_manager.current_menu = "modify_patch"


def create_top_frame(
    parent: tk.Widget,
    switch_to_lock_unlock_menu: Callable,
    switch_to_patch_menu: Callable,
    switch_to_patches_menu: Callable,
    switch_to_modify_patch_menu: Callable,
    selected_menu: str,
) -> tk.Frame:
    """
    Create the top frame with navigation buttons.
    """
    menu_button_frame = tk.Frame(parent)
    menu_button_frame.pack(fill="x", pady=5)

    # Button configurations
    modify_patch_state = state_manager.get_state("modify_patch")
    patch_details = modify_patch_state.get("patch_details") if modify_patch_state else None

    buttons = [
        ("Lock/Unlock", switch_to_lock_unlock_menu, "lock_unlock"),
        ("Create Patch", switch_to_patch_menu, "patch"),
        ("Patches List", switch_to_patches_menu, "patches"),
        ("Modify Patch", 
         lambda: switch_to_modify_patch_menu(patch_details) if patch_details else switch_to_patches_menu(), 
         "modify_patch"),
    ]

    for text, command, menu in buttons:
        is_selected = selected_menu == menu
        tk.Button(
            menu_button_frame,
            text=text,
            command=command,
            background="grey" if is_selected else None,
            width=15,
        ).pack(side="left", padx=5, pady=5)

    return menu_button_frame


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


def check_latest_version(root: tk.Tk) -> None:
    """Check if a newer version of the application is available."""
    try:
        random_number = random.randint(1, 1000000)
        url = f"https://raw.githubusercontent.com/CArchambault00/SVNManager/main/latest_version.txt?nocache={random_number}"

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
            if messagebox.askyesno("Update Available", 
                                 f"A new version ({latest_version}) is available.\nDo you want to open the download page?"):
                release_url = f"https://github.com/CArchambault00/SVNManager/releases/tag/{latest_version}"
                webbrowser.open(release_url)
            sys.exit(0)

    except Exception as e:
        error_msg = f"Failed to check for latest version: {e}"
        print(error_msg)
        log_error(error_msg)


def save_file_listbox_state_to_manager(file_listbox, menu_name: str) -> None:
    """Save the state of a file listbox to the state manager"""
    selected_files = []
    listbox_items = []
    
    for item_id in file_listbox.get_children():
        values = file_listbox.item(item_id, "values")
        listbox_items.append(values)
        if item_id in file_listbox.selection():
            selected_files.append(values[2])  # File path is at index 2
    
    state_manager.save_state(menu_name, 
                           selected_files=selected_files, 
                           listbox_items=listbox_items)
    
    # Also save the form state if applicable
    if menu_name in ["patch", "modify_patch"]:
        # Find the parent root to search for form widgets
        root = file_listbox.winfo_toplevel()
        save_patch_form_state(root, menu_name)


def setup_dnd_safely(listbox, buttons_frame, callback) -> None:
    """
    Safely set up drag and drop binding after ensuring widget is fully ready.
    
    Args:
        listbox: The treeview widget to bind DnD to
        buttons_frame: Dictionary containing UI references
        callback: The callback function to execute on drop
    """
    def schedule_dnd_binding():
        try:
            if not listbox.winfo_exists():
                return False
                
            # Get root window through widget path traversal
            try:
                root = listbox
                while root.master:
                    root = root.master
                root.update_idletasks()
            except (tk.TclError, AttributeError):
                pass
                
            # Bind DnD event
            listbox.dnd_bind("<<Drop>>", callback)
            return True
        except (tk.TclError, AttributeError) as e:
            print(f"DnD binding attempt failed, retrying... ({e})")
            log_error(f"DnD binding attempt failed, retrying... ({e})")
            try:
                listbox.after(100, schedule_dnd_binding)
            except tk.TclError:
                pass
            return False

    # Initial attempt after a short delay
    listbox.after(50, schedule_dnd_binding)

def setup_gui() -> tk.Tk:
    """Initialize and set up the GUI for the application."""
    global root
    root = TkinterDnD.Tk()  # Initialize TkinterDnD root window 
    
    # Set up icon path based on whether we're running from a bundle
    if getattr(sys, 'frozen', False):  # Running as a PyInstaller bundle
        bundle_dir = sys._MEIPASS
    else:
        bundle_dir = os.path.abspath(".")

    icon_path = os.path.join(bundle_dir, "SVNManagerIcon.ico")
        
    root.iconbitmap(icon_path)
    root.title("SVN Manager")
    root.geometry("1000x600")

    # Check for the latest version
    check_latest_version(root)

    # Initialize native topbar and menus
    initialize_native_topbar(root, APP_VERSION)
    
    # Check configuration before switching to initial menu
    config = load_config()
    if not config.get("username"):
        messagebox.showwarning("Setup Required", "Please set your username in the Config menu")
    elif not config.get("active_profile"):
        messagebox.showwarning("Setup Required", "Please select or create a profile in the Profile menu")
    else:
        switch_to_lock_unlock_menu()
    
    return root

def get_root_window() -> Optional[tk.Tk]:
    """Get the root window from the widget hierarchy."""
    try:
        # Try to get the default root window
        if tk._default_root:
            # Check if it's already the right type
            if isinstance(tk._default_root, (tk.Tk, TkinterDnD.Tk)):
                return tk._default_root
            # Look through children for TkinterDnD window
            for child in tk._default_root.winfo_children():
                if isinstance(child, (tk.Tk, TkinterDnD.Tk)):
                    return child
        return None
    except:
        return None

def ensure_root_widget(root_widget=None) -> Optional[tk.Tk]:
    """
    Ensure we have a valid root widget, getting it from hierarchy if needed.
    Returns None if no valid root can be found.
    """
    if root_widget is not None:
        return root_widget
        
    # Try to get root from tkinter's default root
    if tk._default_root:
        return tk._default_root
    
    return None


if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()
import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES
from typing import Callable
from patches_operations import get_selected_patch, refresh_patches
from buttons_function import select_all_rows, deselect_all_rows, handle_drop, remove_selected_patch,view_selected_file_native_diff,lock_selected_files, unlock_selected_files,modify_patch,build_existing_patch,view_patch_files
from svn_operations import refresh_locked_files, refresh_file_status_version, lock_files, unlock_files
from datetime import datetime
from context_menu import context_menu_manager

# Constants for column configurations
TREEVIEW_COLUMNS = [
    ("Patch Version", 100),
    ("Comments", 250),
    ("Size", 50),
    ("Username", 100),
    ("Date", 210),
]

LISTBOX_COLUMNS = [
    ("Status", 60),
    ("Version", 60),
    ("Files Path", 400),
    ("Lock Date", 120),
]

def add_scrollbars(widget: ttk.Treeview, parent: tk.Widget) -> None:
    """
    Add vertical and horizontal scrollbars to a Treeview or Listbox widget.
    """
    v_scrollbar = tk.Scrollbar(parent, orient="vertical", command=widget.yview)
    widget.configure(yscrollcommand=v_scrollbar.set)
    v_scrollbar.pack(side="right", fill="y")

    h_scrollbar = tk.Scrollbar(parent, orient="horizontal", command=widget.xview)
    widget.configure(xscrollcommand=h_scrollbar.set)
    h_scrollbar.pack(side="bottom", fill="x")

def refresh_patches_from_menu(listbox):
    """Refresh patches from context menu"""
    from config import load_config
    config = load_config()
    username = config.get("username")
    # Get the active prefix (need to check parent widget)
    from app import find_patch_prefix_combobox
    root = listbox.winfo_toplevel()
    prefix_combo = find_patch_prefix_combobox(root)
    prefix = prefix_combo.get() if prefix_combo else "S"
    refresh_patches(listbox, False, prefix, username)

def remove_selected_items(listbox: ttk.Treeview) -> None:
    """Remove selected items from the listbox."""
    selected_items = listbox.selection()
    for item in selected_items:
        listbox.delete(item)

def create_patches_treeview(parent: tk.Widget, switch_to_modify_patch_menu: Callable = None) -> ttk.Treeview:
    """
    Create a Treeview widget to display patches.
    """
    treeview = ttk.Treeview(
        parent,
        columns=[col[0] for col in TREEVIEW_COLUMNS],
        show="headings",
        selectmode="browse",
    )

    for col_name, col_width in TREEVIEW_COLUMNS:
        treeview.heading(col_name, text=col_name)
        treeview.column(col_name, width=col_width, stretch=tk.NO)
    treeview.bind("<Button-1>", lambda event: deselect_all_rows(event, treeview))
    add_scrollbars(treeview, parent)
    context_menu_manager.create_patches_menu(treeview, switch_to_modify_patch_menu)  # Pass the callback
    
    treeview.pack(expand=True, fill="both")
    return treeview

def create_file_listbox(parent: tk.Widget, menu_name: str = "filebox") -> ttk.Treeview:
    """Create a Listbox widget to display files with drag-and-drop support."""
    listbox = ttk.Treeview(
        parent,
        columns=[col[0] for col in LISTBOX_COLUMNS],
        show="headings",
        selectmode="extended",  # Allow multiple selection
    )

    for col_name, col_width in LISTBOX_COLUMNS:
        listbox.heading(col_name, text=col_name, command=lambda _col=col_name: sort_treeview_column(listbox, _col, False))
        listbox.column(col_name, width=col_width, stretch=tk.NO)

    add_scrollbars(listbox, parent)
    context_menu_manager.create_files_menu(listbox, menu_name=menu_name)  # Use context menu manager directly

    listbox.pack(expand=True, fill="both")
    listbox.bind("<Control-a>", lambda event: select_all_rows(event, listbox))
    listbox.bind("<Button-1>", lambda event: deselect_all_rows(event, listbox))

    # Enable drag-and-drop
    listbox.drop_target_register(DND_FILES)
    listbox.dnd_bind("<<Drop>>", lambda event: handle_drop(event, listbox))

    return listbox

def sort_treeview_column(treeview: ttk.Treeview, col: str, reverse: bool) -> None:
    """
    Sort the Treeview column.
    """
    data = [(treeview.set(child, col), child) for child in treeview.get_children('')]

    # Sort by date if the column is "Lock Date"
    if col == "Lock Date":
        data.sort(key=lambda item: parse_date(item[0]), reverse=reverse)
    else:
        data.sort(reverse=reverse)

    for index, (_, child) in enumerate(data):
        treeview.move(child, '', index)

    # Reverse the sorting order for the next click
    treeview.heading(col, command=lambda: sort_treeview_column(treeview, col, not reverse))

def parse_date(date_str: str) -> datetime:
    """
    Parse a date string into a datetime object. Return a default date if parsing fails.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.min  # Default to the earliest possible date

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
    selected_patch = get_selected_patch()
    menu_button_frame = tk.Frame(parent)
    menu_button_frame.pack(fill="x", pady=5)

    # Button configurations
    buttons = [
        ("Lock/Unlock", switch_to_lock_unlock_menu, "lock_unlock"),
        ("Create Patch", switch_to_patch_menu, "patch"),
        ("Patches List", switch_to_patches_menu, "patches"),
        ("Modify Patch", lambda: switch_to_modify_patch_menu() if selected_menu == "modify_patch" else (switch_to_modify_patch_menu(selected_patch) if selected_patch else switch_to_patches_menu()), "modify_patch"),
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

def remove_and_return_selected_files(listbox):
    """Remove selected files from patch and return them to available locked files if they're locked by the user"""
    from config import load_config
    from svn_operations import get_file_info
    
    selected_items = listbox.selection()
    if not selected_items:
        return
        
    # Find the locked files treeview
    locked_files_treeview = find_locked_files_treeview(listbox)
    if not locked_files_treeview:
        # Just remove the files if we can't find the locked files treeview
        for item in selected_items:
            listbox.delete(item)
        return
    
    username = load_config().get("username", "")
    
    # Get existing files in locked_files_treeview to avoid duplicates
    existing_locked_files = set()
    for item in locked_files_treeview.get_children():
        file_path = locked_files_treeview.item(item, "values")[2]
        existing_locked_files.add(file_path)
    
    for item in selected_items:
        values = listbox.item(item, "values")
        file_path = values[2]
        
        # Check if file is locked by the current user
        is_locked_by_user, lock_owner, revision, lock_date = get_file_info(file_path)
        
        # Add to locked files treeview if it's locked by current user and not already there
        if is_locked_by_user and file_path not in existing_locked_files:
            locked_files_treeview.insert("", "end", values=values)
        
        # Remove from main files treeview
        listbox.delete(item)

def refresh_available_locked_files_from_menu(listbox):
    """Refresh locked files from context menu"""
    main_treeview = find_main_treeview(listbox)
    if main_treeview:
        from create_buttons import refresh_available_locked_files
        refresh_available_locked_files(listbox, main_treeview)

def find_locked_files_treeview(listbox):
    """Find the locked files treeview that corresponds to this main treeview"""
    # Go up to find the common parent
    parent = listbox.master
    while parent.master and not isinstance(parent, tk.Toplevel) and not isinstance(parent, tk.Tk):
        parent = parent.master
        
    # Look for the bottom_left_frame, then find the locked_files_frame
    for frame in parent.winfo_children():
        if frame.grid_info().get('row') == 1 and frame.grid_info().get('column') == 0:  # bottom_left_frame
            # In the frame, find the container that has both treeviews
            for container in frame.winfo_children():
                if isinstance(container, tk.Frame):
                    # Look for the locked files frame (second LabelFrame)
                    frames = [w for w in container.winfo_children() if isinstance(w, tk.LabelFrame)]
                    if len(frames) >= 2:
                        locked_files_frame = frames[1]  # Second LabelFrame should be locked files
                        # Find the treeview in this frame
                        for widget in locked_files_frame.winfo_children():
                            if isinstance(widget, ttk.Treeview):
                                return widget
    return None

def find_main_treeview(listbox):
    """Find the main treeview (patch files) that corresponds to this locked files treeview"""
    # Go up to find the parent LabelFrame
    parent = listbox.master
    while parent and not isinstance(parent, tk.LabelFrame):
        parent = parent.master
    
    if not parent:
        return None
    
    # Find the parent container that holds both label frames
    container = parent.master
    
    # Find all LabelFrames in this container
    if container:
        label_frames = [widget for widget in container.winfo_children() if isinstance(widget, tk.LabelFrame)]
        # The main treeview is in the first LabelFrame (Files for patch)
        if len(label_frames) >= 1 and label_frames[0] != parent:  # Make sure we're not getting the same frame
            # Find the treeview in this frame
            for widget in label_frames[0].winfo_children():
                if isinstance(widget, ttk.Treeview):
                    return widget
    
    # If all else fails, try to find any Treeview in the window hierarchy
    root = listbox.winfo_toplevel()
    for widget in root.winfo_children():
        if isinstance(widget, ttk.Treeview) and widget != listbox:
            return widget
            
    return None
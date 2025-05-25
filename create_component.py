import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES
from typing import Callable
from patches_operations import get_selected_patch
from buttons_function import select_all_files, deselect_all_files, handle_drop
from datetime import datetime

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
    ("Files Path", 800),
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

def create_context_menu(listbox: ttk.Treeview) -> tk.Menu:
    """Create right-click context menu for the listbox."""
    context_menu = tk.Menu(listbox, tearoff=0)
    context_menu.add_command(label="Remove Selected", command=lambda: remove_selected_items(listbox))
    
    def show_context_menu(event):
        if listbox.selection():  # Only show menu if items are selected
            context_menu.post(event.x_root, event.y_root)
    
    listbox.bind("<Button-3>", show_context_menu)
    return context_menu

def remove_selected_items(listbox: ttk.Treeview) -> None:
    """Remove selected items from the listbox."""
    selected_items = listbox.selection()
    for item in selected_items:
        listbox.delete(item)

def create_patches_treeview(parent: tk.Widget) -> ttk.Treeview:
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

    add_scrollbars(treeview, parent)
    treeview.pack(expand=True, fill="both")
    return treeview

def create_file_listbox(parent: tk.Widget) -> ttk.Treeview:
    """
    Create a Listbox widget to display files with drag-and-drop support.
    """
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
    create_context_menu(listbox)  # Add right-click menu

    listbox.pack(expand=True, fill="both")
    listbox.bind("<Control-a>", lambda event: select_all_files(event, listbox))
    listbox.bind("<Button-1>", lambda event: deselect_all_files(event, listbox))

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
        ("Modify Patch", lambda: switch_to_modify_patch_menu(selected_patch) if selected_patch else switch_to_patches_menu, "modify_patch"),
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
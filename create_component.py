import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES
from typing import Callable
from patches_operations import get_selected_patch
from buttons_function import select_all_files, deselect_all_files, handle_drop

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
    )

    for col_name, col_width in LISTBOX_COLUMNS:
        listbox.heading(col_name, text=col_name)
        listbox.column(col_name, width=col_width, stretch=tk.NO)

    add_scrollbars(listbox, parent)

    listbox.pack(expand=True, fill="both")
    listbox.bind("<Control-a>", lambda event: select_all_files(event, listbox))
    listbox.bind("<Button-1>", lambda event: deselect_all_files(event, listbox))

    # Enable drag-and-drop
    listbox.drop_target_register(DND_FILES)
    listbox.dnd_bind("<<Drop>>", lambda event: handle_drop(event, listbox))

    return listbox


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
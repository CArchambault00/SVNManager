import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from dialog import select_svn_folder, set_username

def create_patches_treeview(parent):
    """
    Create a Treeview widget to display patches.
    """
    treeview = ttk.Treeview(parent, columns=("Patch Version", "Comments", "Size", "Username", "Date"), show="headings")
    treeview.heading("Patch Version", text="Patch Version")
    treeview.heading("Comments", text="Comments")
    treeview.heading("Size", text="Size")
    treeview.heading("Username", text="Username")
    treeview.heading("Date", text="Date")
    
    # Set column widths
    treeview.column("Patch Version", width=75)
    treeview.column("Comments", width=250)
    treeview.column("Size", width=50)
    treeview.column("Username", width=50)
    treeview.column("Username", width=50)
    
    # Add scrollbars
    v_scrollbar = tk.Scrollbar(parent, orient="vertical", command=treeview.yview)
    treeview.configure(yscrollcommand=v_scrollbar.set)
    v_scrollbar.pack(side="right", fill="y")
    
    h_scrollbar = tk.Scrollbar(parent, orient="horizontal", command=treeview.xview)
    treeview.configure(xscrollcommand=h_scrollbar.set)
    h_scrollbar.pack(side="bottom", fill="x")
    
    treeview.pack(expand=True, fill="both")
    
    return treeview


def create_file_listbox(parent):
    
    listbox = ttk.Treeview(parent, columns=("Status", "Files Path"), show="headings")
    listbox.heading("Status", text="Status")
    listbox.heading("Files Path", text="Files Path")
    listbox.column("Status", width=60, stretch=tk.NO)  # Set width of Status column to 25%
    listbox.column("Files Path", width=800, stretch=tk.NO)  # Set width of Files Path column

    # Add horizontal scrollbar
    h_scrollbar = tk.Scrollbar(parent, orient="horizontal", command=listbox.xview)
    listbox.configure(xscrollcommand=h_scrollbar.set)
    h_scrollbar.pack(side="bottom", fill="x")

    
    v_scrollbar = tk.Scrollbar(parent, orient="vertical", command=listbox.yview)
    listbox.configure(yscrollcommand=v_scrollbar.set)
    v_scrollbar.pack(side="right", fill="y")

    listbox.pack(expand=True, fill="both")
    listbox.bind("<Control-a>", lambda event: select_all_files(event, listbox))  # Bind to listbox instead of parent
    listbox.bind("<Button-1>", lambda event: deselect_all_files(event, listbox))  # Bind left-click to deselect all

    # Enable drag-and-drop
    listbox.drop_target_register(DND_FILES)
    listbox.dnd_bind('<<Drop>>', lambda event: handle_drop(event, listbox))

    return listbox

def deselect_all_files(event, files_listbox):
    if not files_listbox.identify_row(event.y):  # Check if click is on an empty area
        files_listbox.selection_remove(files_listbox.selection())


def select_all_files(event, files_listbox):
    for item in files_listbox.get_children():
        files_listbox.selection_add(item)

def handle_drop(event, listbox):
    files = listbox.tk.splitlist(event.data)
    for file in files:
        listbox.insert('', 'end', values=(file, ''))


def create_top_frame(parent, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu):
    tk.Label(parent, text="Username:").pack(side="left", padx=5, pady=5)
    entry = tk.Entry(parent)
    entry.config(state=tk.NORMAL)
    entry.pack(side="left", padx=5, pady=5)
    tk.Button(parent, text="Save", command=lambda: set_username(entry)).pack(side="left", padx=5, pady=5)
    tk.Button(parent, text="Select SVN Folder", command=select_svn_folder).pack(side="right", padx=5, pady=5)
    
    button_frame = tk.Frame(parent)
    button_frame.pack(fill="x", pady=5)
    tk.Button(button_frame, text="Lock/Unlock Menu", command=switch_to_lock_unlock_menu).pack(side="left", padx=5, pady=5)
    tk.Button(button_frame, text="Patch Menu", command=switch_to_patch_menu).pack(side="left", padx=5, pady=5)
    tk.Button(button_frame, text="Patches Menu", command=switch_to_patches_menu).pack(side="left", padx=5, pady=5)
    tk.Button(button_frame, text="Modify Patch", command=switch_to_patches_menu).pack(side="left", padx=5, pady=5)
    
    return entry
import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from dialog import select_svn_folder, set_username, select_instant_client_folder
from config import load_config
from patches_operations import get_selected_patch
from buttons_function import select_all_files, deselect_all_files, handle_drop
def create_patches_treeview(parent):
    """
    Create a Treeview widget to display patches.
    """
    treeview = ttk.Treeview(parent, columns=("Patch Version", "Comments", "Size", "Username", "Date"), show="headings", selectmode="browse")
    treeview.heading("Patch Version", text="Patch Version")
    treeview.heading("Comments", text="Comments")
    treeview.heading("Size", text="Size")
    treeview.heading("Username", text="Username")
    treeview.heading("Date", text="Date")
    
    # Set column widths
    treeview.column("Patch Version", width=100, stretch=tk.NO)
    treeview.column("Comments", width=250, stretch=tk.NO)
    treeview.column("Size", width=50, stretch=tk.NO)
    treeview.column("Username", width=100, stretch=tk.NO)
    treeview.column("Date", width=210, stretch=tk.NO)
    
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

def create_top_frame(parent, switch_to_lock_unlock_menu, switch_to_patch_menu, switch_to_patches_menu, switch_to_modify_patch_menu, selected_menu):
    config = load_config()
    username = config.get("username")
    instant_client = config.get("instant_client")
    svn_path = config.get("svn_path")

    selected_patch = get_selected_patch()

    col1_frame = tk.Frame(parent)
    col1_frame.pack(side="left", fill="y", padx=5,)
    
    username_frame = tk.Frame(col1_frame)
    username_frame.pack(fill="x",)
    tk.Label(username_frame, text="Username:").pack(side="left", padx=5,)
    entry = tk.Entry(username_frame)
    entry.config(state=tk.NORMAL)
    if username:
        entry.insert(0, username)
    else:
        entry.config(highlightbackground="red", highlightcolor="red", highlightthickness=2)
    entry.pack(side="left", padx=5,)
    tk.Button(username_frame, text="Save", command=lambda: set_username(entry)).pack(side='left', padx=5,)

    menu_button_frame = tk.Frame(col1_frame)
    menu_button_frame.pack(fill="x", pady=5)
    if selected_menu == "lock_unlock":
        tk.Button(menu_button_frame, text="Lock/Unlock Menu", command=switch_to_lock_unlock_menu, background="grey").pack(side="left", padx=5, pady=5)
    else:
        tk.Button(menu_button_frame, text="Lock/Unlock Menu", command=switch_to_lock_unlock_menu).pack(side="left", padx=5, pady=5)
    if selected_menu == "patch":
        tk.Button(menu_button_frame, text="Patch Menu", command=switch_to_patch_menu, background="grey").pack(side="left", padx=5, pady=5)
    else:
        tk.Button(menu_button_frame, text="Patch Menu", command=switch_to_patch_menu).pack(side="left", padx=5, pady=5)
    if selected_menu == "patches":
        tk.Button(menu_button_frame, text="Patches Menu", command=switch_to_patches_menu, background="grey").pack(side="left", padx=5, pady=5)
    else:
        tk.Button(menu_button_frame, text="Patches Menu", command=switch_to_patches_menu).pack(side="left", padx=5, pady=5)
    if selected_menu == "modify_patch" and selected_patch != None:
        tk.Button(menu_button_frame, text="Modify Patch", command=lambda:switch_to_modify_patch_menu(selected_patch),  background="grey").pack(side="left", padx=5, pady=5)
    else:
        if selected_patch != None:
            tk.Button(menu_button_frame, text="Modify Patch", command=lambda:switch_to_modify_patch_menu(selected_patch)).pack(side="left", padx=5, pady=5)
        else:
            tk.Button(menu_button_frame, text="Modify Patch", command=switch_to_patches_menu).pack(side="left", padx=5, pady=5)
   

    # Create a frame for the buttons and arrange them in a column
    col2_frame = tk.Frame(parent)
    col2_frame.pack(side="right", padx=5, pady=5)
    instant_client_button = tk.Button(col2_frame, text="Set INSTANT_CLIENT", command=lambda: select_instant_client_folder(instant_client_button))
    instant_client_button.pack(fill="x", pady=2)
    svn_path_button = tk.Button(col2_frame, text="Set SVN Folder", command=lambda: select_svn_folder(svn_path_button))
    svn_path_button.pack(fill="x", pady=2)
    if not svn_path:
        svn_path_button.config(background="red")
    if not instant_client:
        instant_client_button.config(background="red")
    
    return entry,instant_client_button,svn_path_button
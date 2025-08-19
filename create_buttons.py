import tkinter as tk
from tkinter import ttk
from patch_generation import generate_patch
from buttons_function import insert_next_version, deselect_all_rows, select_all_rows
from patches_operations import refresh_patches, update_patch
from config import load_config
from db_handler import dbClass
from tkinter import messagebox
from profiles import get_profile
from create_component import LISTBOX_COLUMNS  # Import add_scrollbars from create_component
from text_widget_utils import ensure_text_widget_visible
from context_menu import context_menu_manager

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

def create_button_frame(parent, files_listbox):
    
    tk.Frame(parent, height=20).pack(side="top")
   
    tk.Frame(parent, height=20).pack(side="top")
   
    # Remove "Refresh Locked Files" button
    
    # Add separator before the View Diff button
    tk.Frame(parent, height=20).pack(side="top")

def create_button_frame_patch(parent, files_listbox, locked_files_frame, patch_state=None):
    ## Patch Version and description panel
    # Create a container for the right side
    right_panel = tk.Frame(parent)
    right_panel.pack(fill="both", expand=True)
    
    # Patch Version section
    patch_version_frame = tk.LabelFrame(right_panel, text="Patch version:")
    patch_version_frame.pack(side="top", fill="x", padx=5, pady=5)
    
    # Get active profile's patch prefix
    config = load_config()
    active_profile = get_profile(config.get("active_profile"))
    if not active_profile or not active_profile.patch_prefix:
        messagebox.showerror("Error", "No active profile or patch prefix configured")
        return {}

    # Dropdown for patch prefix (disabled, showing active profile's prefix)
    patch_version_prefixe = ttk.Combobox(patch_version_frame, values=[active_profile.patch_prefix[0]], width=3, state="disabled")
    patch_version_prefixe.set(active_profile.patch_prefix[0])
    patch_version_prefixe.pack(side="left", padx=5, pady=5)

    # Immediately restore patch version if available
    patch_version_entry = tk.Entry(patch_version_frame, width=14)
    patch_version_entry.pack(side="left", padx=5, pady=5)
    
    # Restore patch version text immediately if available
    if patch_state and patch_state.get("patch_version"):
        patch_version_entry.insert(0, patch_state["patch_version"])
    
    # Next Version Button
    next_btn = tk.Button(patch_version_frame, text="Next", 
                         command=lambda: insert_next_version(patch_version_prefixe.get(), patch_version_entry), 
                         background="#80DDFF")
    next_btn.pack(side="right", padx=5, pady=5)

    # Patch Description section with proper rendering
    patch_description_frame = tk.LabelFrame(right_panel, text="Patch description:")
    patch_description_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

    # Create the Text widget with configurations for better rendering
    patch_description_entry = tk.Text(
        patch_description_frame,
        height=10,
        width=40,
        wrap=tk.WORD,  # Enable word wrapping
        relief=tk.SUNKEN,  # Add visual border
        padx=5,  # Add internal padding
        pady=5
    )
    patch_description_entry.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    # Force render and update the Text widget
    patch_description_entry.update_idletasks()
    
    # Restore text content if available
    if patch_state and patch_state.get("patch_description"):
        ensure_text_widget_visible(patch_description_entry, patch_state["patch_description"])
        
    # Force another update to ensure visibility
    patch_description_entry.update()
    right_panel.update()

    # Unlock files checkbox
    unlock_files = tk.BooleanVar(value=(patch_state.get("unlock_files", False) if patch_state else False))
    unlock_files_checkbox = tk.Checkbutton(
        right_panel,
        text="unlock files after patch generation",
        variable=unlock_files,
    )
    unlock_files_checkbox.pack(side="left", padx=5, pady=5)

    # Generate patch button
    generate_btn = tk.Button(
        right_panel, 
        text="Generate patch", 
        command=lambda: generate_patch(
            [files_listbox.item(item, "values")[2] for item in files_listbox.get_children()],  # All files, not just selected
            patch_version_prefixe.get(), 
            patch_version_entry.get(), 
            patch_description_entry.get("1.0", tk.END).strip(), 
            unlock_files.get()
        ),
        background="#FF8080"
    )
    generate_btn.pack(side="right", padx=5, pady=5)

    # Now create the treeview for available locked files
    locked_files_treeview = ttk.Treeview(
        locked_files_frame,
        columns=[col[0] for col in LISTBOX_COLUMNS],
        show="headings",
        selectmode="extended",
        height=8  # Set a reasonable height for better visibility
    )
    
    locked_files_treeview.bind("<Button-1>", lambda event: deselect_all_rows(event, locked_files_treeview))
    locked_files_treeview.bind("<Control-a>", lambda event: select_all_rows(event, locked_files_treeview))
    for col_name, col_width in LISTBOX_COLUMNS:
        locked_files_treeview.heading(col_name, text=col_name)
        locked_files_treeview.column(col_name, width=col_width, stretch=tk.NO)
    
    # Add scrollbars for the locked files treeview
    v_scrollbar = tk.Scrollbar(locked_files_frame, orient="vertical", command=locked_files_treeview.yview)
    locked_files_treeview.configure(yscrollcommand=v_scrollbar.set)
    v_scrollbar.pack(side="right", fill="y")
    
    h_scrollbar = tk.Scrollbar(locked_files_frame, orient="horizontal", command=locked_files_treeview.xview)
    locked_files_treeview.configure(xscrollcommand=h_scrollbar.set)
    h_scrollbar.pack(side="bottom", fill="x")
    
    locked_files_treeview.bind("<Control-a>", lambda event: select_all_rows(event, locked_files_treeview))
    locked_files_treeview.bind("<Button-1>", lambda event: deselect_all_rows(event, locked_files_treeview))
    locked_files_treeview.pack(side="left", fill="both", expand=True)
    
    # Create context menus
    context_menu_manager.create_files_menu(files_listbox, menu_name='patch_files')  # Create context menu for main treeview
    context_menu_manager.create_files_menu(locked_files_treeview, menu_name='locked_files')  # Create context menu for locked files treeview

    # Add a simple refresh button at the bottom of the locked files frame
    refresh_button = tk.Button(
        locked_files_frame, 
        text="Refresh Locked Files", 
        command=lambda: context_menu_manager.refresh_available_locked_files(locked_files_treeview, files_listbox),
        background="#80DDFF"
    )
    refresh_button.pack(side="bottom", pady=5)

    # We won't call refresh_available_locked_files here, it will be called from the app.py
    
    # Return widget references for state management
    return {
        "patch_version_prefixe": patch_version_prefixe,
        "patch_version_entry": patch_version_entry,
        "patch_description_entry": patch_description_entry,
        "unlock_files": unlock_files,
        "locked_files_treeview": locked_files_treeview
    }

def create_button_frame_modify_patch(parent, files_listbox, patch_details, switch_to_modify_patch_menu, locked_files_frame):
    ## Patch Version and description panel
    # Create a container for the right side
    right_panel = tk.Frame(parent)
    right_panel.pack(fill="both", expand=True)
    
    # Patch Version section
    patch_version_frame = tk.LabelFrame(right_panel, text="Patch version:")
    patch_version_frame.pack(side="top", fill="x", padx=5, pady=5)

    # Get the original patch prefix
    patch_prefixe = patch_details['NAME'][0]  # Extract the prefix from the selected patch's version

    # Create disabled combobox with only the original prefix
    patch_version_prefixe = ttk.Combobox(patch_version_frame, values=[patch_prefixe], width=3, state="disabled")
    patch_version_prefixe.set(patch_prefixe)  # Set to the selected patch's version
    patch_version_prefixe.pack(side="left", padx=5, pady=5)

    patch_version_entry = tk.Entry(patch_version_frame, width=14)
    patch_version_entry.insert(0, patch_details['NAME'][1:])  # Set to the selected patch's version number
    patch_version_entry.pack(side="left", padx=5, pady=5)

    # Next Version Button
    next_btn = tk.Button(patch_version_frame, text="Next", 
                         command=lambda: insert_next_version(patch_version_prefixe.get(), patch_version_entry), 
                         background="#80DDFF")
    
    next_btn.pack(side="right", padx=5, pady=5)

    # Patch Description section with proper rendering
    patch_description_frame = tk.LabelFrame(right_panel, text="Patch description:")
    patch_description_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)

    # Create the Text widget with configurations for better rendering
    patch_description_entry = tk.Text(
        patch_description_frame,
        height=10,
        width=40,
        wrap=tk.WORD,  # Enable word wrapping
        relief=tk.SUNKEN,  # Add visual border
        padx=5,  # Add internal padding
        pady=5
    )
    patch_description_entry.pack(side="top", fill="both", expand=True, padx=5, pady=5)
    
    # Force render and update the Text widget
    patch_description_entry.update_idletasks()
    
    # Restore text content if available
    if patch_details.get('COMMENTS'):
        ensure_text_widget_visible(patch_description_entry, patch_details['COMMENTS'])
        
    # Force another update to ensure visibility
    patch_description_entry.update()
    right_panel.update()

    # Unlock files checkbox
    unlock_files = tk.BooleanVar(value=False)
    unlock_files_checkbox = tk.Checkbutton(
        right_panel,
        text="unlock files after patch generation",
        variable=unlock_files,
    )
    unlock_files_checkbox.pack(side="left", padx=5, pady=5)

    # Update patch button
    update_btn = tk.Button(
        right_panel, 
        text="Update Patch", 
        command=lambda: update_patch(
            [files_listbox.item(item, "values")[2] for item in files_listbox.get_children()],  # All files, not just selected
            patch_details["PATCH_ID"], 
            patch_version_prefixe.get(), 
            patch_version_entry.get(), 
            patch_description_entry.get("1.0", tk.END).strip(), 
            switch_to_modify_patch_menu, 
            unlock_files.get()
        ), 
        background="#FF8080"
    )
    update_btn.pack(side="right", padx=5, pady=5)

    # Now create the treeview for available locked files
    locked_files_treeview = ttk.Treeview(
        locked_files_frame,
        columns=[col[0] for col in LISTBOX_COLUMNS],
        show="headings",
        selectmode="extended",
        height=8  # Set a reasonable height for better visibility
    )
    
    for col_name, col_width in LISTBOX_COLUMNS:
        locked_files_treeview.heading(col_name, text=col_name)
        locked_files_treeview.column(col_name, width=col_width, stretch=tk.NO)
    
    # Add scrollbars for the locked files treeview
    v_scrollbar = tk.Scrollbar(locked_files_frame, orient="vertical", command=locked_files_treeview.yview)
    locked_files_treeview.configure(yscrollcommand=v_scrollbar.set)
    v_scrollbar.pack(side="right", fill="y")
    
    h_scrollbar = tk.Scrollbar(locked_files_frame, orient="horizontal", command=locked_files_treeview.xview)
    locked_files_treeview.configure(xscrollcommand=h_scrollbar.set)
    h_scrollbar.pack(side="bottom", fill="x")
    
    locked_files_treeview.pack(side="left", fill="both", expand=True)
    
    # Create context menus
    context_menu_manager.create_files_menu(files_listbox, menu_name="patch_files")  # Create context menu for main treeview
    context_menu_manager.create_files_menu(locked_files_treeview, menu_name="locked_files")  # Create context menu for locked files treeview

    # Add a simple refresh button at the bottom of the locked files frame
    refresh_button = tk.Button(
        locked_files_frame, 
        text="Refresh Locked Files", 
        command=lambda: context_menu_manager.refresh_available_locked_files(locked_files_treeview, files_listbox),
        background="#80DDFF"
    )
    refresh_button.pack(side="bottom", pady=5)

    # We won't call refresh_available_locked_files here, it will be called from the app.py
    
    # Return widget references for state management
    return {
        "patch_version_prefixe": patch_version_prefixe,
        "patch_version_entry": patch_version_entry,
        "patch_description_entry": patch_description_entry,
        "unlock_files": unlock_files,
        "locked_files_treeview": locked_files_treeview
    }

def create_button_frame_patches(parent, patches_listbox, switch_to_modify_patch_menu):
    config = load_config()
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    db = dbClass()
    prefixes = db.get_prefix_list()

    patch_version_prefixe = ttk.Combobox(patch_version_frame, values=prefixes, width=3)
    patch_version_prefixe.set(config.get("patch_prefix", "S"))  # default value
    patch_version_prefixe.pack(side="left", padx=5)
    username = config.get("username")
    # On patch version change, refresh the patches
    patch_version_prefixe.bind("<<ComboboxSelected>>", lambda event: refresh_patches(patches_listbox, False, patch_version_prefixe.get(), username))

    # Return widget references for state management
    return {
        "patch_version_prefixe": patch_version_prefixe
    }
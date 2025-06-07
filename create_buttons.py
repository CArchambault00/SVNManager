import tkinter as tk
from tkinter import ttk
from svn_operations import lock_files, unlock_files, get_all_locked_files
from buttons_function import lock_selected_files, unlock_selected_files
from patch_generation import generate_patch
from buttons_function import insert_next_version, modify_patch, build_existing_patch, view_patch_files, view_selected_file_native_diff
from patches_operations import refresh_patches, update_patch
from config import load_config
from db_handler import dbClass
from tkinter import messagebox
from profiles import get_profile
from create_component import LISTBOX_COLUMNS, add_scrollbars  # Import add_scrollbars from create_component
from text_widget_utils import ensure_text_widget_visible, get_text_content

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
    tk.Button(parent, text="Lock All", command=lambda: lock_files([files_listbox.item(item, "values")[2] for item in files_listbox.get_children()], files_listbox), background="#FF8080", width=15).pack(side="top", pady=5)
    tk.Button(parent, text="Lock Selected", command=lambda: lock_selected_files(files_listbox), background="#FF8080", width=15).pack(side="top", pady=5)
    tk.Frame(parent, height=20).pack(side="top")
    tk.Button(parent, text="Unlock All", command=lambda: unlock_files([files_listbox.item(item, "values")[2] for item in files_listbox.get_children()], files_listbox), background="#44FF80", width=15).pack(side="top", pady=5)
    tk.Button(parent, text="Unlock Selected", command=lambda: unlock_selected_files(files_listbox), background="#44FF80", width=15).pack(side="top", pady=5)
    
    # Remove "Refresh Locked Files" button
    
    # Add separator before the View Diff button
    tk.Frame(parent, height=20).pack(side="top")
    
    # Add View Diff button
    diff_button = tk.Button(parent, text="View Diff", command=lambda: view_selected_file_native_diff(files_listbox), background="#FCFF80", width=15)
    diff_button.pack(side="top", pady=5)
    
    # Enable/disable View Diff button based on selection
    def on_selection_change(event):
        if len(files_listbox.selection()) == 1:
            diff_button.config(state="normal")
        else:
            diff_button.config(state="disabled")
    
    # Bind selection change events
    files_listbox.bind("<<TreeviewSelect>>", on_selection_change)
    
    # Initial state of the diff button (disabled by default)
    diff_button.config(state="disabled")

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
    
    # Create context menus using the create_context_menu function from create_component
    from create_component import create_context_menu
    create_context_menu(files_listbox, "files")  # Create context menu for main treeview
    create_context_menu(locked_files_treeview, "locked_files")  # Create context menu for locked files treeview

    # Add a simple refresh button at the bottom of the locked files frame
    refresh_button = tk.Button(
        locked_files_frame, 
        text="Refresh Locked Files", 
        command=lambda: refresh_available_locked_files(locked_files_treeview, files_listbox),
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
    
    # Create context menus using the create_context_menu function
    from create_component import create_context_menu
    create_context_menu(files_listbox, "files")  # Create context menu for main treeview
    create_context_menu(locked_files_treeview, "locked_files")  # Create context menu for locked files treeview

    # Add a simple refresh button at the bottom of the locked files frame
    refresh_button = tk.Button(
        locked_files_frame, 
        text="Refresh Locked Files", 
        command=lambda: refresh_available_locked_files(locked_files_treeview, files_listbox),
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
    patch_version_prefixe.set("S")  # default value
    patch_version_prefixe.pack(side="left", padx=5)
    username = config.get("username")
    # On patch version change, refresh the patches
    patch_version_prefixe.bind("<<ComboboxSelected>>", lambda event: refresh_patches(patches_listbox, False, patch_version_prefixe.get(), username))

    # Remove "Refresh Patches" button

    # Add a button to modify the selected patch
    root = parent.winfo_toplevel()  # Get root window reference
    tk.Button(parent, text="Modify Patch", 
              command=lambda: modify_patch([patches_listbox.item(item, "values") for item in patches_listbox.selection()], 
                                        lambda p: switch_to_modify_patch_menu(p, root)), 
              background="#FF8080", width=15).pack(side="top", pady=5)

    # Generate patch
    tk.Button(parent, text="Build Patch", command=lambda: build_existing_patch([patches_listbox.item(item, "values") for item in patches_listbox.selection()]), background="#FCFF80", width=15).pack(side="top", pady=5)

    # View patch files
    tk.Button(parent, text="View Patch Files", command=lambda: view_patch_files([patches_listbox.item(item, "values") for item in patches_listbox.selection()]), background="#44FF80", width=15).pack(side="top", pady=5)
    
    # Return widget references for state management
    return {
        "patch_version_prefixe": patch_version_prefixe
    }

def refresh_available_locked_files(locked_files_treeview, main_files_treeview):
    """
    Refresh the list of locked files, excluding those already in the main treeview
    """
    try:
        # Clear the locked files treeview
        locked_files_treeview.delete(*locked_files_treeview.get_children())
        
        # Get all locked files
        locked_files = get_all_locked_files()
        
        # Get the list of files already in the main treeview
        existing_files = set()
        for item in main_files_treeview.get_children():
            file_path = main_files_treeview.item(item, "values")[2]
            existing_files.add(file_path)
        
        # Add locked files that aren't already in the main treeview
        for file_path, revision, lock_date in locked_files:
            if file_path not in existing_files:
                locked_files_treeview.insert(
                    "", "end",
                    values=("locked", revision, file_path, lock_date)
                )
                
        # Make sure the widgets are updated properly
        locked_files_treeview.update()
    except Exception as e:
        print(f"Error refreshing locked files: {e}")
        messagebox.showerror("Error", f"Failed to refresh available locked files:\n{e}")

def add_selected_to_main_treeview(locked_files_treeview, main_files_treeview):
    """
    Add selected files from the locked files treeview to the main treeview
    """
    selected_items = locked_files_treeview.selection()
    if not selected_items:
        messagebox.showwarning("No Selection", "Please select files to add")
        return
    
    # Get the list of files already in the main treeview
    existing_files = set()
    for item in main_files_treeview.get_children():
        file_path = main_files_treeview.item(item, "values")[2]
        existing_files.add(file_path)
    
    # Add selected files to main treeview if they're not already there
    files_added = 0
    for item in selected_items:
        values = locked_files_treeview.item(item, "values")
        file_path = values[2]
        
        if file_path not in existing_files:
            main_files_treeview.insert("", "end", values=values)
            files_added += 1
            existing_files.add(file_path)
    
    # Remove the added files from the locked files treeview
    for item in selected_items:
        locked_files_treeview.delete(item)
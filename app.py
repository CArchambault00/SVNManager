import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from config import load_config, save_config
from shared_operations import load_locked_files
from file_operations import generate_patch
from svn_operations import lock_files, unlock_files, refresh_locked_files as refresh_locked_files_svn
from version_operation import next_version
from patches_operations import refresh_patches_db

def select_svn_folder():
    folder = filedialog.askdirectory(title="Select SVN Folder")
    if folder:
        config = load_config()
        config["svn_path"] = folder
        save_config(config)

def set_username(username_entry):
    username = username_entry.get()
    if username:
        config = load_config()
        config["username"] = username
        save_config(config)
        messagebox.showinfo("Info", "Username saved!")

def refresh_locked_files(files_listbox):
    refresh_locked_files_svn(files_listbox)

def refresh_patches(treeview, temp, module,  username):
    refresh_patches_db(treeview, temp, module,  username)

def refresh_username(username_entry):
    config = load_config()
    username_entry.delete(0, tk.END)
    if config.get("username"):
        username_entry.insert(0, config["username"])
    else:
        messagebox.showwarning("Warning", "Please set the username!")

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


def switch_to_lock_unlock_menu():
    for widget in root.winfo_children():
        widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    username_entry = create_top_frame(top_frame)
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame(bottom_right_frame, files_listbox)
    refresh_locked_files(files_listbox)
    refresh_username(username_entry)

def switch_to_patch_menu():
    for widget in root.winfo_children():
        widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    username_entry = create_top_frame(top_frame)
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame_patch(bottom_right_frame, files_listbox)
    refresh_locked_files(files_listbox)
    refresh_username(username_entry)

def switch_to_patches_menu():
    for widget in root.winfo_children():
        widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    username_entry = create_top_frame(top_frame)
    refresh_username(username_entry)
    
    # Create a Treeview to display patches
    patches_listbox = create_patches_treeview(bottom_left_frame)
    create_button_frame_patches(bottom_right_frame, patches_listbox)
    username = load_config().get("username")
    refresh_patches(patches_listbox, False, "J", username)  # Populate the Treeview with patches

def switch_to_modify_patch_menu(patch_details):
    for widget in root.winfo_children():
        widget.destroy()
    top_frame, bottom_left_frame, bottom_right_frame = create_main_layout(root)
    username_entry = create_top_frame(top_frame)
    files_listbox = create_file_listbox(bottom_left_frame)
    create_button_frame_modify_patch(bottom_right_frame, files_listbox, patch_details)
    refresh_locked_files(files_listbox)
    refresh_username(username_entry)

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

def create_top_frame(parent):
    tk.Label(parent, text="Username:").pack(side="left", padx=5, pady=5)
    entry = tk.Entry(parent)
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

def handle_drop(event, listbox):
    files = listbox.tk.splitlist(event.data)
    for file in files:
        listbox.insert('', 'end', values=(file, ''))

def deselect_all_files(event, files_listbox):
    if not files_listbox.identify_row(event.y):  # Check if click is on an empty area
        files_listbox.selection_remove(files_listbox.selection())

def create_button_frame(parent, files_listbox):
    tk.Button(parent, text="Refresh lock files", command=lambda: refresh_locked_files(files_listbox)).pack(side="top", pady=10)

    tk.Button(parent, text="Lock All", command=lambda: lock_files([files_listbox.item(item, "values")[0] for item in files_listbox.get_children()], files_listbox, files_listbox)).pack(side="top", pady=0)
    tk.Button(parent, text="Unlock All", command=lambda: unlock_files([files_listbox.item(item, "values")[0] for item in files_listbox.get_children()], files_listbox, files_listbox)).pack(side="top", pady=10)

    tk.Button(parent, text="Lock Selected", command=lambda: lock_selected_files(files_listbox)).pack(side="top", pady=5)
    tk.Button(parent, text="Unlock Selected", command=lambda: unlock_selected_files(files_listbox)).pack(side="top", pady=5)

def create_button_frame_patch(parent, files_listbox):
    ## Patch Version entry
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    patch_version_label = tk.Label(patch_version_frame, text="Patch Version:")
    patch_version_label.pack(side="left", padx=5)

    # Dropdown for patch letter
    patch_version_letter = ttk.Combobox(patch_version_frame, values=["J", "V", "W"], width=3)
    patch_version_letter.set("J")  # default value
    patch_version_letter.pack(side="left", padx=5)

    patch_version_entry = tk.Entry(patch_version_frame, width=14)
    patch_version_entry.pack(side="left", padx=5)

    ## Next Version Button
    tk.Button(patch_version_frame, text="Next Version", command=lambda: insert_next_version(patch_version_letter.get(), patch_version_entry)).pack(side="left", padx=5)

    ## Add a section to write the patch description
    patch_description_frame = tk.Frame(parent)
    patch_description_frame.pack(side="top", pady=5, fill="both", expand=True)

    patch_description_label = tk.Label(patch_description_frame, text="Patch Description:")
    patch_description_label.pack(side="top", padx=5)

    patch_description_entry = tk.Text(patch_description_frame, height=10, width=40)  # Changed to Text widget
    patch_description_entry.pack(side="top", padx=5, fill="both", expand=True)

    tk.Button(parent, text="Generate Patch", command=lambda: generate_patch([files_listbox.item(item, "values")[0] for item in files_listbox.selection()], patch_version_letter.get(), patch_version_entry.get(), patch_description_entry.get("1.0", tk.END).strip())).pack(side="top", pady=5)

def create_button_frame_patches(parent, patches_listbox):
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    patch_version_letter = ttk.Combobox(patch_version_frame, values=["J", "V", "W"], width=3)
    patch_version_letter.set("J")  # default value
    patch_version_letter.pack(side="left", padx=5)

    # On patch version change, refresh the patches
    patch_version_letter.bind("<<ComboboxSelected>>", lambda event: refresh_patches(patches_listbox, False, patch_version_letter.get(), load_config().get("username")))

    tk.Button(parent, text="Refresh Patches", command=lambda: refresh_patches(patches_listbox, False, patch_version_letter.get(), load_config().get("username"))).pack(side="top", pady=5)

    # Add a button to modify the selected patch
    tk.Button(parent, text="Modify Patch", command=lambda: modify_patch([patches_listbox.item(item, "values") for item in patches_listbox.selection()])).pack(side="top", pady=5)

def create_button_frame_modify_patch(parent, files_listbox, patch_details):
    print(patch_details)
    patch_version_frame = tk.Frame(parent)
    patch_version_frame.pack(side="top", pady=5)

    patch_version_label = tk.Label(patch_version_frame, text="Patch Version:")
    patch_version_label.pack(side="left", padx=5)

    patch_version_letter = ttk.Combobox(patch_version_frame, values=["J", "V", "W"], width=3)
    patch_letter = patch_details[0][0]  # Extract the letter from the selected patch's version
    patch_version_letter.set(patch_letter)  # Set to the selected patch's version
    patch_version_letter.pack(side="left", padx=5)

    patch_version_entry = tk.Entry(patch_version_frame, width=14)
    patch_version_entry.insert(0, patch_details[0])  # Set to the selected patch's version number
    patch_version_entry.pack(side="left", padx=5)

    tk.Button(patch_version_frame, text="Next Version", command=lambda: insert_next_version(patch_version_letter.get(), patch_version_entry)).pack(side="left", padx=5)

    patch_description_frame = tk.Frame(parent)
    patch_description_frame.pack(side="top", pady=5, fill="both", expand=True)

    patch_description_label = tk.Label(patch_description_frame, text="Patch Description:")
    patch_description_label.pack(side="top", padx=5)

    patch_description_entry = tk.Text(patch_description_frame, height=10, width=40)
    patch_description_entry.insert("1.0", patch_details[1])  # Set to the selected patch's description
    patch_description_entry.pack(side="top", padx=5, fill="both", expand=True)

    tk.Button(parent, text="Update Patch", command=lambda: update_patch([files_listbox.item(item, "values")[0] for item in files_listbox.selection()], patch_version_letter.get(), patch_version_entry.get(), patch_description_entry.get("1.0", tk.END).strip())).pack(side="top", pady=5)

def modify_patch(selected_patch):
    if selected_patch:
        patch_details = selected_patch[0]  # Assuming selected_patch is a list of selected items
        switch_to_modify_patch_menu(patch_details)

def update_patch(selected_files, patch_version_letter, patch_version_entry, patch_description):
    # Implement the logic to update the patch with the new details
    pass

def insert_next_version(module, patch_version_entry):
    new_version = next_version(module)
    if new_version:
        patch_version_entry.config(state="normal")
        patch_version_entry.delete(0, tk.END)
        patch_version_entry.insert(0, new_version)
        patch_version_entry.config(state="normal")

def lock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[0] for item in files_listbox.selection()]
    lock_files(selected_files, files_listbox, files_listbox)

def unlock_selected_files(files_listbox):
    selected_files = [files_listbox.item(item, "values")[0] for item in files_listbox.selection()]
    unlock_files(selected_files, files_listbox, files_listbox)

def select_all_files(event, files_listbox):
    for item in files_listbox.get_children():
        files_listbox.selection_add(item)

def setup_gui():
    global root
    root = TkinterDnD.Tk()
    root.title("SVN Manager")
    root.geometry("900x600")
    
    switch_to_lock_unlock_menu()
    
    return root

if __name__ == "__main__":
    root = setup_gui()
    root.mainloop()

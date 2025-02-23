import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from config import load_config, save_config
from shared_operations import load_locked_files
from file_operations import generate_patch
from svn_operations import lock_files, unlock_files, refresh_locked_files as refresh_locked_files_svn
from version_operation import next_version

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

def refresh_username(username_entry):
    config = load_config()
    username_entry.delete(0, tk.END)
    if config.get("username"):
        username_entry.insert(0, config["username"])
    else:
        messagebox.showwarning("Warning", "Please set the username!")

def create_main_layout(root):
    root.grid_rowconfigure(1, weight=1)
    root.grid_columnconfigure(0, weight=1)
    
    top_frame = tk.Frame(root, height=80, relief=tk.RIDGE, borderwidth=2)
    top_frame.grid(row=0, column=0, columnspan=2, sticky="nsew")
    
    bottom_left_frame = tk.Frame(root, relief=tk.RIDGE, borderwidth=2)
    bottom_left_frame.grid(row=1, column=0, sticky="nsew")
    
    bottom_right_frame = tk.Frame(root, width=200, relief=tk.RIDGE, borderwidth=2)
    bottom_right_frame.grid(row=1, column=1, sticky="nsew")
    
    root.grid_columnconfigure(0, weight=3)
    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(1, weight=1)
    
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
    
    return entry

def create_file_listbox(parent):
    
    listbox = ttk.Treeview(parent, columns=("Files Path", "Status"), show="headings")
    listbox.heading("Files Path", text="Files Path")
    listbox.heading("Status", text="Status")
    listbox.column("Status", width=100, stretch=tk.NO)  # Set width of Status column to 25%
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
    patch_version_label = tk.Label(parent, text="Patch Version:")
    patch_version_label.pack(side="top", pady=5)

    patch_version_entry = tk.Entry(parent)
    patch_version_entry.pack(side="top", pady=5)

    ## Next Version Button
    tk.Button(parent, text="Next Version", command=lambda: patch_version_entry.insert(0, next_version("J", patch_version_entry))).pack(side="top", pady=5)

    tk.Button(parent, text="Generate Patch", command=lambda: generate_patch([files_listbox.item(item, "values")[0] for item in files_listbox.selection()], patch_version_entry.get())).pack(side="top", pady=5)

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

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from typing import List, Optional, Callable
from profiles import Profile, create_profile, update_profile, delete_profile, get_profile, list_profiles
from db_handler import dbClass
from svn_operations import is_svn_repo_root, get_relative_path
import profiles
class ProfileDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Profile Manager")
        self.dialog.geometry("600x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Add result variable
        self.result = None
        
        # Initialize database connection
        self.db = dbClass()
        
        # Get existing patch prefixes
        self.existing_patch_prefixes = self.get_existing_patch_prefixes()
        
        self.create_widgets()
        self.refresh_profile_list()
        
        # Center the dialog
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f'{width}x{height}+{x}+{y}')
        
        # Add protocol handler for window close button
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_existing_patch_prefixes(self):
        """Get existing patch prefixes from the database"""
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT PREFIX, APPLICATION_ID FROM MODULE WHERE APPLICATION_ID != 'CORE' AND PREFIX != 'J' ORDER BY PREFIX")
            rows = cursor.fetchall()
            result = [f"{row[0]} - {row[1]}" for row in rows]
            cursor.close()
            return result
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to get patch prefixes: {str(e)}")
            return []

    def create_widgets(self):
        # Left side - Profile list
        left_frame = ttk.Frame(self.dialog)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Profile list with scrollbar
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.profile_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.profile_listbox.yview)
        self.profile_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.profile_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.profile_listbox.bind('<<ListboxSelect>>', self.on_profile_select)
        
        # Buttons under the list
        btn_frame = ttk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="New", command=self.new_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.delete_profile).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Set Active", command=self.select_profile).pack(side=tk.LEFT, padx=2)
        
        # Right side - Profile details
        right_frame = ttk.Frame(self.dialog)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Profile details form
        details_frame = ttk.LabelFrame(right_frame, text="Profile Details")
        details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Name
        ttk.Label(details_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(details_frame, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # SVN Path
        ttk.Label(details_frame, text="SVN Path:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.svn_path_var = tk.StringVar()
        svn_frame = ttk.Frame(details_frame)
        svn_frame.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=2)
        self.svn_path_entry = ttk.Entry(svn_frame, textvariable=self.svn_path_var)
        self.svn_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(svn_frame, text="Browse", command=self.browse_svn_path).pack(side=tk.RIGHT, padx=2)
        
        # Patch prefix
        ttk.Label(details_frame, text="Patch prefix:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        patch_prefix_frame = ttk.Frame(details_frame)
        patch_prefix_frame.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=2)
        
        # Add combobox for existing patch prefixes
        self.patch_prefix_var = tk.StringVar()
        patch_prefix_list = self.existing_patch_prefixes + ["Custom..."]
        self.patch_prefix_combo = ttk.Combobox(patch_prefix_frame, 
                                             textvariable=self.patch_prefix_var,
                                             values=patch_prefix_list,
                                             state="readonly",
                                             width=15)
        self.patch_prefix_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.patch_prefix_combo.bind('<<ComboboxSelected>>', self.on_patch_prefix_select)
        
        # Add entry for custom patch prefix (initially hidden)
        self.custom_patch_var = tk.StringVar()
        self.custom_patch_entry = ttk.Entry(patch_prefix_frame, 
                                         textvariable=self.custom_patch_var,
                                         width=10)
        
        # Current Patches Path
        ttk.Label(details_frame, text="Current Patches:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.current_patches_var = tk.StringVar()
        patches_frame = ttk.Frame(details_frame)
        patches_frame.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=2)
        self.current_patches_entry = ttk.Entry(patches_frame, textvariable=self.current_patches_var)
        self.current_patches_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(patches_frame, text="Browse", command=self.browse_patches_path).pack(side=tk.RIGHT, padx=2)
        
        # DSN Name
        ttk.Label(details_frame, text="DSN Name:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=2)
        self.dsn_name_var = tk.StringVar(value="CYFRAMEPROD")  # Set default value
        self.dsn_name_entry = ttk.Entry(details_frame, textvariable=self.dsn_name_var)
        self.dsn_name_entry.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=2)
        
        details_frame.columnconfigure(1, weight=1)
        
        # Save button
        ttk.Button(right_frame, text="Save", command=self.save_profile).pack(pady=10)

    def browse_svn_path(self):
        path = filedialog.askdirectory(title="Select SVN Repository Path")
        if path:
            self.svn_path_var.set(path)

    def browse_patches_path(self):
        path = filedialog.askdirectory(title="Select Current Patches Path")
        if path:
            self.current_patches_var.set(path)

    def on_patch_prefix_select(self, event):
        if self.patch_prefix_combo.get() == "Custom...":
            self.custom_patch_entry.pack(side=tk.LEFT)
            self.custom_patch_entry.focus()
        else:
            self.custom_patch_entry.pack_forget()
            self.custom_patch_var.set("")

    def validate_patch_prefix(self, prefix: str) -> bool:
        """Validate patch prefix format and existence"""
        # Check format
        prefix = prefix.split(" - ")[0].strip().upper()
        if not prefix.isalpha() or len(prefix) > 4:
            messagebox.showwarning("Invalid Format", 
                                "Patch prefix must contain only letters and be maximum 4 characters long")
            return False
        # If it's an existing prefix, it's valid
        for item in self.existing_patch_prefixes:
            if item.split(" - ")[0] == prefix:
                return True
            
        # For new prefixes, ask for confirmation and get APPLICATION_ID
        if messagebox.askyesno("Confirm New Prefix", 
                             f"The patch prefix '{prefix}' doesn't exist in the database. Would you like to create it?"):
            # Get APPLICATION_ID from user
            application_id = None
            while not application_id:
                application_id = simpledialog.askstring("Application ID", 
                                                     "Enter the unique Application ID for this prefix:",
                                                     initialvalue=prefix)
                if application_id is None:  # User cancelled
                    return False
                application_id = application_id.strip().upper()
                # Validate APPLICATION_ID is unique
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM MODULE WHERE APPLICATION_ID = :1", (application_id,))
                    count = cursor.fetchone()[0]
                    if count > 0:
                        messagebox.showerror("Error", f"Application ID '{application_id}' already exists. Please choose a different one.")
                        application_id = None
                        continue
                    
                    # Insert new prefix with APPLICATION_ID
                    cursor.execute("INSERT INTO MODULE (PREFIX, APPLICATION_ID, REPO) VALUES (:1, :2, :3)", 
                                (prefix, application_id, "SVN"))
                    
                    # Update the existing prefixes list and combobox
                    self.existing_patch_prefixes.append(prefix + " - " + application_id)
                    self.existing_patch_prefixes.sort()
                    self.patch_prefix_combo['values'] = self.existing_patch_prefixes + ["Custom..."]
                    
                    return True
                except Exception as e:
                    messagebox.showerror("Database Error", f"Failed to create new patch prefix: {str(e)}")
                    if cursor:
                        cursor.close()
                    return False
        return False
    
    def create_folder(self, patch_prefix: str, svn_path: str):
        """Create the necessary folder structure for the patch prefix"""
        if not svn_path:
            messagebox.showerror("Error", "SVN Path is not set")
            return
            
        # Normalize SVN path
        svn_path = svn_path.replace("\\", "/").rstrip("/")
        
        # Check if we're at the root of the SVN repo
        is_root = is_svn_repo_root(svn_path)
        
        if is_root and patch_prefix != 'S':
            messagebox.showerror("Error", "Only prefix 'S' is allowed at the root of the SVN repository.")
            return
            
        if not is_root and patch_prefix == 'S':
            messagebox.showerror("Error", "Prefix 'S' can only be used at the root of the SVN repository.")
            return
        cursor = None
        try:
            cursor = self.db.conn.cursor()

            # Build path mappings (folder_type: (path_suffix, description_prefix))
            folder_map = {
                1: ("webpage", "Web for "),
                2: ("Database", "Database for "),
                4: ("CGI", "CGI for "),
                3: ("DLL", "DLL for "),
            }

            base_relative = get_relative_path(svn_path)
            base_fake_path = "$/Projects/SVN/" + base_relative

            # Get current max FOLDER_ID once
            cursor.execute("SELECT NVL(MAX(FOLDER_ID), 0) FROM FOLDER")
            next_folder_id = cursor.fetchone()[0] + 1

            for folder_type, (suffix, desc_prefix) in folder_map.items():
                fake_path = f"{base_fake_path}/{suffix}"
                relative_path = f"{base_relative}/{suffix}"
                
                # Check if path already exists
                cursor.execute("SELECT COUNT(*) FROM FOLDER WHERE PATH = :1", (fake_path,))
                exists = cursor.fetchone()[0]
                
                if not exists:
                    cursor.execute("""
                        INSERT INTO FOLDER 
                        (PATH, DESCRIPTION, FOLDER_TYPE, SOFT_PATH, DEFAULT_PREFIX, REPO_TYPE, SVN_PATH, FOLDER_ID)
                        VALUES (:1, :2, :3, :4, :5, :6, :7, :8)
                    """, (
                        fake_path,
                        desc_prefix + patch_prefix,
                        folder_type,
                        relative_path,
                        patch_prefix,
                        "SVN",
                        relative_path,
                        next_folder_id
                    ))
                    next_folder_id += 1  # Increment only when inserting

            self.db.conn.commit()
            cursor.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create folder structure: {str(e)}")
            if cursor:
                cursor.close()
                self.db.conn.rollback()
                messagebox.showerror("Error", f"Failed to create folder structure: {str(e)}")
                if cursor:
                    cursor.close()
        return


    def get_current_patch_prefix(self) -> str:
        """Get the current patch prefix from either combobox or custom entry"""
        if self.patch_prefix_combo.get() == "Custom...":
            return self.custom_patch_var.get().strip().upper()
        return self.patch_prefix_combo.get()

    def set_patch_prefix(self, prefix: str):
        """Set the patch prefix in the UI"""
        # Try to match prefix with existing_patch_prefixes (which are like 'D - DYNA')
        matched = None
        for item in self.existing_patch_prefixes:
            if item.split(" - ")[0] == prefix:
                matched = item
                break
        if matched:
            self.patch_prefix_combo.set(matched)
            self.custom_patch_entry.pack_forget()
            self.custom_patch_var.set("")
        else:
            self.patch_prefix_combo.set("Custom...")
            self.custom_patch_entry.pack(side=tk.LEFT)
            self.custom_patch_var.set(prefix)

    def refresh_profile_list(self):
        self.profile_listbox.delete(0, tk.END)
        for profile_name in list_profiles():
            self.profile_listbox.insert(tk.END, profile_name)

    def on_profile_select(self, event):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
            
        profile_name = self.profile_listbox.get(selection[0])
        profile = get_profile(profile_name)
        if profile:
            self.name_var.set(profile.name)
            self.svn_path_var.set(profile.svn_path)
            self.set_patch_prefix(profile.patch_prefix[0])
            self.current_patches_var.set(profile.current_patches)
            self.dsn_name_var.set(profile.dsn_name)
            
            # Disable name field for existing profiles
            self.name_entry.configure(state="disabled")
        else:
            self.clear_form()

    def clear_form(self):
        self.name_var.set("")
        self.svn_path_var.set("")
        self.patch_prefix_combo.set("")
        self.custom_patch_var.set("")
        self.custom_patch_entry.pack_forget()
        self.current_patches_var.set("")
        self.dsn_name_var.set("CYFRAMEPROD")
        self.name_entry.configure(state="normal")

    def new_profile(self):
        self.clear_form()
        self.profile_listbox.selection_clear(0, tk.END)
        self.dsn_name_var.set("CYFRAMEPROD")

    def delete_profile(self):
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to delete")
            return
            
        profile_name = self.profile_listbox.get(selection[0])
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile '{profile_name}'?"):
            try:
                delete_profile(profile_name)
                self.refresh_profile_list()
                self.clear_form()
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def select_profile(self):
        """Select the current profile as active"""
        selection = self.profile_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a profile to activate")
            return
            
        profile_name = self.profile_listbox.get(selection[0])
        self.result = profile_name
        self.dialog.destroy()

    def on_close(self):
        """Handle dialog close event"""
        self.dialog.destroy()

    def save_profile(self):
        name = self.name_var.get().strip()
        svn_path = self.svn_path_var.get().strip()
        patch_prefix = self.get_current_patch_prefix()
        current_patches = self.current_patches_var.get().strip()
        dsn_name = self.dsn_name_var.get().strip()

        patch_prefix = patch_prefix.split(" - ")[0].strip().upper()
         
        if not all([name, svn_path, patch_prefix, current_patches, dsn_name]):
            messagebox.showwarning("Warning", "All fields are required")
            return
            
        # Normalize and check if we're at the root of the SVN repo (no "Projects" in path, and no subfolders)
        is_root = "Projects" not in svn_path and svn_path.rstrip("/\\").endswith(("jtdev", "jtdev/"))  # adjust if needed

        # S prefix must be used only at the root
        if not is_root and patch_prefix == 'S':
            messagebox.showerror("Error", "Prefix 'S' is only allowed at the root of the SVN repository.")
            return

        # Other prefixes (not 'S') must be used only inside Projects
        if is_root and patch_prefix != 'S':
            messagebox.showerror("Error", "Only prefix 'S' is allowed at the root of the SVN repository.")
            return
        
        if patch_prefix != 'S':
            # Ensure svn_path ends with 'Projects/Clients/{Client_name}' (no trailing slash, no subfolders)
            parts = svn_path.replace("\\", "/").split("/")
            if len(parts) < 3 or parts[-3] != "Projects" or parts[-2] != "Clients" or not parts[-1]:
                messagebox.showerror(
                    "Error",
                    f"SVN_Path must be inside '{{SVN_Root_Folder}}/Projects/Clients/{{Client_name}}' (no subfolders) !\n for patch prefix '{patch_prefix}'."
                )
                return
            
        if not self.validate_patch_prefix(patch_prefix):
            return
        self.create_folder(patch_prefix, svn_path)

        try:
            current_state = str(self.name_entry.cget("state"))
            is_new_profile = current_state != "disabled"
            
            if is_new_profile:
                # Check if profile exists
                if get_profile(name):
                    messagebox.showerror("Error", f"Profile '{name}' already exists")
                    return
                create_profile(name, svn_path, [patch_prefix], current_patches, dsn_name)
            else:  # Update existing profile
                if messagebox.askyesno("Confirm Modification", 
                                     f"Are you sure you want to modify the profile '{name}'?"):
                    update_profile(name, 
                                 svn_path=svn_path, 
                                 patch_prefix=[patch_prefix], 
                                 current_patches=current_patches, 
                                 dsn_name=dsn_name)
                else:
                    return
            
            self.refresh_profile_list()
            messagebox.showinfo("Success", "Profile saved successfully")
            
            # Ask if user wants to make this the active profile
            if messagebox.askyesno("Set Active Profile", 
                                 f"Do you want to make '{name}' the active profile?"):
                self.result = name
                self.dialog.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e))

def show_profile_dialog(parent) -> Optional[str]:
    """Show the profile management dialog and return the selected profile name"""
    dialog = ProfileDialog(parent)
    parent.wait_window(dialog.dialog)  # Wait for dialog to close
    return dialog.result 
import tkinter as tk
from tkinter import messagebox
from svn_operations import (
    lock_files, unlock_files, refresh_file_status_version,
    view_file_native_diff, get_all_locked_files, get_file_info, refresh_locked_files
)
from patches_operations import (
    refresh_patches, remove_patch, view_files_from_patch,
    build_patch, get_full_patch_info
)
from config import load_config
from buttons_function import next_version, view_selected_file_native_diff

class ContextMenuManager:
    """Manages context menus for different UI sections."""
    
    def __init__(self):
        self.menus = {}
        self.switch_callback = None

    def create_files_menu(self, listbox, menu_name: str = "patch_files"):
        """Create context menu for files treeview."""
        menu = tk.Menu(listbox, tearoff=0)
        
        def on_popup(event):
            has_selection = bool(listbox.selection())
            
            # Clear existing menu items
            menu.delete(0, tk.END)
            
            if has_selection:
                if menu_name == "lock_unlock":
                    menu.add_command(label="Refresh Files", 
                                command=lambda: refresh_file_status_version(listbox))
                    menu.add_command(label="Refresh Locked files", 
                                command=lambda: refresh_locked_files(listbox))
                    menu.add_separator()
                    menu.add_command(label="View Diff", 
                                   command=lambda: view_selected_file_native_diff(listbox))
                    menu.add_command(label="Remove selected files", 
                                command=lambda: self._remove_from_patch(listbox))
                    menu.add_separator()
                    menu.add_command(label="Lock selected files", 
                                   command=lambda: lock_files([listbox.item(item, "values")[2] for item in listbox.selection()], listbox))
                    menu.add_command(label="Lock all Files", 
                                   command=lambda: lock_files([listbox.item(item, "values")[2] for item in listbox.get_children()], listbox))
                    menu.add_separator()
                    menu.add_command(label="Unlock selected files", 
                                   command=lambda: unlock_files([listbox.item(item, "values")[2] for item in listbox.selection()], listbox))
                    menu.add_command(label="Unlock all Files", 
                                   command=lambda: unlock_files([listbox.item(item, "values")[2] for item in listbox.get_children()], listbox))
                if menu_name == "patch_files":
                    menu.add_command(label="Refresh Files", 
                            command=lambda: refresh_file_status_version(listbox))
                    menu.add_separator()
                    menu.add_command(label="Remove selected files", 
                                command=lambda: self._remove_from_patch(listbox))
                    menu.add_separator()
                    menu.add_command(label="View Diff", 
                                   command=lambda: view_selected_file_native_diff(listbox))
                if menu_name == "locked_files":
                    menu.add_command(label="Refresh Files", 
                            command=lambda: refresh_file_status_version(listbox))
                    menu.add_command(label="Refresh Locked files", 
                                command=lambda: refresh_locked_files(listbox))
                    menu.add_separator()
                    menu.add_command(label="Add to Patch",
                                   command=lambda: self._add_to_main_treeview(listbox))
                    menu.add_separator()
                    menu.add_command(label="View Diff", 
                                   command=lambda: view_selected_file_native_diff(listbox))
            else:
                if menu_name == "lock_unlock":
                    
                    menu.add_command(label="Refresh Files", 
                                command=lambda: refresh_file_status_version(listbox))
                    menu.add_command(label="Refresh Locked files", 
                                command=lambda: refresh_locked_files(listbox))
                    menu.add_separator()
                    menu.add_command(label="Lock all Files", 
                                   command=lambda: lock_files([listbox.item(item, "values")[2] for item in listbox.get_children()], listbox))
                    menu.add_separator()
                    menu.add_command(label="Unlock all Files", 
                                   command=lambda: unlock_files([listbox.item(item, "values")[2] for item in listbox.get_children()], listbox))
                if menu_name == "patch_files":
                    menu.add_command(label="Refresh Files", 
                            command=lambda: refresh_file_status_version(listbox))
                if menu_name == "locked_files":
                    menu.add_command(label="Refresh Files", 
                            command=lambda: refresh_file_status_version(listbox))
                    menu.add_command(label="Refresh Locked files", 
                                command=lambda: refresh_locked_files(listbox))
            
            menu.post(event.x_root, event.y_root)
            
        listbox.bind("<Button-3>", on_popup)
        return menu

    def create_patches_menu(self, treeview, switch_callback=None):
        """Create context menu for patches treeview."""
        self.switch_callback = switch_callback
        menu = tk.Menu(treeview, tearoff=0)
        
        def on_popup(event):
            has_selection = bool(treeview.selection())
            menu.delete(0, tk.END)
            
            if has_selection:
                menu.add_command(label="Modify Patch", 
                               command=lambda: self._modify_patch(treeview))
                menu.add_command(label="Build Patch",
                               command=lambda: self._build_patch(treeview))
                menu.add_command(label="View Patch Details",
                               command=lambda: self._view_patch_files(treeview))
                menu.add_command(label="Edit Description",
                               command=lambda: self._edit_patch_description(treeview))
                menu.add_separator()
                menu.add_command(label="Remove Patch",
                               command=lambda: self._remove_patch(treeview))
                menu.add_separator()
                menu.add_command(label="Refresh Patches",
                            command=lambda: self._refresh_patches(treeview))
            else:
                menu.add_command(label="Refresh Patches",
                            command=lambda: self._refresh_patches(treeview))
            
            menu.post(event.x_root, event.y_root)
            
        treeview.bind("<Button-3>", on_popup)
        return menu

    def _remove_from_patch(self, listbox):
        """Remove selected files and optionally return to locked files view."""
        locked_files_treeview = self._find_locked_files_treeview(listbox)
        selected_items = listbox.selection()
        if not selected_items:
            return
            
        # If no locked files treeview found, just remove the files
        if not locked_files_treeview:
            for item in selected_items:
                listbox.delete(item)
            return
        
        # Get config for username check
        config = load_config()
        username = config.get("username", "")
        
        # Get existing files in locked_files_treeview
        existing_files = set()
        for item in locked_files_treeview.get_children():
            file_path = locked_files_treeview.item(item, "values")[2]
            existing_files.add(file_path)
        
        # Process each selected file
        for item in selected_items:
            values = listbox.item(item, "values")
            file_path = values[2]
            
            is_locked_by_user, _, _, _ = get_file_info(file_path)
            
            if is_locked_by_user and file_path not in existing_files:
                locked_files_treeview.insert("", "end", values=values)
            
            listbox.delete(item)

    def _add_to_main_treeview(self, locked_files_treeview):
        """Add selected files to the main treeview."""
        main_treeview = self._find_main_treeview(locked_files_treeview)
        if not main_treeview:
            return
            
        selected_items = locked_files_treeview.selection()
        if not selected_items:
            return
        
        # Get existing files to avoid duplicates
        existing_files = set()
        for item in main_treeview.get_children():
            file_path = main_treeview.item(item, "values")[2]
            existing_files.add(file_path)
        
        # Add selected files if not already present
        for item in selected_items:
            values = locked_files_treeview.item(item, "values")
            file_path = values[2]
            
            if file_path not in existing_files:
                main_treeview.insert("", "end", values=values)
                existing_files.add(file_path)
        
        # Remove from locked files view
        for item in selected_items:
            locked_files_treeview.delete(item)

    def _modify_patch(self, treeview):
        """Handle patch modification."""
        if not self.switch_callback:  # Check for callback
            print("Warning: No switch_callback set for modify_patch")
            return
            
        selected = treeview.selection()
        if selected:
            item_values = treeview.item(selected[0], "values")
            # Get full patch info before calling the switch callback
            patch_name = item_values[0]
            full_patch_info = get_full_patch_info(patch_name)
            if full_patch_info:
                self.switch_callback(full_patch_info)
            else:
                messagebox.showerror("Error", f"Could not find details for patch {patch_name}")

    def _build_patch(self, treeview):
        """Build selected patch."""
        selected = treeview.selection()
        if selected:
            patch_values = treeview.item(selected[0], "values")
            # Get full patch info using the patch name (first value)
            full_patch_info = get_full_patch_info(patch_values[0])
            if full_patch_info:
                build_patch(full_patch_info)
            else:
                messagebox.showerror("Error", f"Could not find details for patch {patch_values[0]}")

    def _view_patch_files(self, treeview):
        """View files in selected patch."""
        selected = treeview.selection()
        if selected:
            patch_values = treeview.item(selected[0], "values")
            # Get full patch info using the patch name (first value)
            full_patch_info = get_full_patch_info(patch_values[0])
            if full_patch_info:
                view_files_from_patch(full_patch_info)
            else:
                messagebox.showerror("Error", f"Could not find details for patch {patch_values[0]}")

    def _remove_patch(self, treeview):
        """Remove selected patch."""
        selected = treeview.selection()
        if selected:
            item_id = selected[0]
            patch_values = treeview.item(item_id, "values")
            # Get full patch info using the patch name (first value)
            full_patch_info = get_full_patch_info(patch_values[0])
            if full_patch_info and remove_patch(full_patch_info):
                treeview.delete(item_id)
            else:
                messagebox.showerror("Error", f"Could not find details for patch {patch_values[0]}")

    def _refresh_patches(self, treeview):
        """Refresh patches list."""
        # Get current prefix from combobox in parent window
        prefix_combo = self._find_prefix_combobox(treeview)
        if prefix_combo:
            prefix = prefix_combo.get()
            from config import load_config
            config = load_config()
            refresh_patches(treeview, False, prefix, config.get("username"))

    def refresh_available_locked_files(self, locked_files_treeview, main_treeview):
        """Refresh the list of locked files."""
        try:
            # Clear the locked files treeview
            locked_files_treeview.delete(*locked_files_treeview.get_children())
            
            # Get all locked files
            locked_files = get_all_locked_files()
            
            # Get existing files in main treeview
            existing_files = set()
            for item in main_treeview.get_children():
                file_path = main_treeview.item(item, "values")[2]
                existing_files.add(file_path)
            
            # Add locked files not in main treeview
            for file_path, revision, lock_date in locked_files:
                if file_path not in existing_files:
                    locked_files_treeview.insert(
                        "", "end",
                        values=("locked", revision, file_path, lock_date)
                    )
                    
            locked_files_treeview.update()
            
        except Exception as e:
            print(f"Error refreshing locked files: {e}")
            messagebox.showerror("Error", f"Failed to refresh locked files:\n{e}")

    def _find_main_treeview(self, widget):
        """Find the main files treeview in the window hierarchy."""
        from create_component import find_main_treeview
        return find_main_treeview(widget)

    def _find_locked_files_treeview(self, widget):
        """Find the locked files treeview in the window hierarchy."""
        from create_component import find_locked_files_treeview
        return find_locked_files_treeview(widget)

    def _find_prefix_combobox(self, widget):
        """Find the prefix combobox in the window hierarchy."""
        root = widget.winfo_toplevel()
        for child in root.winfo_children():
            if hasattr(child, "prefix_combobox"):
                return child.prefix_combobox
        return None

    def _edit_patch_description(self, treeview):
        """Edit the description of the selected patch."""
        selected = treeview.selection()
        if selected:
            item_values = treeview.item(selected[0], "values")
            patch_name = item_values[0]
            
            # Create dialog window
            dialog = tk.Toplevel()
            dialog.title(f"Edit Description - {patch_name}")
            dialog.geometry("400x300")
            dialog.transient(treeview.winfo_toplevel())
            dialog.grab_set()
            
            # Get current description
            patch_info = get_full_patch_info(patch_name)
            current_description = patch_info['COMMENTS'] if patch_info else ""
            patch_id = patch_info["PATCH_ID"] if patch_info else None
            
            # Create text widget
            text_widget = tk.Text(dialog, wrap=tk.WORD, width=40, height=10)
            text_widget.insert("1.0", current_description or "")
            text_widget.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
            
            def save_description():
                new_description = text_widget.get("1.0", tk.END).strip()
                from db_handler import dbClass
                db = dbClass()
                try:
                    db.conn.begin()
                    db.update_comment(int(patch_id), new_description)
                    db.conn.commit()
                    dialog.destroy()
                    # Refresh the patches list
                    self._refresh_patches(treeview)
                except Exception as e:
                    db.conn.rollback()
                    messagebox.showerror("Error", f"Failed to save description:\n{e}")
            
            # Buttons frame
            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=5)
            
            tk.Button(btn_frame, text="Save", command=save_description).pack(side=tk.LEFT, padx=5)
            tk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

# Global instance
context_menu_manager = ContextMenuManager()

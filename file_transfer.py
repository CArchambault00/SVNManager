from typing import Optional
import tkinter as tk
from tkinter import ttk
from config import load_config
from svn_operations import get_file_info

def add_selected_to_main_treeview(source_treeview: ttk.Treeview, main_treeview: ttk.Treeview) -> None:
    """Add selected files from source treeview to main treeview."""
    selected_items = source_treeview.selection()
    if not selected_items:
        return
    
    # Create a set of existing files for O(1) lookup
    existing_files = set()
    for item in main_treeview.get_children():
        file_path = main_treeview.item(item, "values")[2]
        existing_files.add(file_path)
    
    # Add selected files if not already in main treeview
    files_added = 0
    for item in selected_items:
        values = source_treeview.item(item, "values")
        file_path = values[2]
        
        if file_path not in existing_files:
            main_treeview.insert("", "end", values=values)
            files_added += 1
            existing_files.add(file_path)
    
    # Remove the added files from the source treeview
    for item in selected_items:
        source_treeview.delete(item)

def remove_and_return_selected_files(listbox: ttk.Treeview, locked_files_treeview: Optional[ttk.Treeview] = None) -> None:
    """Remove selected files from listbox and optionally return them to locked files view."""
    selected_items = listbox.selection()
    if not selected_items:
        return
        
    # If no locked files treeview provided, just remove items
    if not locked_files_treeview:
        for item in selected_items:
            listbox.delete(item)
        return
    
    username = load_config().get("username", "")
    
    # Get existing files in locked_files_treeview to avoid duplicates
    existing_locked_files = set()
    for item in locked_files_treeview.get_children():
        file_path = locked_files_treeview.item(item, "values")[2]
        existing_locked_files.add(file_path)
    
    for item in selected_items:
        values = listbox.item(item, "values")
        file_path = values[2]
        
        # Check if file is locked by the current user
        is_locked_by_user, lock_owner, revision, lock_date = get_file_info(file_path)
        
        # Add to locked files treeview if it's locked by current user and not already there
        if is_locked_by_user and file_path not in existing_locked_files:
            locked_files_treeview.insert("", "end", values=values)
        
        # Remove from main files treeview
        listbox.delete(item)

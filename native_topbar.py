import tkinter as tk
from tkinter import messagebox
from config import load_config, get_unset_var, save_config
from dialog import set_username
from profile_dialog import show_profile_dialog
from profiles import get_profile, list_profiles

class MenuManager:
    def __init__(self, menu_bar):
        self.menu_bar = menu_bar
        self.profile_menu = None
        self.config_menu = None
        
    def set_menus(self, profile_menu, config_menu):
        self.profile_menu = profile_menu
        self.config_menu = config_menu
        
    def update_labels(self, config_menu, unset_var):
        """Update menu labels safely"""
        # Update Config submenu
        config_menu.entryconfig(0, label="Username ❌" if "username" in unset_var else "Username ✔️")
        
        # Get current config
        config = load_config()
        active_profile = config.get("active_profile")
        username = config.get("username")
        
        # Find and update menu items
        for i in range(self.menu_bar.index('end') + 1):
            try:
                if self.menu_bar.entrycget(i, 'label').startswith('Profile'):
                    # Profile status depends on having an active profile
                    self.menu_bar.entryconfig(i, label=f"Profile {'✔️' if active_profile else '❌'}")
                elif 'Config' in self.menu_bar.entrycget(i, 'label'):
                    # Config status depends only on username
                    self.menu_bar.entryconfig(i, label=f"Config {'✔️' if username else '❌'}")
            except tk.TclError:
                continue
        
        # Also update the active profile display
        self.update_active_profile_display(active_profile)
    
    def update_active_profile_display(self, active_profile):
        """Update the active profile display in the menu bar"""
        # Find the active profile display menu item
        for i in range(self.menu_bar.index('end') + 1):
            try:
                label = self.menu_bar.entrycget(i, 'label')
                if label.startswith('Active Profile:') or label == 'No Active Profile':
                    # Update the active profile display
                    if active_profile:
                        self.menu_bar.entryconfig(i, label=f"Active Profile: {active_profile}")
                    else:
                        self.menu_bar.entryconfig(i, label="No Active Profile")
                    break
            except tk.TclError:
                continue

def update_profile_menu(profile_menu, active_profile, menu_bar):
    """Update the profile menu to show active profile"""
    # Clear existing items after "Manage Profiles..."
    last_index = profile_menu.index(tk.END)
    if last_index is not None and last_index > 0:
        profile_menu.delete(1, last_index)
    
    if active_profile:
        profile_menu.add_separator()
        profile_menu.add_command(label=f"Active: {active_profile}", state="disabled")
        

def select_profile(config_menu, menu_bar, profile_menu, menu_manager):
    """Handle profile selection"""
    profile_name = show_profile_dialog(menu_bar.master)
    if profile_name:
        config = load_config()
        old_profile = config.get("active_profile")
        config["active_profile"] = profile_name
        save_config(config)
        
        # Update menu labels based on new profile
        unset_var = get_unset_var()
        menu_manager.update_labels(config_menu, unset_var)
        
        # Update profile menu
        update_profile_menu(profile_menu, profile_name, menu_bar)
        
        # Update active profile display
        menu_manager.update_active_profile_display(profile_name)
        
        # Reset all menus if profile actually changed
        if old_profile != profile_name:
            reset_all_menus(menu_bar.master)

def initialize_native_topbar(root, app_version):
    # Create the menu bar
    menu_bar = tk.Menu(root)
    menu_manager = MenuManager(menu_bar)
    
    config_menu = tk.Menu(menu_bar, tearoff=0)
    profile_menu = tk.Menu(menu_bar, tearoff=0)

    config = load_config()
    unset_var = get_unset_var()
    active_profile = config.get("active_profile")

    # Add Profile menu
    menu_bar.add_cascade(label=f"Profile {'✔️' if active_profile else '❌'}", menu=profile_menu)
    profile_menu.add_command(
        label="Manage Profiles...", 
        command=lambda: select_profile(config_menu, menu_bar, profile_menu, menu_manager)
    )
    
    # Show active profile if exists
    update_profile_menu(profile_menu, active_profile, menu_bar)

    # Add Config menu
    menu_bar.add_cascade(
        label=f"Config {'✔️' if config.get("username") else '❌'}",
        menu=config_menu
    )

    # Store menus for later updates
    menu_manager.set_menus(profile_menu, config_menu)

    # Only show username in config menu
    config_menu.add_command(
        label="Username ❌" if "username" in unset_var else "Username ✔️",
        command=lambda: set_username(config_menu, menu_bar)
    )

    help_menu = tk.Menu(menu_bar, tearoff=0)
    help_menu.add_command(
        label="About",
        command=lambda: messagebox.showinfo("About", f"SVN Manager v{app_version}\n\n")
    )
    
    help_menu.add_command(
        label="How to use",
        command=lambda: messagebox.showinfo("How to use", 
            "To use this application, you must:\n\n"
            "1. Set your username in the Config menu\n"
            "2. Create a profile in the Profile menu\n"
            "3. Select a profile to work with\n\n"
            "The application will remember your selected profile even after closing.")
    )

    help_menu.add_command(
        label="Patch version",
        command=lambda: messagebox.showinfo("Patch version", 
            "Patch must follow the format 'Major.Minor.Patch-*'\n" \
            "Following those patterns (Can be combined):\n" \
            "Web changes :\n" \
            "*-W0 -> web page, change function, logic(not visible for user)\n" \
            "*-W1 -> add/change elements on the web page..\n" \
            "*-W2 -> add/change business logic.. *Breaking change*\n\n" \
            "Server/Database changes :\n" \
            "*-S0 -> min. logical Change; New Label; System Parameter; New type report.\n" \
            "*-S1 -> new function, new param\n" \
            "*-S2 -> add Param; delete Param; alter table; change column size;\n" \
            "")
    )

    help_menu.add_command(
        label="Profile",
        command=lambda: messagebox.showinfo("Profile", 
            "Profiles are used to manage different projects\n\n"
            "To create a new profile:\n"
            "1. Click on Profile at the top left of SVNManager and select 'Manage Profiles...'\n"
            "2. You should see your existing profiles listed and buttons to add or remove profiles.\n"
            "3. Configure the profile settings as needed.\n"
            "4. PATCH PREFIX other than S are meant for specific projects like ANT, DYNA etc...\n"
            "5. The SVN Path must match the PROJECTS and the PREFIX. \n'S' is for the root of SVN Repo and other PREFIX are meant for {{SVN_Repo_root}}/Projects/Clients/{{Client_Name}}\n'A - ANT' is for AntPackaging which must have the SVN_PATH set to {{SVN_Repo_root}}/Projects/Clients/AntPackaging\n\n"
            "To switch between profiles:\n"
            "1. Click on Profile at the top left of SVNManager and select 'Manage Profiles...'\n"
            "2. Choose the profile you want to switch to and click 'Set Active'.\n"
            "3. The application will reload with the selected profile's settings.")
    )

    menu_bar.add_cascade(label="Help", menu=help_menu)
    
    # Add Reset button before Exit
    menu_bar.add_command(
        label="Reset current menu",
        command=lambda: reset_current_menu(root)
    )
    
    menu_bar.add_cascade(label="Exit", command=root.quit)
    
    # Add active profile display after Exit
    if active_profile:
        menu_bar.add_separator()
        menu_bar.add_command(label=f"Active Profile: {active_profile}", state="disabled")
    else:
        menu_bar.add_command(label="No Active Profile", state="disabled")

    root.config(menu=menu_bar)
    
    # Check if username and profile are set
    if not config.get("username"):
        messagebox.showwarning("Setup Required", "Please set your username in the Config menu.")
    elif not config.get("active_profile"):
        messagebox.showwarning("Setup Required", "Please select or create a profile in the Profile menu.")

def reset_current_menu(root):
    """Reset the current menu state"""
    from state_manager import state_manager
    from app import (switch_to_lock_unlock_menu, switch_to_patch_menu,
                    switch_to_patches_menu, switch_to_modify_patch_menu)
    
    if state_manager.is_menu_loading():
        # Schedule reset attempt after a short delay if menu is loading
        root.after(100, lambda: reset_current_menu(root))
        return
        
    current_menu = state_manager.current_menu
    if current_menu == "patch":
        # Clear patch state and rebuild menu
        state_manager.clear_state("patch")
        # Keep current menu to avoid recursion
        state_manager.current_menu = "patch"
        # Recreate menu with fresh state
        switch_to_patch_menu(root)
    elif current_menu == "patches":
        # Just refresh the patches list
        switch_to_patches_menu(root)
    elif current_menu == "modify_patch":
        # Get original patch details to restore initial state
        patch_state = state_manager.get_state("modify_patch")
        original_details = patch_state.get("original_patch_details")
        if original_details:
            state_manager.clear_state("modify_patch")
            # Keep menu state and original details
            state_manager.current_menu = "modify_patch"
            modify_patch_state = state_manager.get_state("modify_patch")
            modify_patch_state["patch_details"] = original_details
            modify_patch_state["original_patch_details"] = original_details
            # Rebuild menu with original state
            switch_to_modify_patch_menu(original_details, root)
    else:
        # Default to lock/unlock menu if no current menu or unknown menu
        switch_to_lock_unlock_menu(root)


def reset_all_menus(root):
    """Reset all menu states and return to the default menu when profile changes"""
    from state_manager import state_manager
    from app import switch_to_lock_unlock_menu
    
    if state_manager.is_menu_loading():
        # Schedule reset attempt after a short delay if menu is loading
        root.after(100, lambda: reset_all_menus(root))
        return
    
    # Set a flag to prevent state saving during reset
    old_current_menu = state_manager.current_menu
    state_manager.current_menu = None  # Prevent save_current_state from working
    
    # Clear all menu states
    state_manager.clear_state()  # This clears all menu states
    
    # Stop any active refresh timers
    state_manager.stop_refresh_timer(root)
    
    # Reset to the default menu (lock/unlock)
    switch_to_lock_unlock_menu(root)
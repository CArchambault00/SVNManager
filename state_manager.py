class StateManager:
    """
    Manages state persistence between menu switches in the application.
    Stores states for different menus like selected files, input values, etc.
    """
    def __init__(self):
        # Initialize states for different menus
        self.states = {
            "lock_unlock": {
                "selected_files": [],
                "listbox_items": []  # Store all items in the listbox
            },
            "patch": {
                "selected_files": [],
                "listbox_items": [],
                "patch_version": "",
                "patch_description": "",
                "unlock_files": False
            },
            "patches": {
                "selected_patch": None,
                "selected_prefix": "S"
            },
            "modify_patch": {
                "selected_files": [],
                "listbox_items": [],
                "patch_version": "",
                "patch_description": "",
                "unlock_files": False,
                "patch_details": None
            }
        }
        
        # Track the current menu
        self.current_menu = None

        # Track menu loading state
        self.is_loading = False

        # Track refresh timer
        self.refresh_timer = None
        self.refresh_timer_interval = 5000  # 5 seconds
    
    def save_state(self, menu_name, **kwargs):
        """
        Save the current state for a specific menu
        """
        if menu_name in self.states:
            for key, value in kwargs.items():
                if key in self.states[menu_name]:
                    self.states[menu_name][key] = value
            self.current_menu = menu_name
    
    def get_state(self, menu_name):
        """
        Get the saved state for a specific menu
        """
        return self.states.get(menu_name, {})
    
    def get_current_menu(self) -> str:
        """Get the name of the current active menu."""
        return self.current_menu

    def clear_state(self, menu_name=None):
        """
        Clear the state for a specific menu or all menus if menu_name is None.
        Preserves original_patch_details for modify_patch menu.
        """
        if menu_name:
            if menu_name in self.states:
                # Preserve both current and original patch details when needed
                patch_details = None
                original_details = None
                if menu_name == "modify_patch":
                    patch_details = self.states[menu_name].get("patch_details")
                    original_details = self.states[menu_name].get("original_patch_details")
                
                # Reset all state fields to their default empty values
                self.states[menu_name] = {
                    "selected_files": [],
                    "listbox_items": [],
                    "patch_version": "",
                    "patch_description": "",
                    "unlock_files": False
                }
                
                # Special handling for different menus
                if menu_name == "patches":
                    self.states[menu_name]["selected_patch"] = None
                    self.states[menu_name]["selected_prefix"] = "S"
                elif menu_name == "modify_patch":
                    if patch_details:
                        self.states[menu_name]["patch_details"] = patch_details
                    if original_details:
                        self.states[menu_name]["original_patch_details"] = original_details
        else:
            for menu in self.states:
                self.clear_state(menu)

    def set_loading(self, loading: bool) -> None:
        """Set the loading state."""
        self.is_loading = loading
    
    def is_menu_loading(self) -> bool:
        """Check if a menu is currently loading."""
        return self.is_loading

    def start_refresh_timer(self, root_widget, files_listbox) -> None:
        """Start periodic refresh timer for files listbox"""
        from svn_operations import refresh_file_status_version
        
        def refresh():
            if self.current_menu in ["patch", "modify_patch"]:
                refresh_file_status_version(files_listbox)
                self.refresh_timer = root_widget.after(self.refresh_timer_interval, refresh)
        
        # Cancel any existing timer
        self.stop_refresh_timer(root_widget)
        # Start new timer
        self.refresh_timer = root_widget.after(self.refresh_timer_interval, refresh)
        
    def stop_refresh_timer(self, root_widget) -> None:
        """Stop the periodic refresh timer"""
        if self.refresh_timer:
            root_widget.after_cancel(self.refresh_timer)
            self.refresh_timer = None

# Create a global instance
state_manager = StateManager()

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
                "selected_prefix": "",  # Default prefix
                "prefix_history": []  # Track prefix history
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
        Preserves patch_details and original_patch_details for modify_patch menu.
        """
        if menu_name:
            if menu_name in self.states:
                # Preserve patch details for modify_patch menu
                patch_details = None
                original_details = None
                if menu_name == "modify_patch":
                    patch_details = self.states[menu_name].get("patch_details")
                    original_details = self.states[menu_name].get("original_patch_details")
                
                # Reset state fields based on menu type
                if menu_name == "lock_unlock":
                    self.states[menu_name] = {
                        "selected_files": [],
                        "listbox_items": []
                    }
                elif menu_name == "patches":
                    self.states[menu_name] = {
                        "selected_patch": None,
                        "selected_prefix": "S",
                        "prefix_history": []
                    }
                else:
                    # For patch and modify_patch menus
                    self.states[menu_name] = {
                        "selected_files": [],
                        "listbox_items": [],
                        "patch_version": "",
                        "patch_description": "",
                        "unlock_files": False
                    }
                    
                    # Restore patch details for modify_patch menu
                    if menu_name == "modify_patch":
                        if patch_details:
                            self.states[menu_name]["patch_details"] = patch_details
                        if original_details:
                            self.states[menu_name]["original_patch_details"] = original_details
        else:
            # When clearing all states, completely reinitialize the states dictionary
            # but preserve modify_patch details if they exist
            patch_details = None
            original_details = None
            if "modify_patch" in self.states:
                patch_details = self.states["modify_patch"].get("patch_details")
                original_details = self.states["modify_patch"].get("original_patch_details")
            
            # Completely reinitialize all states to their default values
            self.states = {
                "lock_unlock": {
                    "selected_files": [],
                    "listbox_items": []
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
                    "selected_prefix": "",
                    "prefix_history": []
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
            
            # Restore modify_patch details if they existed
            if patch_details:
                self.states["modify_patch"]["patch_details"] = None
                self.states["modify_patch"]["original_patch_details"] = None
            
            # Reset current menu
            self.current_menu = None

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

    def update_prefix_selection(self, prefix: str) -> None:
        """Update the selected prefix and maintain selection history."""
        if prefix and self.states["patches"]["selected_prefix"] != prefix:
            # Add current prefix to history if changing
            current = self.states["patches"]["selected_prefix"]
            if current:
                self.states["patches"]["prefix_history"].append(current)
            self.states["patches"]["selected_prefix"] = prefix
            
    def get_last_prefix(self) -> str:
        """Get the last used prefix or default."""
        history = self.states["patches"]["prefix_history"]
        return history[-1] if history else self.states["patches"]["selected_prefix"]

# Create a global instance
state_manager = StateManager()

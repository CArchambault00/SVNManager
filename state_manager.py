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
    
    def clear_state(self, menu_name=None):
        """
        Clear the state for a specific menu or all menus if menu_name is None
        """
        if menu_name:
            if menu_name in self.states:
                for key in self.states[menu_name]:
                    if isinstance(self.states[menu_name][key], list):
                        self.states[menu_name][key] = []
                    elif isinstance(self.states[menu_name][key], bool):
                        self.states[menu_name][key] = False
                    else:
                        self.states[menu_name][key] = ""
        else:
            for menu in self.states:
                self.clear_state(menu)

# Create a global instance
state_manager = StateManager()

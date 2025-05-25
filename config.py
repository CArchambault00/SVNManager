import os
import json
from tkinter import messagebox
import datetime as date
from profiles import get_profile

CONFIG_FILE = "svn_config.json"
ERROR_LOG_FILE = "SVNManager_error.log"
SUCCESS_LOG_FILE = "SVNManager_success.log"
neededVar = ["username"]  # Only username is required globally

def load_config():
    # First try to load from active profile
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            active_profile = config.get("active_profile")
            if active_profile:
                profile = get_profile(active_profile)
                if profile:
                    return {
                        "username": config.get("username", ""),
                        "svn_path": profile.svn_path,
                        "current_patches": profile.current_patches,
                        "dsn_name": profile.dsn_name,
                        "active_profile": active_profile,
                        "patch_prefix": profile.patch_prefix
                    }
            return config
    return {
        "username": "",
        "active_profile": None
    }

def save_config(data):
    # Only save username and active_profile in the config file
    config = {
        "username": data.get("username", ""),
        "active_profile": data.get("active_profile")
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

def get_unset_var():
    config = load_config()
    unsetVar = []
    
    # Check for username
    if not config.get("username"):
        unsetVar.append("username")
    
    # Check for active profile if username is set
    if config.get("username") and not config.get("active_profile"):
        unsetVar.append("active_profile")
    
    return unsetVar

def verify_config():
    unsetVar = get_unset_var()
    if unsetVar:
        raise ValueError(f"The following variables are not set: {', '.join(unsetVar)}")

def log_error(message: str, include_stack: bool = False):
    """
    Log error messages to the error log file.
    Args:
        message: The error message to log
        include_stack: Whether to include stack trace information
    """
    import traceback
    error_msg = message
    if include_stack:
        error_msg += f"\nStack trace:\n{traceback.format_exc()}"
    _write_log(error_msg, ERROR_LOG_FILE)

def log_success(action: str, details: str = None):
    """
    Log successful actions to the success log file.
    Args:
        action: The action that was successful (e.g., "Patch Creation", "File Lock")
        details: Additional details about the success (optional)
    """
    message = f"SUCCESS - {action}"
    if details:
        message += f"\nDetails: {details}"
    _write_log(message, SUCCESS_LOG_FILE)

def _write_log(message: str, log_file: str, include_timestamp: bool = True):
    """Internal function to write to log files with consistent formatting."""
    try:
        with open(log_file, "a", encoding='utf-8') as log:
            if include_timestamp:
                timestamp = date.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log.write(f"[{timestamp}] {message}\n")
            else:
                log.write(f"{message}\n")
            log.write("-" * 80 + "\n")  # Separator line for better readability
    except Exception as e:
        print(f"Failed to write to log file {log_file}: {e}")